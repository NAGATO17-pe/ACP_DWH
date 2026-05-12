import sys
import os
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
tables = ['Silver.Fact_Cosecha_SAP', 'Silver.Fact_Maduracion', 'Silver.Fact_Peladas']

with engine.connect() as conn:
    for t in tables:
        schema, name = t.split('.')
        print(f"--- {t} ---")
        res = conn.execute(text(f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}'
            ORDER BY ORDINAL_POSITION
        """))
        for row in res:
            print(f"  {row.COLUMN_NAME} ({row.DATA_TYPE})")
