
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

def verify_features():
    engine = get_engine()
    queries = {
        "Estados_Fenologicos": "SELECT ID_Estado_Fenologico, Nombre_Estado, Orden FROM Silver.Dim_Estado_Fenologico ORDER BY Orden",
        "Variedades": "SELECT TOP 10 ID_Variedad, Nombre_Variedad FROM Silver.Dim_Variedad",
        "Sample_Cosecha": "SELECT TOP 5 * FROM Silver.Fact_Cosecha_SAP WHERE Estado_DQ = 'OK'",
        "Sample_Fenologia": "SELECT TOP 5 * FROM Silver.Fact_Conteo_Fenologico WHERE Estado_DQ = 'OK'",
        "Sample_Pesos": "SELECT TOP 5 * FROM Silver.Fact_Evaluacion_Pesos WHERE Estado_DQ = 'OK'",
        "Data_Counts": """
            SELECT 'Cosecha' as Tab, COUNT(*) as Total FROM Silver.Fact_Cosecha_SAP UNION ALL
            SELECT 'Fenologia', COUNT(*) FROM Silver.Fact_Conteo_Fenologico UNION ALL
            SELECT 'Pesos', COUNT(*) FROM Silver.Fact_Evaluacion_Pesos
        """
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
    verify_features()
