import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def check_poda_ids():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Análisis de IDs en Poda:")
        
        # 1. ¿Cuántos IDs únicos de la App hay?
        res = conn.execute(text("SELECT COUNT(DISTINCT ID_Evaluacion_Calidad_Poda) FROM Bronce.Evaluacion_Calidad_Poda"))
        ids_unicos = res.scalar()
        print(f"IDs de App únicos: {ids_unicos}")
        
        res = conn.execute(text("SELECT COUNT(*) FROM Bronce.Evaluacion_Calidad_Poda"))
        total = res.scalar()
        print(f"Total filas: {total}")

        # 2. Si usamos el ID de la App como clave, ¿cuántos duplicados quedan?
        print(f"Duplicados técnicos (mismo ID de App): {total - ids_unicos}")

if __name__ == "__main__":
    check_poda_ids()
