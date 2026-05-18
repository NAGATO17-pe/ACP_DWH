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
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning


# Tiempo maximo (ms) que una query del ETL espera por un lock antes de
# fallar con error 1222. Evita que un huerfano bloquee indefinidamente.
LOCK_TIMEOUT_MS = int(os.getenv('ACP_LOCK_TIMEOUT_MS', '60000'))

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

        # En cada conexion nueva: LOCK_TIMEOUT (falla rapida si un huerfano
        # tiene locks) + XACT_ABORT ON (rollback automatico ante cualquier
        # error -> evita transacciones huerfanas si el pipeline crashea).
        @event.listens_for(_engine, 'connect')
        def _configurar_sesion(dbapi_conn, _connection_record):
            cur = dbapi_conn.cursor()
            try:
                cur.execute(f'SET LOCK_TIMEOUT {LOCK_TIMEOUT_MS};')
                cur.execute('SET XACT_ABORT ON;')
            finally:
                cur.close()

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


def limpiar_sesiones_huerfanas(
    minutos_inactivo: int = 5,
    nombre_aplicacion: str = 'ACP_ETL_Pipeline',
) -> list[int]:
    """
    Mata sesiones SQL Server que cumplen TODO esto:
      - program_name = nombre_aplicacion (default 'ACP_ETL_Pipeline')
      - status = 'sleeping'
      - tienen transaccion de usuario abierta
      - llevan >= minutos_inactivo sin actividad
      - NO son la sesion actual (@@SPID)

    Retorna lista de session_id matados. Uso tipico: arranque del pipeline,
    para liberar locks de una corrida previa que crasheo sin rollback.

    Requiere VIEW SERVER STATE + ALTER ANY CONNECTION. Si faltan permisos,
    falla silenciosamente con WARN (no rompe el pipeline).
    """
    engine = obtener_engine()
    matados: list[int] = []
    try:
        with engine.connect() as conexion:
            filas = conexion.execute(text("""
                SELECT s.session_id
                FROM sys.dm_exec_sessions s
                JOIN sys.dm_tran_session_transactions t
                  ON t.session_id = s.session_id
                WHERE s.program_name = :app
                  AND s.session_id <> @@SPID
                  AND s.status = 'sleeping'
                  AND t.is_user_transaction = 1
                  AND DATEDIFF(MINUTE, s.last_request_end_time, GETDATE()) >= :min
            """), {'app': nombre_aplicacion, 'min': minutos_inactivo}).fetchall()

            for (spid,) in filas:
                try:
                    conexion.execute(text(f'KILL {int(spid)};'))
                    matados.append(int(spid))
                except Exception as err_kill:
                    print(f'  WARN: no se pudo matar sesion {spid}: {err_kill}')

        if matados:
            print(f'  Liberadas {len(matados)} sesiones huerfanas: {matados}')
    except Exception as err:
        print(f'  WARN: limpiar_sesiones_huerfanas omitido: {err}')

    return matados


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
