"""
repositorios/repo_catalogos.py
================================
Todas las consultas SQL relacionadas con catálogos MDM y dimensiones Silver.
Todos los métodos son de sólo lectura.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)

_CATALOGOS = {
    "variedades": {
        "sql_count": "SELECT COUNT(*) FROM MDM.Catalogo_Variedades",
        "sql_datos": """
            SELECT
                Nombre_Canonico AS nombre_canonico,
                Breeder         AS breeder,
                Es_Activa       AS es_activa
            FROM MDM.Catalogo_Variedades
            ORDER BY Es_Activa DESC, Nombre_Canonico
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar variedades MDM",
    },
    "dim_variedades": {
        "sql_count": "SELECT COUNT(*) FROM Silver.Dim_Variedad",
        "sql_datos": """
            SELECT
                ID_Variedad        AS id_variedad,
                Nombre_Variedad    AS nombre_variedad,
                Breeder            AS breeder,
                Es_Activa          AS es_activa,
                Fecha_Creacion     AS fecha_creacion,
                Fecha_Modificacion AS fecha_modificacion
            FROM Silver.Dim_Variedad
            ORDER BY Es_Activa DESC, Nombre_Variedad
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar Dim_Variedad Silver",
    },
    "geografia": {
        "sql_count": "SELECT COUNT(*) FROM Silver.Dim_Geografia WHERE Es_Vigente = 1",
        "sql_datos": """
            SELECT
                Fundo               AS fundo,
                Sector              AS sector,
                Modulo              AS modulo,
                Turno               AS turno,
                Valvula             AS valvula,
                Cama                AS cama,
                Es_Test_Block       AS es_test_block,
                Codigo_SAP_Campo    AS codigo_sap_campo,
                Es_Vigente          AS es_vigente
            FROM Silver.Dim_Geografia
            WHERE Es_Vigente = 1
            ORDER BY Fundo, Sector, Modulo, Turno, Valvula, Cama
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar geografÃ­a",
    },
    "personal": {
        "sql_count": "SELECT COUNT(*) FROM Silver.Dim_Personal",
        "sql_datos": """
            SELECT
                DNI                 AS dni,
                Nombre_Completo     AS nombre_completo,
                Rol                 AS rol,
                Sexo                AS sexo,
                ID_Planilla         AS id_planilla,
                Pct_Asertividad     AS pct_asertividad,
                Dias_Ausentismo     AS dias_ausentismo
            FROM Silver.Dim_Personal
            ORDER BY Nombre_Completo
            OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
        """,
        "mensaje_error": "Error al listar personal",
    },
}


_TTL_CATALOGOS = 3600   # 1 hora — datos estáticos
_TTL_CUARENTENA = 120   # 2 minutos — datos operativos


def _paginar(
    con,
    sql_count: str,
    sql_datos: str,
    params: dict,
    pagina: int,
    tamano: int,
) -> dict:
    """
    Helper interno: ejecuta count + query paginada y retorna el envelope estándar.
    """
    total = con.execute(text(sql_count), params).scalar() or 0
    filas = con.execute(text(sql_datos), params).fetchall()
    return {
        "total":  total,
        "pagina": pagina,
        "tamano": tamano,
        "datos":  [dict(fila._mapping) for fila in filas],
    }


def _listar_catalogo(nombre_catalogo: str, pagina: int = 1, tamano: int = 20) -> dict:
    configuracion = _CATALOGOS[nombre_catalogo]
    desplazamiento = (pagina - 1) * tamano
    params = {"offset": desplazamiento, "tamano": tamano}
    try:
        with obtener_engine().connect() as con:
            return _paginar(
                con,
                sql_count=configuracion["sql_count"],
                sql_datos=configuracion["sql_datos"],
                params=params,
                pagina=pagina,
                tamano=tamano,
            )
    except SQLAlchemyError:
        log.exception(configuracion["mensaje_error"])
        raise ErrorBaseDatos()


def listar_variedades(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee MDM.Catalogo_Variedades (catálogo maestro MDM)."""
    return _listar_catalogo("variedades", pagina=pagina, tamano=tamano)


def listar_dim_variedades(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Variedad (dimensión DWH ya homologada)."""
    return _listar_catalogo("dim_variedades", pagina=pagina, tamano=tamano)


# ── Escritura sobre Silver.Dim_Variedad (solo admin) ───────────────────────────────

def insertar_dim_variedad(nombre_variedad: str, breeder: str | None) -> dict:
    """
    Inserta una nueva variedad en Silver.Dim_Variedad.
    Retorna el registro creado: {id_variedad, nombre_variedad, breeder}.
    Lanza ErrorBaseDatos si ya existe (UNIQUE constraint en Nombre_Variedad).
    """
    try:
        with obtener_engine().begin() as con:
            fila = con.execute(
                text("""
                    INSERT INTO Silver.Dim_Variedad
                        (Nombre_Variedad, Breeder, Es_Activa, Fecha_Creacion)
                    OUTPUT
                        INSERTED.ID_Variedad,
                        INSERTED.Nombre_Variedad,
                        INSERTED.Breeder,
                        INSERTED.Es_Activa,
                        INSERTED.Fecha_Creacion
                    VALUES (:nombre, :breeder, 1, GETDATE())
                """),
                {"nombre": nombre_variedad, "breeder": breeder},
            ).fetchone()
        return dict(fila._mapping)
    except SQLAlchemyError as exc:
        msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
        if "UQ_DimVariedad_Nombre" in msg or "UNIQUE" in msg.upper():
            raise ValueError(f"Ya existe una variedad con el nombre '{nombre_variedad}'.")
        log.exception("Error al insertar dim variedad", extra={"nombre": nombre_variedad})
        raise ErrorBaseDatos()


def cambiar_estado_dim_variedad(id_variedad: int, es_activa: bool) -> dict:
    """
    Activa o desactiva una variedad (soft-delete) en Silver.Dim_Variedad.
    Retorna el registro actualizado.
    Lanza ValueError si el ID no existe.
    """
    try:
        with obtener_engine().begin() as con:
            fila = con.execute(
                text("""
                    UPDATE Silver.Dim_Variedad
                    SET Es_Activa          = :activa,
                        Fecha_Modificacion = GETDATE()
                    OUTPUT
                        INSERTED.ID_Variedad,
                        INSERTED.Nombre_Variedad,
                        INSERTED.Breeder,
                        INSERTED.Es_Activa,
                        INSERTED.Fecha_Modificacion
                    WHERE ID_Variedad = :id
                """),
                {"id": id_variedad, "activa": 1 if es_activa else 0},
            ).fetchone()
        if fila is None:
            raise ValueError(f"No existe variedad con ID {id_variedad}.")
        return dict(fila._mapping)
    except ValueError:
        raise
    except SQLAlchemyError:
        log.exception("Error al cambiar estado dim variedad", extra={"id": id_variedad})
        raise ErrorBaseDatos()


def listar_geografia(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Geografia vigente con paginación server-side."""
    return _listar_catalogo("geografia", pagina=pagina, tamano=tamano)


def listar_personal(pagina: int = 1, tamano: int = 20) -> dict:
    """Lee Silver.Dim_Personal con paginación server-side."""
    return _listar_catalogo("personal", pagina=pagina, tamano=tamano)
