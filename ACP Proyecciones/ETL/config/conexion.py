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
warnings.filterwarnings(
    'ignore',
    message=r"Unrecognized server version info '17\..*'\.  Some SQL Server features may not function properly\.",
    category=SAWarning,
)

_engine: Engine | None = None
_engine_lock = threading.Lock()


def _construir_cadena_pyodbc() -> str:
    servidor = os.getenv('DB_SERVIDOR', 'LCP-PAG-PRACTIC')
    base     = os.getenv('DB_NOMBRE', 'ACP_DataWarehose_Proyecciones')
    usuario  = os.getenv('DB_USUARIO')
    clave    = os.getenv('DB_CLAVE')
    driver   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

    entorno = os.getenv('ACP_ENTORNO', 'dev')
    trust   = 'yes' if entorno == 'dev' else 'no'

    if not usuario:
        return (
            f'DRIVER={{{driver}}};'
            f'SERVER={servidor};'
            f'DATABASE={base};'
            f'Trusted_Connection=yes;'
            f'Encrypt=yes;'
            f'TrustServerCertificate={trust};'
            f'APP=ACP_ETL_Pipeline;'
        )
    return (
        f'DRIVER={{{driver}}};'
        f'SERVER={servidor};'
        f'DATABASE={base};'
        f'UID={usuario};'
        f'PWD={clave};'
        f'Encrypt=yes;'
        f'TrustServerCertificate={trust};'
        f'APP=ACP_ETL_Pipeline;'
    )


def obtener_engine() -> Engine:
    """
    Retorna el engine singleton del proceso.

    Pool configurado para una corrida ETL de larga duración:
    - pool_size=5      : conexiones físicas mantenidas abiertas
    - max_overflow=2   : conexiones extra permitidas en picos
    - pool_pre_ping=True : descarta conexiones muertas antes de usarlas
    - pool_recycle=1800  : renueva conexiones cada 30 min para evitar
                           drops por timeout del servidor SQL Server
    """
    global _engine
    if _engine is not None:
        return _engine

    with _engine_lock:
        if _engine is not None:
            return _engine

        cadena_pyodbc = _construir_cadena_pyodbc()
        cadena_url = (
            'mssql+pyodbc:///?odbc_connect='
            + urllib.parse.quote_plus(cadena_pyodbc)
        )
        _engine = create_engine(
            cadena_url,
            fast_executemany=True,
            pool_size=20,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

    return _engine


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
