"""
repositorios/repo_cuarentena.py
================================
Todas las consultas SQL relacionadas con MDM.Cuarentena.

Contrato:
- Recibe parámetros tipados.
- Retorna dicts o structs simples.
- Propaga ErrorBaseDatos o ErrorRecursoNoEncontrado según corresponda.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from nucleo.conexion import obtener_engine
from nucleo.excepciones import ErrorBaseDatos, ErrorRecursoNoEncontrado
from nucleo.logging import obtener_logger

log = obtener_logger(__name__)


def listar_pendientes(
    pagina: int = 1,
    tamano: int = 20,
    tabla_filtro: str | None = None,
) -> dict:
    """
    Lista registros PENDIENTES de MDM.Cuarentena con paginación server-side.
    Retorna: {total, pagina, tamano, datos: list[dict]}
    """
    offset = (pagina - 1) * tamano
    parametros: dict = {"offset": offset, "tamano": tamano}
    clausula_filtro = ""
    if tabla_filtro:
        clausula_filtro = "AND Tabla_Origen LIKE :tabla_filtro"
        parametros["tabla_filtro"] = f"%{tabla_filtro}%"

    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text(f"""
                    SELECT
                        CAST(ID_Cuarentena AS VARCHAR(30)) AS id_registro,
                        Tabla_Origen        AS tabla_origen,
                        Campo_Origen        AS columna_origen,
                        Valor_Recibido      AS valor_raw,
                        NULL                AS nombre_archivo,
                        CONVERT(VARCHAR(19), Fecha_Ingreso, 120) AS fecha_ingreso,
                        Estado              AS estado,
                        Motivo              AS motivo,
                        ID_Registro_Origen  AS id_registro_origen,
                        COUNT(*) OVER()     AS total_rows
                    FROM MDM.Cuarentena WITH (NOLOCK)
                    WHERE Estado = 'PENDIENTE'
                    {clausula_filtro}
                    ORDER BY Fecha_Ingreso DESC, ID_Cuarentena DESC
                    OFFSET :offset ROWS FETCH NEXT :tamano ROWS ONLY
                """),
                parametros,
            ).fetchall()

        total = 0
        datos = []
        if filas:
            total = filas[0]._mapping["total_rows"]
            for fila in filas:
                d = dict(fila._mapping)
                d.pop("total_rows", None)
                datos.append(d)

        return {
            "total":  total,
            "pagina": pagina,
            "tamano": tamano,
            "datos":  datos,
        }
    except SQLAlchemyError:
        log.exception("Error al listar cuarentena")
        raise ErrorBaseDatos()


def contar_por_estado() -> dict[str, int]:
    """
    Devuelve el conteo de registros agrupado por Estado.
    Retorna: {"PENDIENTE": N, "RESUELTO": M, "DESCARTADO": K, ...}
    """
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text("SELECT Estado, COUNT(*) AS total FROM MDM.Cuarentena GROUP BY Estado")
            ).fetchall()
        return {fila.Estado: fila.total for fila in filas}
    except SQLAlchemyError:
        log.exception("Error al contar registros de cuarentena por estado")
        raise ErrorBaseDatos()


def marcar_resuelto(
    tabla_origen: str,
    id_registro: str,
    valor_canonico: str,
    analista: str,
    fecha_resolucion: datetime | None = None,
) -> int:
    """
    Marca un registro como RESUELTO.
    Retorna rowcount (0 si no encontró el registro PENDIENTE).
    """
    fecha = fecha_resolucion or datetime.now()
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("""
                    UPDATE MDM.Cuarentena
                    SET
                        Estado            = 'RESUELTO',
                        Valor_Corregido   = :valor_canonico,
                        Aprobado_Por      = :analista,
                        Fecha_Resolucion  = :fecha_resolucion
                    WHERE ID_Cuarentena = :id_registro
                      AND Tabla_Origen  = :tabla_origen
                      AND Estado        = 'PENDIENTE'
                """),
                {
                    "id_registro":      id_registro,
                    "tabla_origen":     tabla_origen,
                    "valor_canonico":   valor_canonico,
                    "analista":         analista,
                    "fecha_resolucion": fecha,
                },
            )
            return resultado.rowcount
    except SQLAlchemyError:
        log.exception("Error al resolver cuarentena", extra={"id_registro": id_registro})
        raise ErrorBaseDatos()


def marcar_descartado(
    tabla_origen: str,
    id_registro: str,
    analista: str,
    fecha_resolucion: datetime | None = None,
) -> int:
    """
    Marca un registro como DESCARTADO.
    Retorna rowcount (0 si no encontró el registro PENDIENTE).
    """
    fecha = fecha_resolucion or datetime.now()
    try:
        with obtener_engine().begin() as con:
            resultado = con.execute(
                text("""
                    UPDATE MDM.Cuarentena
                    SET
                        Estado            = 'DESCARTADO',
                        Aprobado_Por      = :analista,
                        Fecha_Resolucion  = :fecha_resolucion
                    WHERE ID_Cuarentena = :id_registro
                      AND Tabla_Origen  = :tabla_origen
                      AND Estado        = 'PENDIENTE'
                """),
                {
                    "id_registro":      id_registro,
                    "tabla_origen":     tabla_origen,
                    "analista":         analista,
                    "fecha_resolucion": fecha,
                },
            )
            return resultado.rowcount
    except SQLAlchemyError:
        log.exception("Error al descartar cuarentena", extra={"id_registro": id_registro})
        raise ErrorBaseDatos()
def obtener_resumen() -> dict:
    """
    Retorna el conteo de registros agrupados por estado.
    Útil para badges en la UI sin descargar toda la data.
    """
    try:
        with obtener_engine().connect() as con:
            filas = con.execute(
                text("""
                    SELECT
                        Estado AS estado,
                        COUNT(*) AS total
                    FROM MDM.Cuarentena WITH (NOLOCK)
                    GROUP BY Estado
                """)
            ).fetchall()

        resumen = {"PENDIENTE": 0, "RESUELTO": 0, "DESCARTADO": 0, "TOTAL": 0}
        total_acumulado = 0
        for fila in filas:
            estado = str(fila._mapping["estado"]).upper()
            cantidad = int(fila._mapping["total"])
            resumen[estado] = cantidad
            total_acumulado += cantidad

        resumen["TOTAL"] = total_acumulado
        return resumen
    except SQLAlchemyError:
        log.exception("Error al obtener resumen de cuarentena")
        raise ErrorBaseDatos()
