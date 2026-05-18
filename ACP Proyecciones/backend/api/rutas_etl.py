"""
api/rutas_etl.py
================
Router /api/v1/etl — Pipeline ETL v3 (modelo controlado persistente)

Endpoints:
  POST   /api/v1/etl/corridas                         — Encola corrida
  GET    /api/v1/etl/corridas                         — Historial
  GET    /api/v1/etl/corridas/activas                 — Solo PENDIENTE/EJECUTANDO
  GET    /api/v1/etl/corridas/{id}                    — Estado de una corrida
  GET    /api/v1/etl/corridas/{id}/eventos            — Stream SSE
  DELETE /api/v1/etl/corridas/{id}                    — Solicitar cancelación

Seguridad:
  - GET   → viewer+
  - POST  → operador_etl+
  - DELETE → operador_etl+
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse

from nucleo.auth import UsuarioActual, obtener_usuario_actual, require_rol
from nucleo.excepciones import ErrorRecursoNoEncontrado
from nucleo.http_utils import obtener_ip_cliente, obtener_request_id
from nucleo.rate_limit import verificar_rate_limit
from schemas.etl.peticion import PeticionIniciarCorrida
from schemas.etl.respuesta import (
    RespuestaCorridaIniciada,
    RespuestaDetalleCorrida,
    RespuestaFactDisponible,
    RespuestaHistorialCorrida,
    RespuestaPasoCorrida,
)
from servicios.servicio_auth import registrar_accion
from servicios.servicio_etl import (
    cancelar_corrida,
    corrida_existe,
    iniciar_corrida,
    listar_catalogo_facts,
    listar_corridas_activas,
    obtener_corrida,
    obtener_pasos_corrida,
    stream_eventos_corrida,
)
from servicios.servicio_auditoria import obtener_historial

enrutador_etl = APIRouter(prefix="/v1/etl", tags=["ETL"])

# Políticas de rate-limit por endpoint sensible
_rl_iniciar   = lambda r: verificar_rate_limit(r, max_intentos=10, ventana_segundos=60)   # noqa: E731
_rl_cancelar  = lambda r: verificar_rate_limit(r, max_intentos=20, ventana_segundos=60)   # noqa: E731


# ── POST /corridas ─────────────────────────────────────────────────────────────

@enrutador_etl.post(
    "/corridas",
    response_model=RespuestaCorridaIniciada,
    summary="Encola una corrida del pipeline ETL",
    description=(
        "Crea el registro en Control.Corrida y lo pone en la cola del runner externo. "
        "Retorna inmediatamente. El runner procesará la corrida de forma asíncrona. "
        "Requiere rol **operador_etl** o superior."
    ),
    dependencies=[Depends(require_rol("operador_etl")), Depends(_rl_iniciar)],
)
async def iniciar_corrida_etl(
    cuerpo: PeticionIniciarCorrida,
    request: Request,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> RespuestaCorridaIniciada:
    datos = await iniciar_corrida(
        iniciado_por=usuario.nombre_usuario,
        comentario=cuerpo.comentario,
        modo_ejecucion=cuerpo.modo_ejecucion,
        facts=cuerpo.facts,
        incluir_dependencias=cuerpo.incluir_dependencias,
        refrescar_gold=cuerpo.refrescar_gold,
        forzar_relectura_bronce=cuerpo.forzar_relectura_bronce,
    )
    await registrar_accion(
        nombre_usuario=usuario.nombre_usuario,
        accion="LANZAR_ETL",
        endpoint=str(request.url),
        request_id=obtener_request_id(request),
        ip_origen=obtener_ip_cliente(request),
        detalle=(
            f"id_corrida={datos['id_corrida']} "
            f"modo={cuerpo.modo_ejecucion} "
            f"facts={','.join(cuerpo.facts or []) or '-'}"
        ),
    )
    return RespuestaCorridaIniciada(
        id_corrida=datos["id_corrida"],
        id_log=datos.get("id_log"),
        iniciado_por=datos["iniciado_por"],
        fecha_inicio=datos["fecha_inicio"],
        url_stream=f"/api/v1/etl/corridas/{datos['id_corrida']}/eventos",
    )


# ── GET /corridas ──────────────────────────────────────────────────────────────

@enrutador_etl.get(
    "/corridas",
    response_model=list[RespuestaHistorialCorrida],
    summary="Historial de corridas ETL",
    description="Retorna las últimas N ejecuciones desde Auditoria.Log_Carga.",
    dependencies=[Depends(require_rol("viewer"))],
)
async def listar_historial(
    limite: int = Query(default=50, ge=1, le=500),
) -> list[RespuestaHistorialCorrida]:
    registros = await obtener_historial(limite=limite)
    return [RespuestaHistorialCorrida(**r) for r in registros]


# ── GET /corridas/activas ──────────────────────────────────────────────────────

@enrutador_etl.get(
    "/corridas/activas",
    summary="Corridas activas (PENDIENTE o EJECUTANDO)",
    dependencies=[Depends(require_rol("viewer"))],
)
async def corridas_activas() -> list[dict]:
    return await listar_corridas_activas()
def corridas_activas(
    limite: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    return listar_corridas_activas(limite=limite)


@enrutador_etl.get(
    "/facts",
    response_model=list[RespuestaFactDisponible],
    summary="Catálogo de facts soportadas por rerun",
    dependencies=[Depends(require_rol("viewer"))],
)
async def catalogo_facts() -> list[RespuestaFactDisponible]:
    facts = await listar_catalogo_facts()
    return [RespuestaFactDisponible(**fact) for fact in facts]


# ── GET /corridas/{id} ─────────────────────────────────────────────────────────

@enrutador_etl.get(
    "/corridas/{id_corrida}",
    response_model=RespuestaDetalleCorrida,
    summary="Estado de una corrida",
    dependencies=[Depends(require_rol("viewer"))],
)
async def estado_corrida(id_corrida: str) -> RespuestaDetalleCorrida:
    datos = await obtener_corrida(id_corrida)
    if datos is None:
        raise ErrorRecursoNoEncontrado(f"Corrida '{id_corrida}'")
    return RespuestaDetalleCorrida(**datos)


@enrutador_etl.get(
    "/corridas/{id_corrida}/pasos",
    response_model=list[RespuestaPasoCorrida],
    summary="Traza de pasos de una corrida",
    dependencies=[Depends(require_rol("viewer"))],
)
async def pasos_corrida(id_corrida: str) -> list[RespuestaPasoCorrida]:
    if not await corrida_existe(id_corrida):
        raise ErrorRecursoNoEncontrado(f"Corrida '{id_corrida}'")
    pasos = await obtener_pasos_corrida(id_corrida)
    return [RespuestaPasoCorrida(**paso) for paso in pasos]


# ── GET /corridas/{id}/eventos (SSE) ──────────────────────────────────────────

@enrutador_etl.get(
    "/corridas/{id_corrida}/eventos",
    summary="Stream SSE de una corrida",
    description=(
        "Abre un canal SSE que transmite eventos de la corrida leyendo de "
        "Control.Corrida_Evento. Sobrevive reinicios del servidor web. "
        "Múltiples clientes pueden suscribirse simultáneamente. "
        "Termina cuando la corrida llega a estado terminal. "
        "Requiere rol **viewer** o superior."
    ),
    dependencies=[Depends(require_rol("viewer"))],
)
async def stream_corrida(id_corrida: str) -> EventSourceResponse:
    if not await corrida_existe(id_corrida):
        raise ErrorRecursoNoEncontrado(f"Corrida '{id_corrida}'")
    return EventSourceResponse(stream_eventos_corrida(id_corrida))


# ── DELETE /corridas/{id} — Cancelar ─────────────────────────────────────────

@enrutador_etl.delete(
    "/corridas/{id_corrida}",
    summary="Solicitar cancelación de una corrida",
    description=(
        "Marca la corrida como CANCELADO. "
        "El runner detecta el cambio en su próximo ciclo de heartbeat (≤30s). "
        "Requiere rol **operador_etl** o superior."
    ),
    dependencies=[Depends(require_rol("operador_etl")), Depends(_rl_cancelar)],
)
async def cancelar(
    id_corrida: str,
    request: Request,
    usuario: Annotated[UsuarioActual, Depends(obtener_usuario_actual)],
) -> dict:
    datos = await obtener_corrida(id_corrida)
    if datos is None:
        raise ErrorRecursoNoEncontrado(f"Corrida '{id_corrida}'")

    cancelado = await cancelar_corrida(id_corrida, usuario.nombre_usuario)

    await registrar_accion(
        nombre_usuario=usuario.nombre_usuario,
        accion="CANCELAR_ETL",
        endpoint=str(request.url),
        request_id=obtener_request_id(request),
        ip_origen=obtener_ip_cliente(request),
        detalle=f"id_corrida={id_corrida} cancelado={cancelado}",
    )

    if not cancelado:
        return {"mensaje": "La corrida ya no estaba en estado activo.", "cancelado": False}
    return {"mensaje": "Cancelación solicitada. El runner detendrá el proceso en breve.", "cancelado": True}
