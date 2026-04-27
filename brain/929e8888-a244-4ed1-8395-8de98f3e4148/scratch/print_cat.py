import urllib
from sqlalchemy import create_engine, text

def print_cat():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT Nombre_Canonico FROM MDM.Catalogo_Variedades WHERE Nombre_Canonico LIKE '%FCM%'"))
        for r in res:
            print(r[0])

if __name__ == "__main__":
    print_cat()