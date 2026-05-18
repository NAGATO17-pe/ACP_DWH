"""
conexion.py
===========
Conexión a SQL Server via pyodbc + SQLAlchemy.

Estrategia de carga del .env (del menos al más prioritario):
  1. .env raíz del proyecto  (ACP Proyecciones/.env)  — valores por defecto compartidos
  2. .env local de config    (ETL/config/.env)          — sobreescrituras opcionales por entorno
  3. Variables del sistema   (OS env vars)              — siempre ganan

El engine es un singleton por proceso: se crea una sola vez y se reutiliza
en todas las llamadas. El pool de SQLAlchemy gestiona las conexiones físicas.
"""

import os
import threading
import urllib
import warnings
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning

# ── Rutas ─────────────────────────────────────────────────────────────────────
_DIR_CONFIG      = Path(__file__).resolve().parent          # ETL/config/
_DIR_PROYECTO    = _DIR_CONFIG.parents[1]                   # ACP Proyecciones/

# Carga en orden: raíz → local (override=True en el local para permitir sobreescritura)
load_dotenv(_DIR_PROYECTO / ".env", override=False)         # valores compartidos
load_dotenv(_DIR_CONFIG   / ".env", override=True)          # ajustes locales opcionales

# ── Silenciar aviso de versión ODBC ───────────────────────────────────────────
warnings.filterwarnings(
    "ignore",
    message=r"Unrecognized server version info '17\..*'\.",
    category=SAWarning,
)

_engine: Engine | None = None
_engine_lock = threading.Lock()


def _construir_cadena_pyodbc() -> str:
    servidor = os.getenv("DB_SERVIDOR", ".")
    base     = os.getenv("DB_NOMBRE",   "ACP_DataWarehose_Proyecciones")
    usuario  = os.getenv("DB_USUARIO")
    clave    = os.getenv("DB_CLAVE")
    driver   = os.getenv("DB_DRIVER",   "SQL Server")
    entorno  = os.getenv("ACP_ENTORNO", "dev")
    trust    = "yes" if entorno == "dev" else "no"

    # El driver legacy "SQL Server" no admite TrustServerCertificate ni Encrypt.
    # Los drivers modernos ODBC 17/18 sí los soportan.
    es_legacy = "ODBC" not in driver

    if not usuario:
        cadena = (
            f"DRIVER={{{driver}}};"
            f"SERVER={servidor};"
            f"DATABASE={base};"
            f"Trusted_Connection=yes;"
            f"APP=ACP_ETL_Pipeline;"
        )
    else:
        cadena = (
            f"DRIVER={{{driver}}};"
            f"SERVER={servidor};"
            f"DATABASE={base};"
            f"UID={usuario};"
            f"PWD={clave};"
            f"APP=ACP_ETL_Pipeline;"
        )

    if not es_legacy:
        cadena += f"Encrypt=yes;TrustServerCertificate={trust};"

    return cadena


def obtener_engine() -> Engine:
    """
    Retorna el engine singleton del proceso.

    Pool configurado para una corrida ETL de larga duración:
    - pool_size=5        conexiones físicas mantenidas abiertas
    - max_overflow=2     conexiones extra permitidas en picos
    - pool_pre_ping=True descarta conexiones muertas antes de usarlas
    - pool_recycle=1800  renueva conexiones cada 30 min
    """
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        cadena_pyodbc = _construir_cadena_pyodbc()
        cadena_url = (
            "mssql+pyodbc:///?odbc_connect="
            + urllib.parse.quote_plus(cadena_pyodbc)
        )
        _engine = create_engine(
            cadena_url,
            fast_executemany=True,
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

    return _engine


def resetear_engine() -> None:
    """
    Descarta el singleton y cierra todas las conexiones del pool.
    Usar solo en tests o cuando cambie la configuración de BD en caliente.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None


def verificar_conexion() -> bool:
    """Ping liviano a la BD. Retorna True si la conexión es exitosa."""
    try:
        engine = obtener_engine()
        with engine.connect() as conn:
            fila = conn.execute(
                text("SELECT DB_NAME() AS base_activa")
            ).fetchone()
            print(f"  [OK] Conectado a: {fila.base_activa}")
            return True
    except Exception as error:
        print(f"  [ERROR] Conexion: {error}")
        return False


if __name__ == "__main__":
    verificar_conexion()
