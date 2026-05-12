
import os
import sys
import pandas as pd
from sqlalchemy import text

# Add ETL to path to use project config
PROJECT_ROOT = r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones"
sys.path.append(os.path.join(PROJECT_ROOT, "ETL"))

from config.conexion import obtener_engine

def inspect_db():
    engine = obtener_engine()
    with engine.connect() as conn:
        print("TABLES IN ALL SCHEMAS:")
        query = """
        SELECT SCHEMA_NAME(schema_id) AS s, name 
        FROM sys.tables 
        ORDER BY s, name
        """
        df = pd.read_sql(query, conn)
        print(df.to_string())

        # Check for tables mentioned in SixWek.py
        targets = ['fenologia', 'conteo', 'maduracion', 'peso', 'productividad', 'cosecha']
        for t in targets:
            print(f"\nLooking for '{t}':")
            sq = f"SELECT SCHEMA_NAME(schema_id) AS s, name FROM sys.tables WHERE name LIKE '%{t}%'"
            res = conn.execute(text(sq)).fetchall()
            for r in res:
                print(f"  -> {r.s}.{r.name}")

if __name__ == "__main__":
    inspect_db()
