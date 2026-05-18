
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

def inspect_bronce_values():
    engine = get_engine()
    query = "SELECT TOP 10 ID_Ciclo_Fenologico, Modulo_Raw, Organo_Raw, Valores_Raw FROM Bronce.Ciclos_Fenologicos"
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        print(df)

if __name__ == "__main__":
    inspect_bronce_values()
