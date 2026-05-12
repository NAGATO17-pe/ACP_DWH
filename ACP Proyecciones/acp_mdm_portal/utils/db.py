"""
utils/db.py — Capa de datos del Portal MDM ACP (Enterprise)
=============================================================
Acceso SQL directo para herramientas admin (consola_admin.py).
Las páginas del portal usan utils/api_client.py, no este módulo.
"""

import os
import urllib
import warnings

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SAWarning

warnings.filterwarnings(
    'ignore',
    message=r"Unrecognized server version info '17\..*'\.",
    category=SAWarning,
)


# ── Engine con pool tuning ────────────────────────────────────────────────────

@st.cache_resource
def obtener_engine():
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
            f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};'
            f'Trusted_Connection=yes;TrustServerCertificate=yes;'
        )
    else:
        cadena_pyodbc = (
            f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};'
            f'UID={usuario};PWD={clave};TrustServerCertificate=yes;'
        )

    url = 'mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(cadena_pyodbc)
    return create_engine(url, fast_executemany=True)


# ── Queries estándar ──────────────────────────────────────────────────────────

def ejecutar_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """Ejecuta una consulta SELECT y retorna un DataFrame completo."""
    with obtener_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


def health_check() -> dict:
    """
    Diagnóstico detallado de la conexión a SQL Server.
    Retorna un dict con: conectado, base_datos, version, latencia_ms, uptime.
    """
    import time

    info = {
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

