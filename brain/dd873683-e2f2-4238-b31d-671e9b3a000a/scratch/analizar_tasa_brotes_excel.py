"""
Análisis forense del Excel: Tasa de Crecimiento 2025-2026
Objetivo: entender qué es Fecha Poda Aux y por qué hay fechas futuras (2024-06-26)
"""
import pandas as pd
import numpy as np

ARCHIVO = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\entrada\tasa_crecimiento_brotes\Tasa de Crecimiento 2025 - 2026.xlsx'

print("="*70)
print("PASO 1: Estructura del archivo")
print("="*70)
xl = pd.ExcelFile(ARCHIVO)
print(f"Hojas: {xl.sheet_names}")
print()

# ---- HOJA BD_General ----
print("="*70)
print("HOJA: BD_General")
print("="*70)
df = pd.read_excel(ARCHIVO, sheet_name='BD_General', header=1)
print(f"Total filas: {len(df):,}")
print(f"Columnas ({len(df.columns)}):")
for c in df.columns:
    dtype = df[c].dtype
    nn = df[c].notna().sum()
    print(f"  [{c}]  dtype={dtype}  no-nulos={nn:,}")
print()

# Análisis específico de fechas
print("--- Rango de Fecha Evaluación ---")
fe = pd.to_datetime(df['Fecha Evaluación'], errors='coerce')
print(f"  Min: {fe.min()}  |  Max: {fe.max()}")
print()

print("--- Rango de Fecha Poda Aux ---")
fp = pd.to_datetime(df['Fecha Poda Aux'], errors='coerce')
print(f"  Min: {fp.min()}  |  Max: {fp.max()}")
print()

# Calcular dias
df['_dias'] = (fe - fp).dt.days
print("--- Distribución de días desde poda ---")
print(df['_dias'].describe())
print()

# Registros con dias < 0 (poda POSTERIOR a evaluación)
df_neg = df[df['_dias'] < 0].copy()
print(f"Registros con Fecha_Poda_Aux POSTERIOR a Fecha_Evaluacion: {len(df_neg):,}")
if len(df_neg) > 0:
    print()
    print("--- Fechas de Poda Aux que aparecen como futuras ---")
    print(df_neg['Fecha Poda Aux'].value_counts().head(15).to_string())
    print()
    print("--- Fechas de Evaluación de esos registros ---")
    print(df_neg['Fecha Evaluación'].value_counts().head(15).to_string())
    print()
    print("--- ¿Qué Módulos/Turnos/Válvulas tienen este problema? ---")
    print(df_neg.groupby(['Mód', 'Tur', 'Vál']).size().reset_index(name='count').sort_values('count', ascending=False).head(20).to_string())
    print()
    print("--- Variedad de esos registros ---")
    print(df_neg['Variedad'].value_counts().head(10).to_string())
    print()
    print("--- Muestra de 15 filas con dias negativos ---")
    cols_show = ['Unnamed: 0', 'Semana ', 'Fecha Evaluación', 'Mód', 'Tur', 'Vál', 'Variedad', 'Fecha Poda Aux', '_dias', 'CAMPAÑA']
    cols_ok = [c for c in cols_show if c in df_neg.columns]
    print(df_neg[cols_ok].head(15).to_string())

print()
print("="*70)
print("HOJA: Fechas Poda General (catálogo de referencia)")
print("="*70)
df_cat = pd.read_excel(ARCHIVO, sheet_name='Fechas Poda General', header=1)
print(f"Total filas: {len(df_cat):,}")
print(f"Columnas: {list(df_cat.columns)}")
print()
print("Primeras 20 filas:")
print(df_cat.head(20).to_string())
print()
print("--- Rango de Fecha Poda Aux en catálogo ---")
fp_cat = pd.to_datetime(df_cat['Fecha Poda Aux'], errors='coerce')
print(f"  Min: {fp_cat.min()}  |  Max: {fp_cat.max()}")
print()
print("--- Columna 'aux Poda G' (¿nombre de persona?) ---")
print(df_cat['aux Poda G'].value_counts(dropna=False).head(20).to_string())
print()

# ¿Hay registros con fecha 2024-06-26 en el catálogo?
mask_jun26 = fp_cat == pd.Timestamp('2024-06-26')
print(f"Registros en catálogo con Fecha Poda Aux = 2024-06-26: {mask_jun26.sum()}")
if mask_jun26.sum() > 0:
    print(df_cat[mask_jun26].to_string())
