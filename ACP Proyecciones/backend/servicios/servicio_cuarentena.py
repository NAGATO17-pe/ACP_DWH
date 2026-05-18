"""
servicios/servicio_cuarentena.py
================================
Lógica para consultar y gestionar registros en MDM.Cuarentena.
Todos los métodos son async — I/O delegado a asyncio.to_thread.
Emite señales Blinker al EventBus al resolver/rechazar.
"""

from __future__ import annotations

import asyncio

from nucleo.cache import cache
from nucleo.excepciones import ErrorRecursoNoEncontrado
from nucleo.logging import obtener_logger
from servicios.event_bus import EventBus
import repositorios.repo_auditoria as repo_auditoria
import repositorios.repo_cuarentena as repo

log = obtener_logger(__name__)


async def listar_cuarentena(
    pagina: int = 1,
    tamano: int = 20,
    tabla_filtro: str | None = None,
) -> dict:
    return await asyncio.to_thread(
        repo.listar_pendientes,
        pagina=pagina,
        tamano=tamano,
        tabla_filtro=tabla_filtro,
    )


async def resolver_registro(
    tabla_origen: str,
    id_registro: str,
    valor_canonico: str,
    analista: str,
    comentario: str | None,
) -> dict:
    """Marca un registro de MDM.Cuarentena como RESUELTO."""
    rowcount = await asyncio.to_thread(
        repo.marcar_resuelto,
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico=valor_canonico,
        analista=analista,
    )
    if rowcount == 0:
        raise ErrorRecursoNoEncontrado(f"Registro #{id_registro} en {tabla_origen}")

    await asyncio.to_thread(cache.limpiar_todo)
    await asyncio.to_thread(
        repo_auditoria.insertar_decision_mdm,
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico=valor_canonico,
        decision="RESUELTO",
        analista=analista,
        comentario=comentario or "",
    )

    EventBus.mdm_decision.send(
        "servicio_cuarentena",
        accion="RESUELTO",
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        analista=analista,
    )
    log.info(
        "Registro de cuarentena resuelto",
        extra={"id_registro": id_registro, "tabla_origen": tabla_origen},
    )
    return {
        "id_registro":  id_registro,
        "estado_nuevo": "RESUELTO",
        "mensaje":      f"Registro resuelto con valor corregido '{valor_canonico}'.",
    }


async def rechazar_registro(
    tabla_origen: str,
    id_registro: str,
    motivo: str,
    analista: str,
) -> dict:
    """Marca un registro de MDM.Cuarentena como DESCARTADO."""
    rowcount = await asyncio.to_thread(
        repo.marcar_descartado,
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        analista=analista,
    )
    if rowcount == 0:
        raise ErrorRecursoNoEncontrado(f"Registro #{id_registro} en {tabla_origen}")

    await asyncio.to_thread(cache.limpiar_todo)
    await asyncio.to_thread(
        repo_auditoria.insertar_decision_mdm,
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        valor_canonico="",
        decision="DESCARTADO",
        analista=analista,
        comentario=motivo,
    )

    EventBus.mdm_decision.send(
        "servicio_cuarentena",
        accion="DESCARTADO",
        tabla_origen=tabla_origen,
        id_registro=id_registro,
        analista=analista,
    )
    log.info(
        "Registro de cuarentena descartado",
        extra={"id_registro": id_registro, "tabla_origen": tabla_origen},
    )
    return {
        "id_registro":  id_registro,
        "estado_nuevo": "DESCARTADO",
        "mensaje":      f"Registro descartado. Motivo: {motivo}",
    }
async def obtener_resumen_cuarentena() -> dict:
    """Retorna conteos resumidos por estado."""
    return await asyncio.to_thread(repo.obtener_resumen)
