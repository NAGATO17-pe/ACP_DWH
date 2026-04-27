"""
conexion.py
===========
Conexion a SQL Server via pyodbc + SQLAlchemy.
Usa odbc_connect directo para evitar problemas de parsing de URL.

El engine es un singleton por proceso: se crea una sola vez y se
reutiliza en todas las llamadas. El pool interno de SQLAlchemy
gestiona las conexiones físicas, evitando abrir/cerrar sockets en
cada módulo que llame a obtener_engine().
"""

import os
import threading
import urllib
import warnings
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning

load_dotenv()

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

    if not usuario:
        return (
            f'DRIVER={{{driver}}};'
            f'SERVER={servidor};'
            f'DATABASE={base};'
            f'Trusted_Connection=yes;'
            f'TrustServerCertificate=yes;'
        )
    return (
        f'DRIVER={{{driver}}};'
        f'SERVER={servidor};'
        f'DATABASE={base};'
        f'UID={usuario};'
        f'PWD={clave};'
        f'TrustServerCertificate=yes;'
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
            pool_size=5,
            max_overflow=2,
            pool_pre_ping=True,
            pool_recycle=1800,
        )

    return _engine


def resetear_engine() -> None:
    """
    Descarta el singleton y cierra todas las conexiones del pool.
    Llamar solo en tests o cuando cambie la configuración de BD en caliente.
    """
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None


def verificar_conexion() -> bool:
    try:
        engine = obtener_engine()
        with engine.connect() as conexion:
            resultado = conexion.execute(
                text('SELECT DB_NAME() AS base_activa')
            )
            fila = resultado.fetchone()
            print(f'Conectado a: {fila.base_activa}')
            return True
    except Exception as error:
        print(f'Error de conexion: {error}')
        return False


if __name__ == '__main__':
    verificar_conexion()
