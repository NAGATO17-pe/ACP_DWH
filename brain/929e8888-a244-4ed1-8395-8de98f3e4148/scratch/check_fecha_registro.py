import urllib
from sqlalchemy import create_engine, text

def check_fecha_registro():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Bronce' AND COLUMN_NAME = 'Fecha_Registro_Raw'"))
        print("Tablas con Fecha_Registro_Raw:")
        for r in res:
            print(f"- {r[0]}")

if __name__ == "__main__":
    check_fecha_registro()
