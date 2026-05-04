
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

def explore_silver_cols():
    engine = get_engine()
    tables = [
        "Silver.Fact_Cosecha_SAP",
        "Silver.Fact_Conteo_Fenologico",
        "Silver.Fact_Evaluacion_Pesos"
    ]
    
    with engine.connect() as conn:
        for table in tables:
            print(f"\n--- Columns of {table} ---")
            schema, name = table.split(".")
            query = f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{name}'"
            try:
                df = pd.read_sql(text(query), conn)
                print(df)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    explore_silver_cols()
