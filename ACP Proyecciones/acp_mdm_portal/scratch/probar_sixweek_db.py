import sys
import os
import pandas as pd
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.motor_proyecciones import ejecutar_proyeccion, MATRIZ_INPUTS_DEFAULT, MARGEN_PESIMISTA, MARGEN_OPTIMISTA

def probar_sem_27():
    print("Iniciando proyección Six-Week para la Semana 27 - 2025...")
    
    id_tiempo = 20250630 # Lunes de la Sem 27
    
    # Ejecutar proyección completa para todas las unidades
    res = ejecutar_proyeccion(
        id_tiempo=id_tiempo,
        matriz_inputs=MATRIZ_INPUTS_DEFAULT,
        margen_pesimista=MARGEN_PESIMISTA,
        margen_optimista=MARGEN_OPTIMISTA
    )
    
    # Extraer los datos del resultado
    df = res.get('df_semanal')
    
    if df is not None and not df.empty:
        print("\n" + "="*50)
        print("RESULTADO PROYECCIÓN SIX-WEEK (Semana 27 - 2025)")
        print("="*50)
        for _, row in df.iterrows():
            print(f"Semana {row['semana']}: {row['kg_base']:15,.2f} kg")
        print("-" * 50)
        print(f"TOTAL: {df['kg_base'].sum():15,.2f} kg")
        print("="*50)
        
        kpis = res.get('kpis', {})
        print(f"Unidades cubiertas: {kpis.get('unidades_cubiertas')}/{kpis.get('unidades_totales')}")
        print(f"Total plantas proyectadas: {kpis.get('total_plantas'):,.0f}")
    else:
        print("No se generaron resultados.")
        print("Keys en el resultado:", res.keys())
        if 'df_detalle' in res and res['df_detalle'] is not None:
             print("Detalle size:", len(res['df_detalle']))

if __name__ == "__main__":
    probar_sem_27()
