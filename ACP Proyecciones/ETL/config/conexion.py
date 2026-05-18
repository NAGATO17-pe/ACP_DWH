"""
config/conexion.py
==================
Compatibilidad: este modulo delega en comun/conexion.py.

La logica canonica vive en `comun/conexion.py` (compartida con backend).
Mantenemos las firmas existentes para no tocar los call sites del ETL.
"""

from __future__ import annotations

import sys
from pathlib import Path

_DIR_PROYECTO = Path(__file__).resolve().parent.parent.parent
if str(_DIR_PROYECTO) not in sys.path:
    sys.path.insert(0, str(_DIR_PROYECTO))

from comun.conexion import (  # noqa: E402
    obtener_engine,
    resetear_engine,
)
from comun.conexion import verificar_conexion as _verificar_conexion_dict  # noqa: E402


def verificar_conexion() -> bool:
    """
    Compat: el ETL espera bool, comun/conexion devuelve dict.
    Mantenemos la firma original imprimiendo el resultado como antes.
    """
    info = _verificar_conexion_dict()
    if info.get("conectado"):
        print(f"Conectado a: {info.get('base_datos')}")
        return True
    print(f"Error de conexion: {info.get('error', 'desconocido')}")
    return False


__all__ = ["obtener_engine", "resetear_engine", "verificar_conexion"]


if __name__ == "__main__":
    verificar_conexion()
