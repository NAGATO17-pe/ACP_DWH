"""
utils/db.py — Capa de datos del Portal MDM ACP
================================================
Engine SQLAlchemy compartido para el Portal Streamlit.

Estrategia de carga del .env (del menos al más prioritario):
  1. .env raíz del proyecto  (ACP Proyecciones/.env)  — valores compartidos con ETL y Backend
  2. Variables del sistema   (OS env vars)              — siempre ganan

Las páginas del portal usan utils/api_client.py para operaciones normales.
Este módulo se usa solo en consola_admin.py para acceso SQL directo.
"""

import os
import urllib
import warnings
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SAWarning

# ── Carga de configuración ────────────────────────────────────────────────────
_DIR_PROYECTO = Path(__file__).resolve().parents[2]   # ACP Proyecciones/
load_dotenv(_DIR_PROYECTO / ".env", override=False)   # cede ante OS env vars

warnings.filterwarnings(
    "ignore",
    message=r"Unrecognized server version info '17\..*'\.",
    category=SAWarning,
)


# ── Engine con pool tuning ────────────────────────────────────────────────────

@st.cache_resource
def obtener_engine():
    """Engine Streamlit compartido. Misma config de BD que ETL y Backend."""
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
    """Engine compartido sin dependencias del módulo ETL."""
    from dotenv import load_dotenv
    load_dotenv()

    servidor = os.getenv('DB_SERVIDOR', 'LCP-PAG-PRACTIC')
    base     = os.getenv('DB_NOMBRE', 'ACP_DataWarehouse_Proyecciones')
    usuario  = os.getenv('DB_USUARIO')
    clave    = os.getenv('DB_CLAVE')
    driver   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

    if not usuario:
        cadena_pyodbc = (
            f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};"
            f"Trusted_Connection=yes;APP=ACP_Portal;"
        )
    else:
        cadena_pyodbc = (
            f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};"
            f"UID={usuario};PWD={clave};APP=ACP_Portal;"
        )

    if not es_legacy:
        cadena_pyodbc += f"Encrypt=yes;TrustServerCertificate={trust};"

    url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(cadena_pyodbc)
    return create_engine(url, fast_executemany=True, pool_pre_ping=True)


# ── Queries estándar ──────────────────────────────────────────────────────────

def ejecutar_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """Ejecuta una consulta SELECT y retorna un DataFrame completo."""
    with obtener_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def ejecutar_comando(query: str, params: dict | None = None) -> int:
    """Ejecuta un comando (INSERT/UPDATE/DELETE) y retorna las filas afectadas."""
    with obtener_engine().begin() as conn:
        res = conn.execute(text(query), params or {})
        return res.rowcount


def health_check() -> dict:
    """
    Diagnóstico detallado de la conexión a SQL Server.
    Retorna un dict con: conectado, base_datos, version, latencia_ms, uptime.
    """
    import time

    info: dict = {
        "conectado":   False,
        "base_datos":  "—",
        "version":     "—",
        "latencia_ms": "—",
        "uptime":      "—",
    }
    try:
        t0 = time.perf_counter()
        with obtener_engine().connect() as conn:
            row = conn.execute(text("""
                SELECT
                    DB_NAME()                                       AS base,
                    SERVERPROPERTY('ProductVersion')                AS ver,
                    DATEDIFF(HOUR, sqlserver_start_time, GETDATE()) AS uptime_h
                FROM sys.dm_os_sys_info
            """)).fetchone()
        t1 = time.perf_counter()

        info["conectado"]   = True
        info["base_datos"]  = str(row.base)
        info["version"]     = f"SQL {row.ver}"
        info["latencia_ms"] = f"{(t1 - t0) * 1000:.0f} ms"
        info["uptime"]      = f"{row.uptime_h}h"
    except Exception:
        pass

    return info
