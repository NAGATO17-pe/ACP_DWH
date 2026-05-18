import os, sys, urllib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
servidor = os.getenv('DB_SERVIDOR', 'LCP-PAG-PRACTIC')
base     = os.getenv('DB_NOMBRE', 'ACP_DataWarehose_Proyecciones')
driver   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
cadena = (f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};'
          f'Trusted_Connection=yes;TrustServerCertificate=yes;')
url = 'mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(cadena)
engine = create_engine(url)

query = """
SELECT TOP 10 
    f.ID_Campana,
    t.Anio,
    t.Semana_ISO,
    COUNT(*) as Regs
FROM Silver.Fact_Conteo_Fenologico f
JOIN Silver.Dim_Tiempo t ON f.ID_Tiempo = t.ID_Tiempo
GROUP BY f.ID_Campana, t.Anio, t.Semana_ISO
ORDER BY t.Anio DESC, t.Semana_ISO DESC
"""
with engine.connect() as conn:
    df = pd.read_sql(query, conn)
    print(df)
