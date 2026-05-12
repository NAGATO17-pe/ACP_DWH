import sys
import os
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
sql_path = r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\sql_migrations\dummy_data_sixweek.sql"

with engine.begin() as conn:
    with open(sql_path, 'r') as f:
        sql = f.read()
    
    # Split by semicolon but be careful with comments and other characters
    # For this simple script, splitting by semicolon is fine if we ignore empty ones
    statements = sql.split(';')
    for stmt in statements:
        if stmt.strip():
            conn.execute(text(stmt))
    print("Dummy data inserted successfully.")
