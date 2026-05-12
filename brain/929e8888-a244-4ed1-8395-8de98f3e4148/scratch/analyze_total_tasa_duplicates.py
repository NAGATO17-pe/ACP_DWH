import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def analyze_total_duplicates():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Análisis Global de Duplicados en Bronce.Tasa_Crecimiento_Brotes (Total: 268,474):")
        
        # 1. Conteo de filas únicas globales (sin filtrar por Estado_Carga)
        query_unid = """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT 
                    Modulo_Raw, Fecha_Raw, Variedad_Raw, 
                    Tipo_Evaluacion_Raw, Tipo_Tallo_Raw, Ensayo_Raw, Medida_Raw, Codigo_Origen_Raw
                FROM Bronce.Tasa_Crecimiento_Brotes
            ) AS t
        """
        res = conn.execute(text(query_unid))
        unicas = res.scalar()
        print(f"Filas únicas globales: {unicas}")
        print(f"Duplicados técnicos totales: {268474 - unicas}")

        # 2. Verificar si los que están en 'CARGADO' son duplicados de los 'PROCESADO'/'RECHAZADO'
        query_check_cargado = """
            SELECT COUNT(*) 
            FROM Bronce.Tasa_Crecimiento_Brotes c
            WHERE c.Estado_Carga = 'CARGADO'
              AND EXISTS (
                  SELECT 1 FROM Bronce.Tasa_Crecimiento_Brotes p
                  WHERE p.Estado_Carga IN ('PROCESADO', 'RECHAZADO')
                    AND p.Modulo_Raw = c.Modulo_Raw
                    AND p.Fecha_Raw = c.Fecha_Raw
                    AND p.Variedad_Raw = c.Variedad_Raw
                    AND p.Tipo_Evaluacion_Raw = c.Tipo_Evaluacion_Raw
                    AND p.Tipo_Tallo_Raw = c.Tipo_Tallo_Raw
                    AND p.Ensayo_Raw = c.Ensayo_Raw
                    AND p.Medida_Raw = c.Medida_Raw
                    AND p.Codigo_Origen_Raw = c.Codigo_Origen_Raw
              )
        """
        res = conn.execute(text(query_check_cargado))
        duplicados_existentes = res.scalar()
        print(f"Filas en 'CARGADO' que ya existen como 'PROCESADO'/'RECHAZADO': {duplicados_existentes}")

if __name__ == "__main__":
    analyze_total_duplicates()
