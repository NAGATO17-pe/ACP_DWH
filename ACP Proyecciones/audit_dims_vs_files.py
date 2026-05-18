"""
audit_dims_vs_files.py
======================
Audita cada Dim del DWH contra los valores reales que aparecen en los archivos
de Data Historica. Reporta cuantos valores referenciados existen / faltan en
cada dimension antes de intentar cargar los facts.
"""
import os
import urllib
import pandas as pd
from sqlalchemy import create_engine, text

BASE = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\Data Historica'
CAD = ('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
       'DATABASE=ACP_DataWarehose_Proyecciones;Trusted_Connection=yes;TrustServerCertificate=yes;')
ENG = create_engine('mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(CAD))


def read_file(name, sep=';'):
    p = os.path.join(BASE, name)
    if name.endswith('.csv'):
        df = pd.read_csv(p, sep=sep, encoding='utf-8-sig')
    else:
        df = pd.read_excel(p, sheet_name=0)
    # Normaliza mojibake habitual
    rename = {}
    for c in df.columns:
        nc = (c.replace('Campa\xf1a', 'Campana').replace('Campa?a', 'Campana')
                .replace('A\xf1o', 'Anio').replace('A?o', 'Anio')
                .replace('M\xf3dulo', 'Modulo').replace('M?dulo', 'Modulo')
                .replace('V\xe1lvula', 'Valvula').replace('V?lvula', 'Valvula')
                .replace('\xc1rea', 'Area').replace('?rea', 'Area')
                .replace('CAMPA\xd1A', 'Campana').replace('CAMPA?A', 'Campana')
                .replace('﻿', ''))
        rename[c] = nc.strip()
    return df.rename(columns=rename)


def db_unique(query):
    with ENG.connect() as c:
        return pd.read_sql(text(query), c)


def section(title):
    print('\n' + '=' * 90); print('  ' + title); print('=' * 90)


# --- DIM_TIEMPO ---
section('Dim_Tiempo  vs  rangos de fecha en archivos')
dim_t = db_unique("SELECT MIN(Fecha) min_f, MAX(Fecha) max_f, COUNT(*) n FROM Silver.Dim_Tiempo")
print('Dim_Tiempo:'); print(dim_t.to_string(index=False))
# Fechas extremas requeridas: 2016-01-01 ... 2026-12-31 minimo
print('Necesario por archivos: 2016-01-01  ...  2026-12-31')

# --- DIM_VARIEDAD ---
section('Dim_Variedad  vs  variedades en archivos')
dim_v = set(db_unique("SELECT DISTINCT UPPER(LTRIM(RTRIM(Nombre_Variedad))) AS v FROM Silver.Dim_Variedad")['v'].dropna())
print(f'Dim_Variedad ({len(dim_v)}):', sorted(dim_v))

archivos_var = {
    'fact_Fenologia.xlsx': 'Variedad',
    'fact_Evaluacion_vegetativa.xlsx': 'Variedad',
    'fact_Censo_Plantas.xlsx': 'Variedad',
    'fact_calidad_poda.csv': 'Variedad',
    'Fact_pesos.xlsx': 'Variedad',
    'historico_BI_Cosecha3.xlsx': 'Variedad',
}
all_file_var = set()
for f, col in archivos_var.items():
    df = read_file(f)
    if col in df.columns:
        vals = set(df[col].dropna().astype(str).str.strip().str.upper().unique())
        all_file_var |= vals
print(f'Variedades en archivos ({len(all_file_var)}):', sorted(all_file_var))
faltantes_v = sorted(all_file_var - dim_v)
print(f'FALTAN en Dim_Variedad ({len(faltantes_v)}):', faltantes_v)

# --- DIM_GEOGRAFIA: combinaciones Modulo-Turno-Valvula ---
section('Dim_Geografia  vs  combinaciones Modulo/Turno/Valvula en archivos')
# Vamos a inspeccionar cols de Dim_Geografia primero
cols_g = pd.read_sql(text(
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='Silver' AND TABLE_NAME='Dim_Geografia' ORDER BY ORDINAL_POSITION"
), ENG.connect())
print('Cols Dim_Geografia:', cols_g['COLUMN_NAME'].tolist())

dim_g = db_unique("""
    SELECT DISTINCT m.Modulo AS Modulo, t.Turno AS Turno, v.Valvula AS Valvula
    FROM Silver.Dim_Geografia g
    LEFT JOIN Silver.Dim_Modulo_Catalogo  m ON g.ID_Modulo_Catalogo  = m.ID_Modulo_Catalogo
    LEFT JOIN Silver.Dim_Turno_Catalogo   t ON g.ID_Turno_Catalogo   = t.ID_Turno_Catalogo
    LEFT JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
    WHERE m.Modulo IS NOT NULL AND m.Modulo >= 0
""")
print(f'Dim_Geografia combinaciones unicas (Mod,Tur,Val): {len(dim_g)}')
def _i(x):
    try: return int(float(x))
    except: return str(x)
set_g = set((_i(m), _i(t), _i(v)) for m, t, v in zip(dim_g['Modulo'], dim_g['Turno'], dim_g['Valvula']))

all_file_g = set()
for f, _ in archivos_var.items():
    df = read_file(f)
    cm = next((c for c in df.columns if c.lower() in ('modulo', 'm', 'm\xf3dulo')), None)
    ct = next((c for c in df.columns if c.lower() == 'turno'), None)
    cv = next((c for c in df.columns if c.lower() == 'valvula'), None)
    if cm and ct and cv:
        sub = df[[cm, ct, cv]].dropna()
        try:
            tuples = set((int(m), int(t), int(v)) for m, t, v in sub.itertuples(index=False))
        except Exception:
            tuples = set((m, t, v) for m, t, v in sub.itertuples(index=False))
        all_file_g |= tuples
print(f'Combinaciones Modulo/Turno/Valvula en archivos: {len(all_file_g)}')
faltan_g = list(all_file_g - set_g)
print(f'FALTAN en Dim_Geografia: {len(faltan_g)}')
if faltan_g[:20]:
    print('Primeras 20 faltantes:', sorted(faltan_g, key=lambda x: (str(x[0]), str(x[1]), str(x[2])))[:20])

# --- DIM_PERSONAL (DNI de evaluacion vegetativa) ---
section('Dim_Personal  vs  DNIs del archivo evaluacion vegetativa')
dim_p = set(db_unique("SELECT DISTINCT DNI FROM Silver.Dim_Personal WHERE DNI IS NOT NULL")['DNI'].astype(str))
print(f'Dim_Personal DNIs registrados: {len(dim_p)}')
ev = read_file('fact_Evaluacion_vegetativa.xlsx')
file_dni = set(ev['DNI'].dropna().astype(str).str.strip().unique()) if 'DNI' in ev.columns else set()
print(f'DNIs en archivo evaluacion vegetativa: {len(file_dni)}')
faltan_dni = sorted(file_dni - dim_p)
print(f'FALTAN en Dim_Personal: {len(faltan_dni)}')
if faltan_dni[:20]:
    print('Primeros 20:', faltan_dni[:20])

# --- DIM_CAMPANA ---
section('Dim_Campana  vs  campanas en archivos')
dim_c = db_unique("SELECT ID_Campana, Anio_Cosecha, Nombre_Campana FROM Silver.Dim_Campana ORDER BY Anio_Cosecha")
print('Dim_Campana actual:'); print(dim_c.to_string(index=False))
all_campanas = set()
for f, _ in archivos_var.items():
    df = read_file(f)
    cc = next((c for c in df.columns if c.lower() in ('campana',)), None)
    if cc:
        all_campanas |= set(df[cc].dropna().astype(str).str.strip().unique())
print(f'Campanas declaradas en archivos ({len(all_campanas)}):', sorted(all_campanas))

# --- DIM_ESTADO_FENOLOGICO (para fact_Fenologia que trae columnas por fase) ---
section('Dim_Estado_Fenologico')
cols_ef = pd.read_sql(text(
    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='Silver' AND TABLE_NAME='Dim_Estado_Fenologico' ORDER BY ORDINAL_POSITION"
), ENG.connect())
print('Cols:', cols_ef['COLUMN_NAME'].tolist())
ef = pd.read_sql(text("SELECT * FROM Silver.Dim_Estado_Fenologico"), ENG.connect())
print(ef.to_string(index=False))
# Las fases que aparecen como columnas en fact_Fenologia.xlsx:
fases_archivo = ['Yema Hinchada', 'Boton', 'Flor', 'Pequeña', 'Verde',
                 'Fase 1', 'Fase 2', 'Crema', 'Madura', 'Cosechable']
print('Fases columna en archivo Fenologia:', fases_archivo)
