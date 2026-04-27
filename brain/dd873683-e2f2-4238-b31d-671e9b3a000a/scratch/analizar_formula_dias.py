"""
Análisis forense de la fórmula 'días desde poda' en BD_General
"""
import pandas as pd
import numpy as np

ARCHIVO = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\entrada\tasa_crecimiento_brotes\Tasa de Crecimiento 2025 - 2026.xlsx'

print("Cargando BD_General...")
df = pd.read_excel(ARCHIVO, sheet_name='BD_General', header=1)
df.columns = [str(c).strip() for c in df.columns]

# Renombrar columnas con caracteres especiales para trabajar fácil
df = df.rename(columns={
    'Fecha Evaluación': 'FechaEval',
    'Fecha Poda Aux':   'FechaPoda',
    'Mód': 'Mod',
    'Tur': 'Tur',
    'Vál': 'Val',
    'Condición': 'Condicion',
    'Estado Vegetativo': 'EstadoVeg',
    'Tipo de Tallo': 'TipoTallo',
    'CAMPAÑA': 'Campana',
    'EVALUACIÓN': 'TipoEval',
})

df['_fe'] = pd.to_datetime(df['FechaEval'], errors='coerce')
df['_fp'] = pd.to_datetime(df['FechaPoda'], errors='coerce')
df['_dias'] = (df['_fe'] - df['_fp']).dt.days
df['_medida'] = pd.to_numeric(df['Medida'], errors='coerce')

df_ok = df.dropna(subset=['_fe', '_fp'])

print(f"Filas con ambas fechas válidas: {len(df_ok):,}")
print()

# ============================================================
# Distribución por rangos
# ============================================================
print("=== DISTRIBUCIÓN DE DÍAS (FechaEval - FechaPoda) ===")
bins   = [-999, -30, -15, -7, 0, 7, 30, 60, 90, 120, 999]
labels = ['< -30','-30 a -15','-15 a -7','-7 a 0','0 a 7','7 a 30','30 a 60','60 a 90','90 a 120','> 120']
df_ok['_rango'] = pd.cut(df_ok['_dias'], bins=bins, labels=labels)
print(df_ok['_rango'].value_counts().sort_index().to_string())
print()

# ============================================================
# Detalle de los 100 registros con días negativos
# ============================================================
df_neg = df_ok[df_ok['_dias'] < 0].copy()
print(f"=== REGISTROS CON DÍAS NEGATIVOS ({len(df_neg)}) ===")
cols = ['Unnamed: 0', 'Semana', 'FechaEval', 'FechaPoda', '_dias', 'Medida', 'Variedad', 'Mod', 'Tur', 'Val', 'Campana']
print(df_neg[[c for c in cols if c in df_neg.columns]].sort_values('_dias').to_string())
print()

# ============================================================
# Columna Día: ¿qué contiene?
# ============================================================
print("=== COLUMNA 'Dia' del Excel ===")
print(df_ok['Dia'].value_counts(dropna=False).head(10).to_string())
print()

# ============================================================
# Muestra normal: verificar que la fórmula es FechaEval - FechaPoda
# ============================================================
print("=== MUESTRA NORMAL (30-70 días) para verificar fórmula ===")
muestra = df_ok[(df_ok['_dias'] >= 30) & (df_ok['_dias'] <= 35)].head(8)
print(muestra[['Unnamed: 0', 'FechaEval', 'FechaPoda', '_dias', 'Medida', 'Variedad']].to_string())
print()

# ============================================================
# ¿La Medida es el crecimiento en cm desde la poda?
# Tasa implícita = Medida / días
# ============================================================
df_tasa = df_ok[(df_ok['_dias'] > 0) & (df_ok['_medida'].notna())].copy()
df_tasa['_tasa_dia'] = df_tasa['_medida'] / df_tasa['_dias']

print("=== TASA DIARIA IMPLÍCITA (Medida / dias) ===")
print(df_tasa['_tasa_dia'].describe())
print()

print("Muestra con tasa por variedad:")
print(df_tasa.groupby('Variedad')['_tasa_dia']
      .agg(['mean','min','max','count'])
      .round(3)
      .sort_values('count', ascending=False)
      .head(10)
      .to_string())
print()

# ============================================================
# ¿Los negativos tienen medida similar a los positivos cercanos?
# (para verificar si son datos reales o errores)
# ============================================================
print("=== COMPARATIVA: negativos vs positivos 0-7 días (misma variedad IMPERIAL) ===")
df_imperial = df_ok[df_ok['Variedad'] == 'IMPERIAL'].copy()
df_imperial['_grupo'] = pd.cut(df_imperial['_dias'], bins=[-999,-1,0,7,30], labels=['negativo','0','1a7','8a30'])
print(df_imperial.groupby('_grupo')['_medida']
      .agg(['mean','min','max','count'])
      .round(2)
      .to_string())
