import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
with engine.connect() as conn:
    print("--- TABLAS EN ESQUEMA SILVER ---")
    res = conn.execute(text("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'Silver'
        ORDER BY TABLE_NAME
    """))
    for row in res.fetchall():
        print(row[0])

    print("\n--- COLUMNAS DE Fact_Evaluacion_Vegetativa ---")
    try:
        res_cols = conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa'
            ORDER BY ORDINAL_POSITION
        """))
        for row in res_cols.fetchall():
            print(f"{row[0]} ({row[1]})")
    except Exception as e:
        print("Error:", e)
