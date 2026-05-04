
import os
import urllib
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def get_engine():
    load_dotenv("D:/Proyecto2026/ACP_DWH/ACP Proyecciones/.env")
    servidor = os.getenv('DB_SERVIDOR', 'LCP-PAG-PRACTIC')
    base     = os.getenv('DB_NOMBRE', 'ACP_DataWarehose_Proyecciones')
    usuario  = os.getenv('DB_USUARIO')
    clave    = os.getenv('DB_CLAVE')
    driver   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

    if not usuario:
        cadena_pyodbc = f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};Trusted_Connection=yes;TrustServerCertificate=yes;'
    else:
        cadena_pyodbc = f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};UID={usuario};PWD={clave};TrustServerCertificate=yes;'

    url = 'mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(cadena_pyodbc)
    return create_engine(url)

def explore_db():
    engine = get_engine()
    queries = {
        "Schemas": "SELECT name FROM sys.schemas WHERE principal_id = 1",
        "Tables_Silver": "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Silver'",
        "Tables_Gold": "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Gold'",
        "Tables_Fact": "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'Fact%'"
    }
    
    with engine.connect() as conn:
        for name, query in queries.items():
            print(f"\n--- {name} ---")
            try:
                df = pd.read_sql(text(query), conn)
                print(df)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    explore_db()
