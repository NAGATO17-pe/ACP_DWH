"""
nucleo/conexion.py
==================
Conexion SQL Server del backend ACP Platform.

Consume la configuración desde nucleo.settings — nunca llama os.getenv()
directamente. El engine se crea una sola vez (lru_cache) y se reutiliza
durante toda la vida del proceso.
"""

import warnings
import urllib
from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning
import time
from nucleo.settings import settings

# Silencia la advertencia de versión del driver ODBC 17 con SQL Server 2017+
warnings.filterwarnings(
    "ignore",
    message=r"Unrecognized server version info '17\..*'\. Some SQL Server features may not function properly\.",
    category=SAWarning,
)


@lru_cache(maxsize=1)
def obtener_engine() -> Engine:
    """
    Retorna el Engine SQLAlchemy singleton para el backend.
    Se construye a partir de settings — sin hardcodear nada.
    """
    trust = "yes" if settings.entorno == "dev" else "no"

    if settings.db_usuario:
        cadena_pyodbc = (
            f"DRIVER={{{settings.db_driver}}};"
            f"SERVER={settings.db_servidor};"
            f"DATABASE={settings.db_nombre};"
            f"UID={settings.db_usuario};"
            f"PWD={settings.db_clave};"
            f"Encrypt=yes;"
            f"TrustServerCertificate={trust};"
            f"APP=ACP_Backend;"
        )
    else:
        cadena_pyodbc = (
            f"DRIVER={{{settings.db_driver}}};"
            f"SERVER={settings.db_servidor};"
            f"DATABASE={settings.db_nombre};"
            f"Trusted_Connection=yes;"
            f"Encrypt=yes;"
            f"TrustServerCertificate={trust};"
            f"APP=ACP_Backend;"
        )

    cadena_url = (
        "mssql+pyodbc:///?odbc_connect="
        + urllib.parse.quote_plus(cadena_pyodbc)
    )

    return create_engine(
        cadena_url,
        fast_executemany=True,
        pool_pre_ping=True,
    )

def verificar_conexion() -> dict:
    """
    Ejecuta un ping liviano contra la BD.
    Retorna un dict con el estado, latencia y versión del servidor.
    Nunca propaga excepciones — devuelve {'conectado': False} si falla.
    """
    info: dict = {"conectado": False, "base_datos": "-", "latencia_ms": "-"}
    try:
        inicio = time.perf_counter()
        with obtener_engine().connect() as conexion:
            fila = conexion.execute(
                text(
                    "SELECT DB_NAME() AS base_activa, "
                    "SERVERPROPERTY('ProductVersion') AS version_sql"
                )
            ).fetchone()
        fin = time.perf_counter()

        info["conectado"] = True
        info["base_datos"] = fila.base_activa  # type: ignore[union-attr]
        info["version"] = str(fila.version_sql)  # type: ignore[union-attr]
        info["latencia_ms"] = round((fin - inicio) * 1000, 1)
    except Exception as error:  # noqa: BLE001
        info["error"] = str(error)
    return info
