
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

def search_cosecha_data():
    engine = get_engine()
    query = """
    SELECT s.name as SchemaName, t.name as TableName, p.rows
    FROM sys.tables t
    INNER JOIN sys.indexes i ON t.object_id = i.object_id
    INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE (t.name LIKE '%Cosecha%' OR t.name LIKE '%Prod%')
    AND i.index_id IN (0,1)
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
        print(df)

if __name__ == "__main__":
    search_cosecha_data()
