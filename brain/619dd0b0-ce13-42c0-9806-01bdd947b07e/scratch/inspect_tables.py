
import sqlalchemy
from sqlalchemy import create_engine, text
import pandas as pd

CONN_STR = "mssql+pyodbc://sa:Nagato17!!@localhost:1433/ACP_DataWarehose_Proyecciones?driver=ODBC+Driver+17+for+SQL+Server"

def inspect_db():
    engine = create_engine(CONN_STR)
    with engine.connect() as conn:
        # List all tables and their schemas
        query = """
        SELECT SCHEMA_NAME(schema_id) AS schema_name, name AS table_name
        FROM sys.tables
        ORDER BY schema_name, table_name
        """
        df_tables = pd.read_sql(query, conn)
        print("TABLES IN DB:")
        print(df_tables.to_string())

        # Check for specific tables mentioned in SixWek.py
        target_tables = [
            'fenologia_produccion', 'conteo_fruta', 'maduracion', 
            'proyeccion_pesos', 'seguimiento_productividad', 'reporte_cosecha'
        ]
        
        for table in target_tables:
            print(f"\nSearching for table like '{table}'...")
            search_query = f"SELECT SCHEMA_NAME(schema_id) AS s, name FROM sys.tables WHERE name LIKE '%{table}%'"
            res = conn.execute(text(search_query)).fetchall()
            if res:
                for r in res:
                    print(f"FOUND: {r.s}.{r.name}")
            else:
                print("NOT FOUND")

if __name__ == "__main__":
    inspect_db()
