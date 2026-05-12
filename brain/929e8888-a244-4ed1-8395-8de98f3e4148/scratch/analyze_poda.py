import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def analyze_poda_duplicates():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Conteo por Estado_Carga en Bronce.Evaluacion_Calidad_Poda:")
        res = conn.execute(text("SELECT Estado_Carga, COUNT(*) FROM Bronce.Evaluacion_Calidad_Poda GROUP BY Estado_Carga"))
        for r in res:
            print(f"- {r[0]}: {r[1]}")

        # Análisis Global de Duplicados
        query_unid = """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT 
                    Modulo_Raw, Fecha_Raw, Variedad_Raw, Tipo_Evaluacion_Raw
                FROM Bronce.Evaluacion_Calidad_Poda
            ) AS t
        """
        res = conn.execute(text(query_unid))
        unicas = res.scalar()
        print(f"\nFilas únicas globales: {unicas}")
        
        total_query = "SELECT COUNT(*) FROM Bronce.Evaluacion_Calidad_Poda"
        total = conn.execute(text(total_query)).scalar()
        print(f"Duplicados técnicos totales: {total - unicas}")

        # Verificar si los que están en 'CARGADO' son duplicados de los 'PROCESADO'
        query_check_cargado = """
            SELECT COUNT(*) 
            FROM Bronce.Evaluacion_Calidad_Poda c
            WHERE c.Estado_Carga = 'CARGADO'
              AND EXISTS (
                  SELECT 1 FROM Bronce.Evaluacion_Calidad_Poda p
                  WHERE p.Estado_Carga = 'PROCESADO'
                    AND p.Modulo_Raw = c.Modulo_Raw
                    AND p.Fecha_Raw = c.Fecha_Raw
                    AND p.Variedad_Raw = c.Variedad_Raw
                    AND p.Tipo_Evaluacion_Raw = c.Tipo_Evaluacion_Raw
              )
        """
        res = conn.execute(text(query_check_cargado))
        duplicados_existentes = res.scalar()
        print(f"Filas en 'CARGADO' que ya existen como 'PROCESADO': {duplicados_existentes}")

if __name__ == "__main__":
    analyze_poda_duplicates()
