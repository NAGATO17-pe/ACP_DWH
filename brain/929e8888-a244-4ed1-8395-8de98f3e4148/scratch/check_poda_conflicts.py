import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_poda_grain_conflicts():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Buscando conflictos de grano en Poda (Misma clave, diferentes datos):")
        
        # Criterio: Modulo, Fecha, Variedad, Tipo_Evaluacion
        # Queremos ver si hay variaciones en columnas de datos como TallosPlanta_Raw
        query = """
            SELECT 
                Modulo_Raw, Fecha_Raw, Variedad_Raw, Tipo_Evaluacion_Raw,
                COUNT(DISTINCT CAST(TallosPlanta_Raw AS NVARCHAR(50)) + '_' + CAST(LongitudTallo_Raw AS NVARCHAR(50))) as Variaciones_Datos,
                COUNT(*) as Total_Registros
            FROM Bronce.Evaluacion_Calidad_Poda
            GROUP BY Modulo_Raw, Fecha_Raw, Variedad_Raw, Tipo_Evaluacion_Raw
            HAVING COUNT(DISTINCT CAST(TallosPlanta_Raw AS NVARCHAR(50)) + '_' + CAST(LongitudTallo_Raw AS NVARCHAR(50))) > 1
        """
        df = pd.read_sql(text(query), conn)
        if df.empty:
            print("No se encontraron casos de misma clave con diferentes datos.")
        else:
            print(f"Se encontraron {len(df)} grupos con conflictos de datos.")
            print(df.head(10).to_string(index=False))

if __name__ == "__main__":
    check_poda_grain_conflicts()
