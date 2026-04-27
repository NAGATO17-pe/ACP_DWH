import urllib
from sqlalchemy import create_engine, text

def find_remaining_fks():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        query = """
            SELECT OBJECT_NAME(parent_object_id) AS TableName, name AS FK_Name
            FROM sys.foreign_keys
            WHERE referenced_object_id = OBJECT_ID('Silver.Dim_Geografia_Obsoleta')
        """
        res = conn.execute(text(query))
        print("Tablas que aún referencian a Silver.Dim_Geografia_Obsoleta:")
        for r in res:
            print(f"- {r[0]} (FK: {r[1]})")

if __name__ == "__main__":
    find_remaining_fks()
