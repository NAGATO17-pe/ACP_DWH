"""
sql_lotes.py
============
Utilidades reutilizables para ejecutar sentencias SQL en lotes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.elements import TextClause

from utils.contexto_transaccional import RecursoDB, administrar_recurso_db


TAM_LOTE_DEFECTO = 2000


def _normalizar_sentencia(sentencia: str | TextClause) -> TextClause:
    return text(sentencia) if isinstance(sentencia, str) else sentencia


# ── Helper compartido para tablas temporales ───────────────────────────────────

def crear_e_insertar_temp(
    conexion: Connection,
    nombre_temp: str,
    columnas_con_tipos: list[tuple[str, str]],
    datos: list[tuple],
) -> None:
    """
    Crea una #Temp table y la carga con fast_executemany en la misma sesión.

    Consolida la lógica que estaba duplicada entre _base_processor._crear_tabla_temp_en_sesion
    + _insertar_en_temp y marcar_estado_carga_por_ids. Cualquier cambio en el
    patrón DROP/CREATE/INSERT afecta a ambos consumidores desde un único lugar.

    Parámetros
    ----------
    conexion          : conexión activa dentro de la transacción del pipeline.
    nombre_temp       : nombre de la tabla temporal (ej. '#Temp_Batch_CosechaSAP').
    columnas_con_tipos: lista de (nombre_col, tipo_sql) para el DDL de la temp.
    datos             : filas como lista de tuplas, en el mismo orden que columnas_con_tipos.
    """
    cols_ddl      = ', '.join(f'[{col}] {tipo}' for col, tipo in columnas_con_tipos)
    cols_quoted   = ', '.join(f'[{col}]' for col, _ in columnas_con_tipos)
    placeholders  = ', '.join('?' for _ in columnas_con_tipos)

    conexion.execute(text(
        f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"
    ))
    conexion.execute(text(f"CREATE TABLE {nombre_temp} ({cols_ddl})"))

    if datos:
        sql_insert = f"INSERT INTO {nombre_temp} ({cols_quoted}) VALUES ({placeholders})"
        # exec_driver_sql envía SQL nativo al driver pyodbc respetando
        # fast_executemany del engine, sin acceder a atributos internos de SQLAlchemy.
        conexion.exec_driver_sql(sql_insert, datos)


# ── Funciones públicas ─────────────────────────────────────────────────────────

def ejecutar_en_lotes(
    conexion: Connection,
    sentencia: str | TextClause,
    payload: Sequence[Mapping],
    tam_lote: int = TAM_LOTE_DEFECTO,
) -> int:
    if not payload:
        return 0

    sentencia_sql = _normalizar_sentencia(sentencia)
    for inicio in range(0, len(payload), tam_lote):
        conexion.execute(sentencia_sql, list(payload[inicio:inicio + tam_lote]))

    return len(payload)


def ejecutar_en_lotes_con_recurso(
    recurso_db: RecursoDB,
    sentencia: str | TextClause,
    payload: Sequence[Mapping],
    tam_lote: int = TAM_LOTE_DEFECTO,
) -> int:
    if not payload:
        return 0

    with administrar_recurso_db(recurso_db) as conexion:
        return ejecutar_en_lotes(conexion, sentencia, payload, tam_lote)


def ejecutar_en_lotes_con_engine(
    engine: Engine,
    sentencia: str | TextClause,
    payload: Sequence[Mapping],
    tam_lote: int = TAM_LOTE_DEFECTO,
) -> int:
    return ejecutar_en_lotes_con_recurso(engine, sentencia, payload, tam_lote)


def marcar_estado_carga_por_ids(
    recurso_db: RecursoDB,
    tabla_origen: str,
    columna_id: str,
    ids: Sequence[int | None],
    estado: str = 'PROCESADO',
    tam_lote: int = TAM_LOTE_DEFECTO,
) -> int:
    ids_limpios = list({int(i) for i in ids if i is not None})
    if not ids_limpios:
        return 0

    with administrar_recurso_db(recurso_db) as conexion:
        nombre_temp = f"#Temp_Update_{tabla_origen.split('.')[-1]}"

        crear_e_insertar_temp(
            conexion,
            nombre_temp,
            columnas_con_tipos=[('id_origen', 'BIGINT PRIMARY KEY')],
            datos=[(i,) for i in ids_limpios],
        )

        resultado = conexion.execute(
            text(f"""
                UPDATE orig
                SET    Estado_Carga = :estado
                FROM   {tabla_origen} orig
                INNER JOIN {nombre_temp} tmp ON orig.{columna_id} = tmp.id_origen
            """),
            {'estado': estado},
        )

        conexion.execute(text(
            f"IF OBJECT_ID('tempdb..{nombre_temp}') IS NOT NULL DROP TABLE {nombre_temp}"
        ))

        return resultado.rowcount
