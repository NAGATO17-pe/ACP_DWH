"""
servicios/servicio_auditoria.py
================================
Lógica de consulta de auditoría.
Todos los métodos son async — I/O delegado a asyncio.to_thread.
Los listeners de EventBus se registran desde main.py en lifespan.
"""

from __future__ import annotations

import asyncio

import repositorios.repo_auditoria as repo


async def obtener_historial(limite: int = 50) -> list[dict]:
    """Retorna las últimas N corridas registradas en Auditoria.Log_Carga."""
    return await asyncio.to_thread(repo.listar_corridas, limite=limite)


async def obtener_ultimo_estado_tabla(tabla_destino: str) -> dict | None:
    """Retorna el último estado de carga para una tabla específica."""
    return await asyncio.to_thread(repo.ultimo_estado_tabla, tabla_destino)
