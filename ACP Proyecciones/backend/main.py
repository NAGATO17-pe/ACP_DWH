"""
main.py
=======
Punto de entrada del backend ACP Platform.

Registra todos los routers, middlewares, manejadores de error
y expone los health checks principal, liveness y readiness.

Arranque directo:
    uvicorn main:aplicacion --host 0.0.0.0 --port 8810

Arranque por módulo (dev con reload):
    python main.py
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ── Núcleo ────────────────────────────────────────────────────────────────────
from nucleo.settings import settings
from nucleo.logging import configurar_logging, obtener_logger
from nucleo.middleware import RequestIdMiddleware
from nucleo.conexion import verificar_conexion
from nucleo.excepciones import manejar_error_generico, manejar_error_http
from servicios.listeners import registrar_listeners, desregistrar_listeners

# ── Routers ───────────────────────────────────────────────────────────────────
from api.rutas_health import enrutador_health
from api.rutas_auth import enrutador_auth
from api.rutas_etl import enrutador_etl
from api.rutas_cuarentena import enrutador_cuarentena
from api.rutas_catalogos import enrutador_catalogos
from api.rutas_auditoria import enrutador_auditoria
from api.rutas_config import enrutador_config
from api.rutas_reinyeccion import enrutador_reinyeccion

# ── Documentación Scalar (opcional) ───────────────────────────────────────────
try:
    from scalar_fastapi import get_scalar_api_reference
except ImportError:
    get_scalar_api_reference = None  # pragma: no cover

# Configura logging al importar el módulo (antes del lifespan)
configurar_logging()
log = obtener_logger(__name__)


_MAX_REINTENTOS_BD = 3
_ESPERA_REINTENTO_SEG = 5


@asynccontextmanager
async def lifespan(app: FastAPI):
    registrar_listeners()

    # Verificar conexión con reintentos (útil en contenedores donde SQL Server arranca lento)
    info: dict = {"conectado": False}
    for intento in range(1, _MAX_REINTENTOS_BD + 1):
        info = await asyncio.to_thread(verificar_conexion)
        if info["conectado"]:
            break
        log.warning(
            "BD no disponible, reintentando...",
            extra={"intento": intento, "max": _MAX_REINTENTOS_BD, "error": info.get("error")},
        )
        if intento < _MAX_REINTENTOS_BD:
            await asyncio.sleep(_ESPERA_REINTENTO_SEG)

    if info["conectado"]:
        log.info(
            "Backend iniciado — BD conectada",
            extra={
                "entorno":     settings.entorno,
                "base_datos":  info["base_datos"],
                "latencia_ms": info["latencia_ms"],
                "version_sql": info.get("version", "-"),
            },
        )
    else:
        log.warning(
            "Backend iniciado — SIN conexión a SQL Server tras reintentos",
            extra={
                "entorno": settings.entorno,
                "error":   info.get("error", "desconocido"),
            },
        )

    yield

    desregistrar_listeners()
    log.info("Backend detenido limpiamente")


# ── Aplicación ─────────────────────────────────────────────────────────────────
aplicacion = FastAPI(
    title=settings.api_titulo,
    description=(
        "Backend headless para el DWH Geographic Phenology - Agrícola Cerro Prieto. "
        "Expone el pipeline ETL como subproceso con telemetría SSE, gestión de cuarentena MDM, "
        "consulta de catálogos y auditoría de cargas."
    ),
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middlewares ────────────────────────────────────────────────────────────────
aplicacion.add_middleware(RequestIdMiddleware)
aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origenes,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# ── Manejadores de error ───────────────────────────────────────────────────────
aplicacion.add_exception_handler(HTTPException, manejar_error_http)
aplicacion.add_exception_handler(Exception, manejar_error_generico)

# ── Routers ──────────────────────────────────────────────────────────────────
# Infraestructura (sin versionar)
aplicacion.include_router(enrutador_health)      # /health, /health/live, /health/ready
# Autenticación (sin versionar, estable por diseño)
aplicacion.include_router(enrutador_auth)          # /auth/login, /auth/me, /auth/usuarios
# Dominio — todos bajo /api con versionado /v1 en el propio router
aplicacion.include_router(enrutador_etl,          prefix="/api")
aplicacion.include_router(enrutador_cuarentena,   prefix="/api")
aplicacion.include_router(enrutador_catalogos,    prefix="/api")
aplicacion.include_router(enrutador_auditoria,    prefix="/api")
aplicacion.include_router(enrutador_config,       prefix="/api")
aplicacion.include_router(enrutador_reinyeccion,  prefix="/api")  # Herramienta Re-inyección MDM

# ── Documentación Scalar (opcional) ───────────────────────────────────────────
if get_scalar_api_reference is not None:
    @aplicacion.get("/scalar", include_in_schema=False)
    async def scalar_html():
        """Sirve la documentación moderna de Scalar."""
        return get_scalar_api_reference(
            openapi_url=aplicacion.openapi_url,
            title=aplicacion.title + " (Scalar)",
        )


# ── Arranque directo ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:aplicacion",
        host=settings.host,
        port=settings.puerto,
        workers=settings.workers,
        reload=settings.reload or settings.es_desarrollo,
        log_level=settings.log_nivel.lower(),
    )
