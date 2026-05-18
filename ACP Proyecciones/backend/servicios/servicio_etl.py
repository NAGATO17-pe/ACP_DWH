"""
servicios/servicio_etl.py
=========================
Servicio ETL v3 — modelo controlado persistente.

Ya NO lanza subprocess directamente.
Ya NO usa broker SSE en memoria.

Responsabilidades:
  1. insertar_corrida → crea registro en Control.Corrida + encola en Control.Comando_Ejecucion
  2. El runner externo (runner/runner.py) lee la cola y ejecuta el pipeline
  3. stream_corrida → genera eventos SSE leyendo de Control.Corrida_Evento (poll persistente)
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator

import repositorios.repo_corridas as r_corrida
import repositorios.repo_comandos as r_cmd
from nucleo.etl_catalogo import listar_facts_disponibles
from nucleo.etl_argumentos import enriquecer_corrida_con_parametros, serializar_comentario_etl
from nucleo.excepciones import ErrorValidacion
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

_POLL_INTERVALO_SEG     = 2.0   # Frecuencia de polling SSE al DB
_POLL_TIMEOUT_TOTAL_SEG = 7200  # Tiempo máximo que el SSE espera (2h)


async def iniciar_corrida(
    iniciado_por: str,
    comentario: str | None = None,
    modo_ejecucion: str = "completo",
    facts: list[str] | None = None,
    incluir_dependencias: bool = True,
    refrescar_gold: bool = True,
    forzar_relectura_bronce: bool = True,
    max_reintentos: int = 0,
    timeout_segundos: int = 3600,
) -> dict:
    """
    Registra la corrida en Control.* y la pone en la cola del runner.
    Retorna inmediatamente con los metadatos de la corrida — no espera ejecución.
    """
    id_corrida = str(uuid.uuid4())
    ahora      = datetime.now()
    try:
        comentario_persistido = serializar_comentario_etl(
            comentario_usuario=comentario,
            modo_ejecucion=modo_ejecucion,
            facts=facts,
            incluir_dependencias=incluir_dependencias,
            refrescar_gold=refrescar_gold,
            forzar_relectura_bronce=forzar_relectura_bronce,
        )
    except ValueError as error:
        raise ErrorValidacion(str(error)) from error

    # 1. Crear registro maestro
    await asyncio.to_thread(
        r_corrida.insertar_corrida,
        id_corrida     = id_corrida,
        iniciado_por   = iniciado_por,
        comentario     = comentario_persistido,
        max_reintentos = max_reintentos,
        timeout_segundos = timeout_segundos,
    )

    # 2. Encolar comando para el runner
    await asyncio.to_thread(
        r_cmd.encolar_comando,
        id_corrida     = id_corrida,
        iniciado_por   = iniciado_por,
        tipo_comando   = "INICIAR",
        comentario     = comentario_persistido,
        max_reintentos = max_reintentos,
        timeout_seg    = timeout_segundos,
    )

    log.info(
        "Corrida encolada",
        extra={"id_corrida": id_corrida, "iniciado_por": iniciado_por},
    )

    return {
        "id_corrida":   id_corrida,
        "id_log":       None,   # Se rellena cuando el runner arranca
        "iniciado_por": iniciado_por,
        "fecha_inicio": ahora,
        "estado":       "PENDIENTE",
    }


async def cancelar_corrida(id_corrida: str, solicitado_por: str) -> bool:
    """
    Solicita la cancelación de una corrida activa.
    Retorna True si la corrida estaba en estado cancelable.
    """
    resultado = await asyncio.to_thread(
        r_corrida.solicitar_cancelacion,
        id_corrida, solicitado_por
    )
    if resultado:
        await asyncio.to_thread(
            r_corrida.insertar_evento,
            id_corrida,
            f"[CANCELADO] Solicitado por {solicitado_por}",
            "FIN",
        )
    return resultado


async def stream_eventos_corrida(id_corrida: str) -> AsyncGenerator[dict, None]:
    """
    Generador asíncrono para EventSourceResponse.
    Lee Control.Corrida_Evento en polling incremental.
    Termina cuando:
      - La corrida llega a estado terminal (OK/ERROR/CANCELADO/TIMEOUT)
      - Se alcanza el timeout global de streaming
    """
    ultimo_id_visto = 0
    tiempo_total    = 0.0
    estados_terminal = {"OK", "ERROR", "CANCELADO", "TIMEOUT"}

    while tiempo_total < _POLL_TIMEOUT_TOTAL_SEG:
        eventos, estado_corrida = await asyncio.to_thread(
            r_corrida.listar_eventos_y_estado,
            id_corrida,
            ultimo_id_visto,
        )

        for evento in eventos:
            ultimo_id_visto = evento["id_evento"]
            yield {
                "event": evento["tipo"].lower(),
                "data":  evento["mensaje"],
                "id":    str(evento["id_evento"]),
            }

        if estado_corrida in estados_terminal:
            eventos_finales, _ = await asyncio.to_thread(
                r_corrida.listar_eventos_y_estado, id_corrida, ultimo_id_visto
            )
            for evento in eventos_finales:
                ultimo_id_visto = evento["id_evento"]
                yield {
                    "event": evento["tipo"].lower(),
                    "data":  evento["mensaje"],
                    "id":    str(evento["id_evento"]),
                }
            yield {"event": "fin", "data": "[FIN_CORRIDA]"}
            return

        await asyncio.sleep(_POLL_INTERVALO_SEG)
        tiempo_total += _POLL_INTERVALO_SEG

    yield {"event": "error", "data": "[TIMEOUT_STREAM] La corrida excedió el tiempo de streaming."}


def corrida_existe(id_corrida: str) -> bool:
    """Verificación rápida de existencia para el endpoint de stream."""
    return r_corrida.obtener_corrida(id_corrida) is not None


def obtener_corrida(id_corrida: str) -> dict | None:
    """Retorna el estado actual de una corrida."""
    corrida = enriquecer_corrida_con_parametros(r_corrida.obtener_corrida(id_corrida))
    if corrida is None:
        return None
    corrida["pasos"] = r_corrida.listar_pasos_corrida(id_corrida)
    return corrida


def obtener_pasos_corrida(id_corrida: str) -> list[dict]:
    """Retorna la traza persistida de pasos para una corrida."""
    return r_corrida.listar_pasos_corrida(id_corrida)


def listar_corridas_activas(limite: int = 50) -> list[dict]:
    """Retorna corridas PENDIENTE o EJECUTANDO. Acepta limite configurable."""
    return [
        enriquecer_corrida_con_parametros(corrida)
        for corrida in r_corrida.listar_corridas(limite=limite, solo_activas=True)
    ]


def listar_catalogo_facts() -> list[dict]:
    """Retorna el catálogo oficial de facts soportadas por rerun."""
    return listar_facts_disponibles()
