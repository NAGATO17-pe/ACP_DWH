import urllib
from sqlalchemy import create_engine, text

def check_counts():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Conteo por Estado_Carga en Bronce.Tasa_Crecimiento_Brotes:")
        res = conn.execute(text("SELECT Estado_Carga, COUNT(*) FROM Bronce.Tasa_Crecimiento_Brotes GROUP BY Estado_Carga"))
        for r in res:
            print(f"- {r[0]}: {r[1]}")

if __name__ == "__main__":
    check_counts()
