import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine
from sqlalchemy import text
import pandas as pd

engine = obtener_engine()

def diag_campanas():
    print("=== Analizando Podas para Definicion de Campañas ===")
    with engine.connect() as conn:
        # 1. Ver qué tipos de poda tenemos y fechas
        df_podas = pd.read_sql("""
            SELECT 
                p.ID_Poda,
                p.Fecha_Evento,
                DATEPART(isowk, p.Fecha_Evento) as Semana_ISO,
                g.ID_Modulo_Catalogo
            FROM Silver.Fact_Ciclo_Poda p
            INNER JOIN Silver.Dim_Geografia g ON p.ID_Geografia = g.ID_Geografia
            ORDER BY p.Fecha_Evento DESC
        """, conn)
        
        if df_podas.empty:
            print("No se encontraron podas en Silver.Fact_Ciclo_Poda")
            return

        print(f"Total podas encontradas: {len(df_podas)}")
        
        # Aplicar regla del usuario
        # semana < 20 -> Año Campaña = Año Evento
        # semana >= 20 -> Año Campaña = Año Evento + 1
        
        df_podas['Anio_Evento'] = pd.to_datetime(df_podas['Fecha_Evento']).dt.year
        df_podas['Anio_Campana'] = df_podas.apply(
            lambda x: x['Anio_Evento'] if x['Semana_ISO'] < 20 else x['Anio_Evento'] + 1, 
            axis=1
        )
        
        print("\nMuestra de calculo de Campaña:")
        print(df_podas[['Fecha_Evento', 'Semana_ISO', 'Anio_Campana']].head(20))
        
        print("\nDistribucion de campañas por año:")
        print(df_podas['Anio_Campana'].value_counts().sort_index())

if __name__ == "__main__":
    diag_campanas()
