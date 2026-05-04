import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
tables = ['Fact_Maduracion', 'Fact_Peladas', 'Fact_Cosecha_SAP', 'Fact_Evaluacion_Pesos', 'Fact_Conteo_Fenologico']

with engine.connect() as conn:
    for t in tables:
        print(f"\n--- {t} ---")
        res = conn.execute(text(f"SELECT COLUMN_NAME, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = '{t}'"))
        for row in res:
            if row.IS_NULLABLE == 'NO':
                print(f"REQUIRED: {row.COLUMN_NAME}")
