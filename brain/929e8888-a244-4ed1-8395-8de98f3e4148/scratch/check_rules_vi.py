import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_rules():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Buscando reglas para 'VI' en MDM.Regla_Modulo_Raw:")
        query = "SELECT * FROM MDM.Regla_Modulo_Raw WHERE Modulo_Raw = 'VI' OR Modulo_Raw = 'vi'"
        df = pd.read_sql(text(query), conn)
        print(df.to_string(index=False) if not df.empty else "No se encontraron reglas para 'VI'.")

if __name__ == "__main__":
    check_rules()
