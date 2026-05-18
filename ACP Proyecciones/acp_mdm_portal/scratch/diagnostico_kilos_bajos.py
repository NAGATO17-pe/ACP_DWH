"""Analiza por qué el cálculo da tan pocos kilos para una unidad específica."""
import pandas as pd
from utils.motor_proyecciones import extraer_datos_granulares, calcular_proyeccion

# Simulamos la carga para el Módulo 14 (que sale en tu captura)
# o el primer módulo disponible en la fecha de mayo
id_tiempo = 20260505 

print("--- Extrayendo datos para diagnóstico ---")
df_conteo, df_plantas, df_pesos = extraer_datos_granulares(id_tiempo)

if df_conteo.empty:
    print("¡Error! No hay conteos para esta fecha.")
else:
    # Miramos las primeras filas de conteo y plantas
    print("\nMuestra de Conteo (órganos):")
    print(df_conteo.head())
    
    print("\nMuestra de Plantas por unidad (Peladas):")
    print(df_plantas.head())
    
    print("\nMuestra de Pesos:")
    print(df_pesos.head())

    # Ejecutamos el cálculo para ver el desglose
    print("\n--- Ejecutando cálculo completo ---")
    df_res, info = calcular_proyeccion(id_tiempo)
    
    print("\nResultado Proyectado (Primeras 10 filas):")
    cols_kg = [c for c in df_res.columns if 'kg_w' in c]
    print(df_res[['modulo', 'turno', 'valvula', 'variedad'] + cols_kg].head(10))
    
    total_kg = df_res[cols_kg].sum().sum()
    print(f"\nTOTAL KILOS CALCULADOS: {total_kg:.2f} kg")
