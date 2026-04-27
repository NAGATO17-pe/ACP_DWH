import urllib
from sqlalchemy import create_engine, text

def list_auditoria_tables():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Tablas en Auditoria:")
        res = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Auditoria'"))
        for r in res:
            print(f"- {r[0]}")
        
        print("\nTablas en MDM:")
        res = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'MDM'"))
        for r in res:
            print(f"- {r[0]}")

        # Check if there is a specific rejections table
        print("\nBuscando tabla de rechazos...")
        res = conn.execute(text("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%Rechazo%' OR TABLE_NAME LIKE '%Error%'"))
        for r in res:
            print(f"- {r[0]}.{r[1]}")

if __name__ == "__main__":
    list_auditoria_tables()
