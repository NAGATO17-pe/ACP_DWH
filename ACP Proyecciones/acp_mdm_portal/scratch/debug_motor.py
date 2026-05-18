import sys
import os
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db import ejecutar_query
from utils.motor_proyecciones import extraer_datos_granulares, MARGEN_PESIMISTA, MARGEN_OPTIMISTA

def probar_sem_27():
    print("Extrayendo datos granulares para la Semana 27 - 2025...")
    
    id_tiempo = 20250630
    
    df, df_p, df_w = extraer_datos_granulares(id_tiempo)
    
    if df is not None and not df.empty:
        print(f"Se encontraron {len(df)} registros granulares.")
        print("Columnas disponibles:", df.columns.tolist())
        # Ver si hay datos de conteo
        conteo_cols = ['cosechable', 'maduras', 'cremas', 'fase_2', 'fase_1', 'verdes', 'pequena']
        present_cols = [c for c in conteo_cols if c in df.columns]
        print("Suma de conteos por estado:")
        print(df[present_cols].sum())
        
        # Ver si hay plantas
        if 'Plantas' in df.columns:
            print(f"Total plantas: {df['Plantas'].sum():,.0f}")
        else:
            print("AVISO: No se encontró la columna 'Plantas' en el resultado granular.")
    else:
        print("No se encontraron datos granulares para esta semana.")

if __name__ == "__main__":
    probar_sem_27()
