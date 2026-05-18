"""
nucleo/conexion.py
==================
Compatibilidad: este modulo delega en comun/conexion.py.

La logica canonica vive en `comun/conexion.py` (compartida con ETL).
Mantenemos las firmas existentes para no tocar los call sites del backend.
"""

from __future__ import annotations

import sys
from pathlib import Path

_DIR_PROYECTO = Path(__file__).resolve().parents[2]
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import obtener_engine, resetear_engine, verificar_conexion  # noqa: E402
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

__all__ = ["obtener_engine", "resetear_engine", "verificar_conexion"]
