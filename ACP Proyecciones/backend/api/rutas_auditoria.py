"""
api/rutas_auditoria.py
=======================
Router /api/v1/auditoria — Consultas de solo lectura.

Seguridad: viewer+ en todos los endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from nucleo.auth import require_rol
from nucleo.excepciones import ErrorRecursoNoEncontrado
from schemas.auditoria.respuesta import RespuestaLogCarga, RespuestaUltimoEstado
from servicios.servicio_auditoria import obtener_historial, obtener_ultimo_estado_tabla

enrutador_auditoria = APIRouter(prefix="/v1/auditoria", tags=["Auditoría"])


@enrutador_auditoria.get(
    "/log-carga",
    response_model=list[RespuestaLogCarga],
    summary="Historial de cargas ETL",
    description="Retorna las últimas N entradas de Auditoria.Log_Carga ordenadas por fecha desc.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def listar_log_carga(
    limite: int = Query(default=50, ge=1, le=500, description="Máximo de registros a retornar."),
) -> list[RespuestaLogCarga]:
    registros = await obtener_historial(limite=limite)
    return [RespuestaLogCarga(**r) for r in registros]


@enrutador_auditoria.get(
    "/log-carga/{tabla_destino}",
    response_model=RespuestaUltimoEstado,
    summary="Último estado de una tabla",
    description="Retorna la última entrada de Auditoria.Log_Carga para una tabla específica.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def ultimo_estado(tabla_destino: str) -> RespuestaUltimoEstado:
    datos = await obtener_ultimo_estado_tabla(tabla_destino)
    if datos is None:
        raise ErrorRecursoNoEncontrado(f"Tabla '{tabla_destino}'")
    return RespuestaUltimoEstado(**datos)
