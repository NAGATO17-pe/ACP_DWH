import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def show_rejection_reasons():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Motivos de Rechazo (Cuarentena) - Hoy:")
        query = """
            SELECT Tabla_Origen, Motivo, COUNT(*) as Total
            FROM MDM.Cuarentena
            WHERE CAST(Fecha_Ingreso AS DATE) = CAST(GETDATE() AS DATE)
            GROUP BY Tabla_Origen, Motivo
            ORDER BY Tabla_Origen, Total DESC
        """
        try:
            df = pd.read_sql(text(query), conn)
            if df.empty:
                print("No hay registros de cuarentena hoy.")
            else:
                print(df.to_string(index=False))
        except Exception as e:
            print(f"Error al consultar MDM.Cuarentena: {e}")

if __name__ == "__main__":
    show_rejection_reasons()
