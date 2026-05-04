import sys
import os
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
sql_path = r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\sql_migrations\alter_fact_proyecciones_sixweek.sql"

with engine.begin() as conn:
    with open(sql_path, 'r') as f:
        sql = f.read()
    conn.execute(text(sql))
    print("Migration executed successfully.")
