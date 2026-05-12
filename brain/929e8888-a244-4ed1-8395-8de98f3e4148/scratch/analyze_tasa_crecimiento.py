import urllib
from sqlalchemy import create_engine, text
import pandas as pd

def analyze_tasa_crecimiento_duplicates():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        print("Análisis de duplicados en Bronce.Tasa_Crecimiento_Brotes (Estado_Carga='CARGADO'):")
        
        # 1. Total de filas cargadas
        res = conn.execute(text("SELECT COUNT(*) FROM Bronce.Tasa_Crecimiento_Brotes WHERE Estado_Carga = 'CARGADO'"))
        total = res.scalar()
        print(f"Total filas: {total}")

        # 2. Conteo de filas únicas según el criterio de pre_limpiar_duplicados_batch
        # Columnas: Modulo_Raw, Fecha_Raw, Variedad_Raw, Tipo_Evaluacion_Raw, Tipo_Tallo_Raw, Ensayo_Raw, Medida_Raw, Codigo_Origen_Raw
        query_unid = """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT 
                    Modulo_Raw, Fecha_Raw, Variedad_Raw, 
                    Tipo_Evaluacion_Raw, Tipo_Tallo_Raw, Ensayo_Raw, Medida_Raw, Codigo_Origen_Raw
                FROM Bronce.Tasa_Crecimiento_Brotes
                WHERE Estado_Carga = 'CARGADO'
            ) AS t
        """
        res = conn.execute(text(query_unid))
        unicas = res.scalar()
        duplicados_batch = total - unicas
        print(f"Filas únicas (criterio batch): {unicas}")
        print(f"Duplicados técnicos intra-batch: {duplicados_batch}")

        # 3. ¿Qué pasa si quitamos Medida_Raw de la clave? (Posible grano de negocio)
        query_grain = """
            SELECT COUNT(*) FROM (
                SELECT DISTINCT 
                    Modulo_Raw, Fecha_Raw, Variedad_Raw, 
                    Tipo_Evaluacion_Raw, Tipo_Tallo_Raw, Ensayo_Raw, Codigo_Origen_Raw
                FROM Bronce.Tasa_Crecimiento_Brotes
                WHERE Estado_Carga = 'CARGADO'
            ) AS t
        """
        res = conn.execute(text(query_grain))
        unicas_negocio = res.scalar()
        print(f"Filas únicas (sin Medida_Raw): {unicas_negocio}")
        print(f"Conflictos de grano (misma clave, diferente medida): {unicas - unicas_negocio}")

if __name__ == "__main__":
    analyze_tasa_crecimiento_duplicates()
