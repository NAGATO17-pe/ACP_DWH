import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_geografia():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Buscando Modulo 'VI' en Silver.Dim_Geografia:")
        query = """
            SELECT TOP 20 ID_Geografia, Modulo_Alias
            FROM Silver.Dim_Geografia
            WHERE Modulo_Alias LIKE '%VI%' OR Modulo_Alias = '6' OR Modulo_Alias = '06'
        """
        try:
            df = pd.read_sql(text(query), conn)
            print(df.to_string(index=False) if not df.empty else "No se encontraron módulos con 'VI' o '6'.")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    check_geografia()
