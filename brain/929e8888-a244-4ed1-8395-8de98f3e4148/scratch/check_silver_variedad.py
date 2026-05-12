import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_silver_variedad():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Buscando FCM en Silver.Dim_Variedad:")
        query = "SELECT * FROM Silver.Dim_Variedad"
        df = pd.read_sql(text(query), conn)
        df_filt = df[df.astype(str).apply(lambda x: x.str.contains('FCM', case=False)).any(axis=1)]
        print(df_filt.to_string(index=False) if not df_filt.empty else "No encontrado en Silver.Dim_Variedad.")

if __name__ == "__main__":
    check_silver_variedad()
