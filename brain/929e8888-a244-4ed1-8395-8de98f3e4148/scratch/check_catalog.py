import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_catalog():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT * FROM MDM.Catalogo_Variedades"), conn)
        df_filt = df[df.astype(str).apply(lambda x: x.str.contains('FCM', case=False)).any(axis=1)]
        print(df_filt)

if __name__ == "__main__":
    check_catalog()
