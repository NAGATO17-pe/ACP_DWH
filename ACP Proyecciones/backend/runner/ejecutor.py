"""
runner/ejecutor.py
==================
Ejecutor de un subproceso pipeline.py para una corrida específica.

Responsabilidades:
  - Lanzar pipeline.py como subprocess
  - Capturar stdout/stderr línea a línea
  - Persistir cada línea en Control.Corrida_Evento (no en memoria)
  - Publicar heartbeats periódicos al lock y a la corrida
  - Detectar cancelación en cada ciclo de heartbeat
  - Registrar inicio y fin en Auditoria.Log_Carga
  - Retornar el estado final (OK | ERROR | CANCELADO | TIMEOUT)
"""

from __future__ import annotations
import os
import re
import sys
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from nucleo.etl_argumentos import construir_argumentos_pipeline, deserializar_comentario_etl
from nucleo.auditoria import registrar_inicio_corrida, registrar_fin_corrida
from nucleo.logging import obtener_logger
import repositorios.repo_corridas as r_corrida
import repositorios.repo_locks as r_lock

log = obtener_logger(__name__)

EstadoFinal = Literal["OK", "ERROR", "CANCELADO", "TIMEOUT"]

_DIR_ETL = Path(__file__).resolve().parents[2] / "ETL"
_SCRIPT  = _DIR_ETL / "pipeline.py"
_PATRON_PASO = re.compile(r"^\[(?P<orden>\d+)/(?:\d+)\]\s+(?P<descripcion>.+?)\s*$")
_PATRON_ERROR = re.compile(r"^\s*ERROR(?:\s+en\s+(?P<objetivo>[^:]+))?:\s*(?P<detalle>.+)$")


@dataclass
class _PasoActivo:
    id_paso: int
    nombre_paso: str
    orden: int
    cerrado: bool = False


def _resolver_python() -> str:
    """Devuelve el ejecutable Python del mismo entorno virtual."""
    exe = sys.executable
    if "uvicorn" in exe.lower():
        return str(Path(exe).parent / "python.exe")
    return exe


def _normalizar_nombre_paso(descripcion: str) -> str:
    return descripcion.strip().rstrip(".").strip()


def _extraer_inicio_paso(linea: str) -> tuple[int, str] | None:
    coincidencia = _PATRON_PASO.match(linea.strip())
    if not coincidencia:
        return None
    return (
        int(coincidencia.group("orden")),
        _normalizar_nombre_paso(coincidencia.group("descripcion")),
    )


def _linea_es_error_de_paso(linea: str, paso_activo: _PasoActivo | None) -> tuple[bool, str | None]:
    coincidencia = _PATRON_ERROR.match(linea.strip())
    if not coincidencia:
        return False, None

    objetivo = (coincidencia.group("objetivo") or "").strip()
    if paso_activo is None or not objetivo:
        return True, linea.strip()
    if objetivo in paso_activo.nombre_paso:
        return True, linea.strip()
    return False, None


def _cerrar_paso_activo(
    paso_activo: _PasoActivo | None,
    *,
    estado: str,
    mensaje_error: str | None = None,
) -> None:
    if paso_activo is None or paso_activo.cerrado or paso_activo.id_paso < 0:
        return
    r_corrida.cerrar_paso(
        paso_activo.id_paso,
        estado=estado,
        mensaje_error=mensaje_error,
    )
    paso_activo.cerrado = True


def _abrir_nuevo_paso(id_corrida: str, orden: int, nombre_paso: str) -> _PasoActivo:
    return _PasoActivo(
        id_paso=r_corrida.insertar_paso(id_corrida, nombre_paso, orden=orden),
        nombre_paso=nombre_paso,
        orden=orden,
    )


def ejecutar_corrida(
    id_corrida: str,
    iniciado_por: str,
    comentario: str | None = None,
    timeout_segundos: int = 3600,
    heartbeat_intervalo_seg: int = 30,
) -> EstadoFinal:
    """
    Ejecuta pipeline.py para la corrida dada.

    Flujo:
        1. Registra el inicio en Auditoria.Log_Carga → obtiene id_log
        2. Actualiza Control.Corrida a EJECUTANDO
        3. Lanza subprocess con timeout de watchdog
        4. Lee stdout línea a línea → INSERT Control.Corrida_Evento
        5. Cada heartbeat_intervalo_seg verifica cancelación
        6. Al terminar: actualiza Control.Corrida y Auditoria.Log_Carga

    Retorna el estado final.
    """
    pid = os.getpid()
    estado_final: EstadoFinal = "ERROR"
    codigo_retorno = -1
    id_log: int | None = None
    parametros = deserializar_comentario_etl(comentario)
    modo_ejecucion = parametros["modo_ejecucion"]
    nombre_pipeline = "PIPELINE_COMPLETO" if modo_ejecucion == "completo" else "PIPELINE_FACTS"
    argumentos_pipeline = construir_argumentos_pipeline(comentario)

    # ── 1. Auditoría de inicio ─────────────────────────────────────────────────
    try:
        id_log = registrar_inicio_corrida(
            nombre_proceso="ETL_RUNNER",
            tabla_destino=nombre_pipeline,
            nombre_archivo=f"corrida_{id_corrida[:8]}_{modo_ejecucion}",
        )
    except Exception:
        log.warning("No se pudo registrar inicio en auditoría", extra={"id_corrida": id_corrida})

    # ── 2. Marcar corrida como EJECUTANDO ─────────────────────────────────────
    r_corrida.actualizar_estado_corrida(
        id_corrida=id_corrida,
        estado="EJECUTANDO",
        pid_runner=pid,
        id_log_auditoria=id_log,
    )
    r_corrida.insertar_evento(id_corrida, f"[RUNNER] Inicio. PID={pid}", tipo="LOG")
    paso_activo: _PasoActivo | None = None

    # ── 3. Lanzar subprocess ──────────────────────────────────────────────────
    proceso: subprocess.Popen | None = None
    cancelado_por_heartbeat = False

    try:
        proceso = subprocess.Popen(
            [_resolver_python(), str(_SCRIPT), *argumentos_pipeline],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(_DIR_ETL),
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        # ── 4. Leer stdout + heartbeat en thread paralelo ──────────────────────
        ultimo_heartbeat = time.monotonic()
        deadline = time.monotonic() + timeout_segundos

        if proceso.stdout:
            for linea in proceso.stdout:
                ahora = time.monotonic()
                linea_limpia = linea.rstrip("\n")

                r_corrida.insertar_evento(id_corrida, linea_limpia, tipo="LOG")
                inicio_paso = _extraer_inicio_paso(linea_limpia)
                if inicio_paso is not None:
                    orden_paso, nombre_paso = inicio_paso
                    _cerrar_paso_activo(paso_activo, estado="OK")
                    paso_activo = _abrir_nuevo_paso(id_corrida, orden_paso, nombre_paso)
                else:
                    es_error_paso, mensaje_error = _linea_es_error_de_paso(linea_limpia, paso_activo)
                    if es_error_paso:
                        _cerrar_paso_activo(
                            paso_activo,
                            estado="ERROR",
                            mensaje_error=mensaje_error,
                        )

                # ── 5. Heartbeat y verificación de cancelación ─────────────────
                if ahora - ultimo_heartbeat >= heartbeat_intervalo_seg:
                    r_corrida.actualizar_heartbeat_corrida(id_corrida, pid)
                    r_lock.actualizar_heartbeat_lock()
                    ultimo_heartbeat = ahora

                    if r_corrida.corrida_fue_cancelada(id_corrida):
                        log.info("[RUNNER] Cancelación detectada, terminando proceso",
                                 extra={"id_corrida": id_corrida})
                        proceso.terminate()
                        cancelado_por_heartbeat = True
                        break

                if ahora > deadline:
                    log.warning("[RUNNER] Timeout alcanzado, terminando proceso",
                                extra={"id_corrida": id_corrida})
                    proceso.terminate()
                    estado_final = "TIMEOUT"
                    break

        proceso.wait(timeout=10)
        codigo_retorno = proceso.returncode

    except subprocess.TimeoutExpired:
        if proceso:
            proceso.kill()
        codigo_retorno = -9
        estado_final = "TIMEOUT"
    except Exception as exc:
        r_corrida.insertar_evento(id_corrida, f"[RUNNER ERROR] {exc}", tipo="ERROR")
        log.exception("[RUNNER] Excepción al ejecutar pipeline", extra={"id_corrida": id_corrida})
        codigo_retorno = -99

    # ── 6. Determinar estado final ────────────────────────────────────────────
    if cancelado_por_heartbeat:
        estado_final = "CANCELADO"
    elif estado_final not in ("TIMEOUT",):
        estado_final = "OK" if codigo_retorno == 0 else "ERROR"

    msg_final = (
        "Pipeline finalizado con éxito."
        if estado_final == "OK"
        else f"Pipeline terminó con estado {estado_final}. Código: {codigo_retorno}."
    )

    # Evento de cierre
    r_corrida.insertar_evento(id_corrida, f"[FIN] {msg_final}", tipo="FIN")

    _cerrar_paso_activo(
        paso_activo,
        estado="OK" if estado_final == "OK" else "ERROR",
        mensaje_error=msg_final if estado_final != "OK" else None,
    )

    # Actualizar Control.Corrida
    r_corrida.actualizar_estado_corrida(
        id_corrida=id_corrida,
        estado=estado_final,
        mensaje_final=msg_final,
    )

    # Actualizar Auditoria.Log_Carga
    if id_log is not None:
        try:
            registrar_fin_corrida(
                id_log=id_log,
                estado="OK" if estado_final == "OK" else "ERROR",
                mensaje_error=msg_final if estado_final != "OK" else None,
            )
        except Exception:
            log.warning("No se pudo actualizar auditoría al finalizar")

    log.info(
        "[RUNNER] Corrida finalizada",
        extra={"id_corrida": id_corrida, "estado": estado_final, "codigo": codigo_retorno},
    )
    return estado_final
