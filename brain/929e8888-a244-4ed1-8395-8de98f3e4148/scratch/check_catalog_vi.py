import urllib
from sqlalchemy import create_engine, text
import pandas as pd
import os

def export_cuarentena():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'MDM_Cuarentena_Export.csv'))
    
    with engine.connect() as conn:
        print(f"Exportando MDM.Cuarentena a CSV...")
        query = "SELECT * FROM MDM.Cuarentena ORDER BY Fecha_Ingreso DESC"
        df = pd.read_sql(text(query), conn)
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"Exportación completada. Archivo guardado en: {output_path}")

if __name__ == "__main__":
    export_cuarentena()
