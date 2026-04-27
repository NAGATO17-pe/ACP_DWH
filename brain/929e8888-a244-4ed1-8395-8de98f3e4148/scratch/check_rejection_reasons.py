import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_rejections():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Resumen de Seguimiento_Errores (últimos 50):")
        query = "SELECT TOP 50 * FROM Bronce.Seguimiento_Errores ORDER BY Fecha_Sistema DESC"
        df = pd.read_sql(text(query), conn)
        print(df.to_string())

        print("\nConteo por Motivo (hoy):")
        query = """
            SELECT Motivo, COUNT(*) as Total 
            FROM Bronce.Seguimiento_Errores 
            WHERE CAST(Fecha_Sistema AS DATE) = CAST(GETDATE() AS DATE)
            GROUP BY Motivo
            ORDER BY Total DESC
        """
        df_count = pd.read_sql(text(query), conn)
        print(df_count.to_string())

if __name__ == "__main__":
    check_rejections()
