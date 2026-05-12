"""
Verifica el rango de fechas disponible en las fuentes Silver que usa fact_sixweek.
"""
import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()

tablas = [
    ("Silver.Fact_Maduracion",      "ID_Tiempo", "Fecha_Evento"),
    ("Silver.Fact_Peladas",         "ID_Tiempo", "Fecha_Evento"),
    ("Silver.Fact_Cosecha_SAP",     "ID_Tiempo", "Fecha_Evento"),
    ("Silver.Fact_Conteo_Fenologico","ID_Tiempo","Fecha_Evaluacion"),
]

with engine.connect() as conn:
    for tabla, col_id, col_fecha in tablas:
        # Intentar con columna de fecha primero, si no existe usar MIN/MAX de ID_Tiempo
        try:
            q = f"""
                SELECT 
                    MIN({col_id})  AS id_min,
                    MAX({col_id})  AS id_max,
                    MIN({col_fecha}) AS fecha_min,
                    MAX({col_fecha}) AS fecha_max,
                    COUNT(*) AS total
                FROM {tabla}
            """
            row = conn.execute(text(q)).fetchone()
            print(f"\n{tabla}:")
            print(f"  Total filas : {row.total}")
            print(f"  ID_Tiempo   : {row.id_min} .. {row.id_max}")
            print(f"  Fechas      : {row.fecha_min} .. {row.fecha_max}")
        except Exception as e:
            print(f"\n{tabla}: ERROR -> {e}")
