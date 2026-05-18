"""
servicios/servicio_etl.py
=========================
Servicio ETL v3 — modelo controlado persistente.
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
        "id_log":       None,
        "iniciado_por": iniciado_por,
        "fecha_inicio": ahora,
        "estado":       "PENDIENTE",
    }


async def cancelar_corrida(id_corrida: str, solicitado_por: str) -> bool:
    """Solicita la cancelación de una corrida activa."""
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
    """Generador asíncrono para EventSourceResponse con polling persistente."""
    ultimo_id_visto = 0
    tiempo_total    = 0.0
    estados_terminal = {"OK", "ERROR", "CANCELADO", "TIMEOUT"}

    while tiempo_total < _POLL_TIMEOUT_TOTAL_SEG:
        eventos = await asyncio.to_thread(r_corrida.listar_eventos, id_corrida, ultimo_id_visto)
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

        corrida = await asyncio.to_thread(r_corrida.obtener_corrida, id_corrida)
        if corrida and corrida.get("estado") in estados_terminal:
            eventos_finales = await asyncio.to_thread(r_corrida.listar_eventos, id_corrida, ultimo_id_visto)
        if estado_corrida in estados_terminal:
            eventos_finales, _ = await asyncio.to_thread(
                r_corrida.listar_eventos_y_estado, id_corrida, ultimo_id_visto
            )
            for evento in eventos_finales:
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


async def corrida_existe(id_corrida: str) -> bool:
    """Verificación rápida de existencia asíncrona."""
    res = await asyncio.to_thread(r_corrida.obtener_corrida, id_corrida)
    return res is not None


async def obtener_corrida(id_corrida: str) -> dict | None:
    """Retorna el estado detallado de una corrida."""
    raw = await asyncio.to_thread(r_corrida.obtener_corrida, id_corrida)
    if raw is None:
        return None
    corrida = enriquecer_corrida_con_parametros(raw)
    pasos = await asyncio.to_thread(r_corrida.listar_pasos_corrida, id_corrida)
    corrida["pasos"] = pasos
    return corrida


async def obtener_pasos_corrida(id_corrida: str) -> list[dict]:
    """Retorna la traza de pasos de forma asíncrona."""
    return await asyncio.to_thread(r_corrida.listar_pasos_corrida, id_corrida)


async def listar_corridas_activas() -> list[dict]:
    """Lista corridas activas (PENDIENTE/EJECUTANDO) asíncronamente."""
    raw_list = await asyncio.to_thread(r_corrida.listar_corridas, limite=10, solo_activas=True)
    return [enriquecer_corrida_con_parametros(c) for c in raw_list]
def listar_corridas_activas(limite: int = 50) -> list[dict]:
    """Retorna corridas PENDIENTE o EJECUTANDO. Acepta limite configurable."""
    return [
        enriquecer_corrida_con_parametros(corrida)
        for corrida in r_corrida.listar_corridas(limite=limite, solo_activas=True)
    ]


async def listar_catalogo_facts() -> list[dict]:
    """Retorna el catálogo oficial asíncronamente."""
    # listar_facts_disponibles es memoria pura (lista estática), no requiere thread
    return listar_facts_disponibles()
