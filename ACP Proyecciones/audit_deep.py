"""
audit_deep.py
=============
Auditoria profunda de Dim_* contra Data Historica.
Genera:
  - AUDITORIA_DIMENSIONES_DEEP.md   (resumen ejecutivo)
  - audit_csv/*.csv                 (detalle por dimension)

Foco especial: detectar duplicados YA cargados en DB (encoding roto / espaciado)
ademas de los faltantes para la carga historica.
"""
from __future__ import annotations
import os
import re
import unicodedata
import urllib
from collections import defaultdict
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

ROOT = os.path.dirname(os.path.abspath(__file__))
BASE = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\Data Historica'
OUT_CSV = os.path.join(ROOT, 'audit_csv')
OUT_MD = os.path.join(ROOT, 'AUDITORIA_DIMENSIONES_DEEP.md')
os.makedirs(OUT_CSV, exist_ok=True)

CAD = ('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
       'DATABASE=ACP_DataWarehose_Proyecciones;Trusted_Connection=yes;TrustServerCertificate=yes;')
ENG = create_engine('mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(CAD))


# ── Utilidades ────────────────────────────────────────────────────────────────
def fix_mojibake(s: str) -> str:
    """Repone caracteres latinos comunes rotos por encoding (cp1252 <-> utf8)."""
    if not isinstance(s, str):
        return s
    # Reemplazos directos de mojibake mas comunes en estos archivos
    rep = {
        '�': '_',     # REPLACEMENT CHARACTER
        '\x91': "'", '\x92': "'", '\x93': '"', '\x94': '"',
        '\xa9': 'n', '\xf1': 'n',
    }
    for k, v in rep.items():
        s = s.replace(k, v)
    return s


_normalize_re = re.compile(r'[\s\-_().]+')
def norm_variedad(s: str) -> str:
    """Llave canonica para detectar duplicados de Variedad.
    Quita: mojibake, acentos, espacios, guiones, parentesis, puntos, casos.
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ''
    s = str(s).strip().upper()
    s = fix_mojibake(s)
    # Quitar acentos
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    # Quitar todos los separadores y puntos
    s = _normalize_re.sub('', s)
    # Quitar sufijos de campania entre parentesis ya removidos por regex
    return s


def read_file(name: str) -> pd.DataFrame:
    p = os.path.join(BASE, name)
    if name.endswith('.csv'):
        df = pd.read_csv(p, sep=';', encoding='utf-8-sig')
    else:
        df = pd.read_excel(p, sheet_name=0)
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


def q(sql: str) -> pd.DataFrame:
    with ENG.connect() as c:
        return pd.read_sql(text(sql), c)


# ── Lectura comun de todos los archivos ───────────────────────────────────────
FILES = {
    'fact_Fenologia.xlsx':            None,
    'fact_Evaluacion_vegetativa.xlsx': None,
    'fact_Censo_Plantas.xlsx':         None,
    'fact_calidad_poda.csv':           None,
    'Fact_pesos.xlsx':                 None,
    'historico_BI_Cosecha3.xlsx':      None,
}
for name in FILES:
    FILES[name] = read_file(name)

md = []  # acumulador del reporte markdown


def section(title, level=2):
    md.append('\n' + ('#' * level) + ' ' + title)


# =============================================================================
section('Auditoria Profunda de Dimensiones  vs  Data Historica', level=1)
md.append(f'\nGenerado: {pd.Timestamp.now():%Y-%m-%d %H:%M:%S}')
md.append('\nDB: `ACP_DataWarehose_Proyecciones` @ localhost')


# ── 1. DIM_TIEMPO ─────────────────────────────────────────────────────────────
section('1. Dim_Tiempo')
dim_t_rng = q("SELECT MIN(Fecha) AS min_f, MAX(Fecha) AS max_f, COUNT(*) AS n FROM Silver.Dim_Tiempo")
min_f, max_f, n = dim_t_rng.iloc[0]
# Rango necesario: fecha minima del archivo de cosecha (2016-07-26 visto) y maxima del archivo mas reciente
all_dates = []
for f in ['fact_Evaluacion_vegetativa.xlsx', 'historico_BI_Cosecha3.xlsx']:
    df = FILES[f]
    if 'Fecha' in df.columns:
        all_dates.append(pd.to_datetime(df['Fecha'], errors='coerce'))
all_dates = pd.concat(all_dates)
fmin, fmax = all_dates.min(), all_dates.max()

md.append(f'\n- DB: **{min_f}** -> **{max_f}** ({n:,} filas)')
md.append(f'- Archivos requieren: **{fmin:%Y-%m-%d}** -> **{fmax:%Y-%m-%d}**')
fechas_db = set(q("SELECT Fecha FROM Silver.Dim_Tiempo")['Fecha'].astype(str))
need = set(pd.date_range(fmin, fmax).strftime('%Y-%m-%d'))
faltan_t = sorted(need - fechas_db)
md.append(f'- Fechas requeridas y faltantes en Dim_Tiempo: **{len(faltan_t):,}**')
md.append(f'- Primera faltante: `{faltan_t[0] if faltan_t else "—"}`  ·  Ultima faltante: `{faltan_t[-1] if faltan_t else "—"}`')
pd.DataFrame({'Fecha_Faltante': faltan_t}).to_csv(os.path.join(OUT_CSV, '01_dim_tiempo_faltantes.csv'), index=False)


# ── 2. DIM_CAMPANA ────────────────────────────────────────────────────────────
section('2. Dim_Campana')
dim_c = q("SELECT ID_Campana, Anio_Cosecha, Nombre_Campana FROM Silver.Dim_Campana ORDER BY Anio_Cosecha")
md.append('\nEstado actual en DB:\n')
md.append('```\n' + dim_c.to_string(index=False) + '\n```')

# Recolectar valores de Campana de los archivos
campanas_obs = defaultdict(int)
for fname, df in FILES.items():
    for col in ['Campana', 'CAMPANA']:
        if col in df.columns:
            for v in df[col].dropna().astype(str).str.strip():
                campanas_obs[v] += 1

df_cmp = pd.DataFrame(sorted(campanas_obs.items()), columns=['Valor_en_archivo', 'Frecuencia'])
df_cmp.to_csv(os.path.join(OUT_CSV, '02_dim_campana_valores_archivo.csv'), index=False)

md.append(f'\nValores distintos de "Campana" observados en los archivos: **{len(campanas_obs)}**')
md.append('(Ver `audit_csv/02_dim_campana_valores_archivo.csv` para detalle.)')
md.append('\n**Problema**: el archivo mezcla formatos `2022`, `2022.0`, `2022 - 2023`, `2022-2023`. Necesita normalizacion antes de mapear a `Anio_Cosecha`.')


# ── 3. DIM_VARIEDAD: detectar DUPLICADOS YA EN DB + faltantes ────────────────
section('3. Dim_Variedad — duplicados ya cargados + faltantes')
dim_var = q("SELECT ID_Variedad, Nombre_Variedad FROM Silver.Dim_Variedad ORDER BY Nombre_Variedad")
dim_var['Nombre_Variedad_Fix'] = dim_var['Nombre_Variedad'].apply(fix_mojibake)
dim_var['norm'] = dim_var['Nombre_Variedad_Fix'].apply(norm_variedad)

# Clusters con > 1 fila comparten la misma clave normalizada -> DUPLICADOS
clusters = dim_var.groupby('norm').agg(
    cuantos=('ID_Variedad', 'count'),
    ids=('ID_Variedad', list),
    nombres=('Nombre_Variedad', list),
).reset_index()
dup_clusters = clusters[clusters['cuantos'] > 1].copy()
dup_clusters['nombres_str'] = dup_clusters['nombres'].apply(lambda L: ' | '.join(map(str, L)))
dup_clusters['ids_str'] = dup_clusters['ids'].apply(lambda L: ', '.join(map(str, L)))

md.append(f'\nVariedades en DB: **{len(dim_var)}**')
md.append(f'Clusters duplicados (mismo material con nombres distintos): **{len(dup_clusters)}**')
md.append(f'Total IDs duplicados a consolidar: **{int(dup_clusters["cuantos"].sum() - len(dup_clusters))}**')
if len(dup_clusters):
    md.append('\n| Clave normalizada | # IDs | IDs | Nombres en DB |')
    md.append('|---|---:|---|---|')
    for _, r in dup_clusters.sort_values('cuantos', ascending=False).head(25).iterrows():
        md.append(f'| `{r["norm"]}` | {r["cuantos"]} | {r["ids_str"]} | {r["nombres_str"]} |')
dup_clusters[['norm', 'cuantos', 'ids_str', 'nombres_str']].to_csv(
    os.path.join(OUT_CSV, '03a_dim_variedad_DUPLICADOS_EN_DB.csv'), index=False
)

# Variedades en archivos -> ¿estan o no en Dim?
file_var_set = set()
file_var_freq = defaultdict(int)
for fname, df in FILES.items():
    if 'Variedad' in df.columns:
        for v in df['Variedad'].dropna().astype(str).str.strip():
            file_var_set.add(v)
            file_var_freq[v] += 1

db_norm_set = set(dim_var['norm'])
faltan_var = [(v, file_var_freq[v], norm_variedad(v)) for v in file_var_set
              if norm_variedad(v) and norm_variedad(v) not in db_norm_set]
df_falt = pd.DataFrame(faltan_var, columns=['Nombre_Archivo', 'Frecuencia', 'norm']).sort_values('Frecuencia', ascending=False)
df_falt.to_csv(os.path.join(OUT_CSV, '03b_dim_variedad_FALTANTES.csv'), index=False)
md.append(f'\nVariedades del archivo que NO matchean ningun cluster (faltantes reales): **{len(df_falt)}**')
md.append('Top faltantes (ya normalizadas, ordenadas por frecuencia):')
md.append('\n| Nombre en archivo | Frecuencia | Norm |\n|---|---:|---|')
for _, r in df_falt.head(20).iterrows():
    md.append(f'| `{r["Nombre_Archivo"]}` | {r["Frecuencia"]} | `{r["norm"]}` |')


# ── 4. DIM_PERSONAL (DNI + Nombre del archivo de evaluacion vegetativa) ──────
section('4. Dim_Personal — evaluadores historicos')
dim_p = q("SELECT ID_Personal, DNI, Nombre_Completo FROM Silver.Dim_Personal")
md.append(f'\nDim_Personal actual: **{len(dim_p)}** registros')
md.append('```\n' + dim_p.to_string(index=False) + '\n```')

ev = FILES['fact_Evaluacion_vegetativa.xlsx']
if 'DNI' in ev.columns and 'Nombres' in ev.columns:
    file_dnis = (ev[['DNI', 'Nombres']].dropna()
                   .assign(DNI=lambda d: d['DNI'].astype(str).str.strip(),
                           Nombres=lambda d: d['Nombres'].astype(str).str.strip()))
    # Quedarse con un nombre por DNI (el mas frecuente)
    grouped = (file_dnis.groupby('DNI')
                 .agg(Nombre=('Nombres', lambda s: s.value_counts().idxmax()),
                      Evaluaciones=('Nombres', 'size'))
                 .reset_index())
    db_dnis = set(dim_p['DNI'].astype(str))
    faltan_p = grouped[~grouped['DNI'].isin(db_dnis)].sort_values('Evaluaciones', ascending=False)
    md.append(f'\nDNIs unicos en archivo Evaluacion Vegetativa: **{len(grouped)}**')
    md.append(f'DNIs que FALTAN en Dim_Personal: **{len(faltan_p)}**')
    faltan_p.to_csv(os.path.join(OUT_CSV, '04_dim_personal_FALTANTES.csv'), index=False)
    md.append('\nTop 15 evaluadores faltantes (por # de evaluaciones realizadas):')
    md.append('\n| DNI | Nombre | Evaluaciones |\n|---|---|---:|')
    for _, r in faltan_p.head(15).iterrows():
        md.append(f'| {r["DNI"]} | {r["Nombre"]} | {r["Evaluaciones"]:,} |')


# ── 5. DIM_GEOGRAFIA (Modulo, Turno, Valvula) ────────────────────────────────
section('5. Dim_Geografia — combinaciones Modulo/Turno/Valvula')
dim_g = q("""
    SELECT DISTINCT m.Modulo, t.Turno, v.Valvula
    FROM Silver.Dim_Geografia g
    JOIN Silver.Dim_Modulo_Catalogo  m ON g.ID_Modulo_Catalogo  = m.ID_Modulo_Catalogo
    JOIN Silver.Dim_Turno_Catalogo   t ON g.ID_Turno_Catalogo   = t.ID_Turno_Catalogo
    JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
    WHERE m.Modulo >= 0
""")
def _i(x):
    try:    return int(float(x))
    except: return None
db_combos = set()
for m, t, v in zip(dim_g['Modulo'], dim_g['Turno'], dim_g['Valvula']):
    mi, ti, vi = _i(m), _i(t), _i(v)
    if None not in (mi, ti, vi):
        db_combos.add((mi, ti, vi))

# Construir uso (combo -> freq) y origen (combo -> set archivos) desde archivos
combo_freq = defaultdict(int)
combo_origin = defaultdict(set)
for fname, df in FILES.items():
    cm = next((c for c in df.columns if c.lower() in ('modulo', 'm')), None)
    ct = next((c for c in df.columns if c.lower() == 'turno'), None)
    cv = next((c for c in df.columns if c.lower() == 'valvula'), None)
    if not (cm and ct and cv):
        continue
    sub = df[[cm, ct, cv]].dropna()
    for m, t, v in sub.itertuples(index=False):
        mi, ti, vi = _i(m), _i(t), _i(v)
        if None in (mi, ti, vi):
            continue
        combo_freq[(mi, ti, vi)] += 1
        combo_origin[(mi, ti, vi)].add(fname)

falt_g = sorted(set(combo_freq) - db_combos)
md.append(f'\nCombinaciones unicas (Modulo, Turno, Valvula) en DB: **{len(db_combos)}**')
md.append(f'Combinaciones referenciadas por archivos: **{len(combo_freq)}**')
md.append(f'Combinaciones FALTANTES en Dim_Geografia: **{len(falt_g)}**')

rows = [(m, t, v, combo_freq[(m, t, v)], ' | '.join(sorted(combo_origin[(m, t, v)])))
        for (m, t, v) in falt_g]
pd.DataFrame(rows, columns=['Modulo', 'Turno', 'Valvula', 'Frecuencia', 'Archivos']).sort_values('Frecuencia', ascending=False) \
  .to_csv(os.path.join(OUT_CSV, '05_dim_geografia_FALTANTES.csv'), index=False)
md.append('\nTop 15 combinaciones faltantes (por frecuencia de uso en archivos):')
md.append('\n| Modulo | Turno | Valvula | Frecuencia | Archivos |\n|---:|---:|---:|---:|---|')
for m, t, v, fr, ar in sorted(rows, key=lambda r: -r[3])[:15]:
    md.append(f'| {m} | {t} | {v} | {fr:,} | {ar} |')


# ── 6. DIM_ESTADO_FENOLOGICO ─────────────────────────────────────────────────
section('6. Dim_Estado_Fenologico — mapping archivo <-> DB')
ef = q("SELECT ID_Estado_Fenologico, Nombre_Estado, Orden_Estado FROM Silver.Dim_Estado_Fenologico ORDER BY Orden_Estado")
md.append('\nEstados en DB:\n```\n' + ef.to_string(index=False) + '\n```')
md.append('\nColumnas de fase en `fact_Fenologia.xlsx` (a pivotear):')
md.append('`Yema Hinchada, Boton, Flor, Pequena, Verde, Fase 1, Fase 2, Crema, Madura, Cosechable`')
md.append('\nMapping propuesto:')
md.append('\n| Columna archivo | Estado_Fenologico DB | Accion |\n|---|---|---|')
mappings = [
    ('Yema Hinchada', '(no existe)', 'INSERTAR nuevo estado con Orden_Estado=-1'),
    ('Boton',         'Boton Floral', 'Alias directo'),
    ('Flor',          'Flor',         'Match exacto'),
    ('Pequena',       'Pequena',      'Match exacto (limpiar enie en archivo)'),
    ('Verde',         'Verde',        'Match exacto'),
    ('Fase 1',        'Inicio F1',    'Alias'),
    ('Fase 2',        'Inicio F2',    'Alias'),
    ('Crema',         'Crema',        'Match exacto'),
    ('Madura',        'Madura',       'Match exacto'),
    ('Cosechable',    'Cosechable',   'Match exacto'),
]
for arc, db, ac in mappings:
    md.append(f'| `{arc}` | `{db}` | {ac} |')


# ── 7. % cargable por archivo si FK estricto ─────────────────────────────────
section('7. Capacidad de carga con FK estricto')
# Esta es una estimacion: para cada archivo cuento filas que tienen
# valores cuyas dims faltan. Solo se evalua Variedad + (Modulo,Turno,Valvula) + Tiempo.
md.append('\nEstimacion del % de filas de cada archivo que entrarian con FK estricto **hoy** (sin agregar nada a las Dims):')
md.append('\n| Archivo | Filas | Fallaria por Variedad | Fallaria por Geografia | Fallaria por Tiempo | Filas cargables |\n|---|---:|---:|---:|---:|---:|')

# Set helpers
dim_var_norm = set(dim_var['norm'])
dim_dates_set = set(q("SELECT CAST(Fecha AS VARCHAR(10)) AS f FROM Silver.Dim_Tiempo")['f'])
for fname, df in FILES.items():
    n_total = len(df)
    cm = next((c for c in df.columns if c.lower() in ('modulo', 'm')), None)
    ct = next((c for c in df.columns if c.lower() == 'turno'), None)
    cv = next((c for c in df.columns if c.lower() == 'valvula'), None)
    has_var = 'Variedad' in df.columns
    has_fecha = 'Fecha' in df.columns

    fail_var = 0
    if has_var:
        fail_var = int((~df['Variedad'].astype(str).str.strip().apply(norm_variedad).isin(dim_var_norm)).sum())

    fail_geo = 0
    if cm and ct and cv:
        s = df[[cm, ct, cv]]
        def _in_dim(row):
            try:
                k = (int(float(row[cm])), int(float(row[ct])), int(float(row[cv])))
                return k in db_combos
            except: return False
        fail_geo = int((~s.apply(_in_dim, axis=1)).sum())

    fail_t = 0
    if has_fecha:
        f = pd.to_datetime(df['Fecha'], errors='coerce')
        fail_t = int((~f.dt.strftime('%Y-%m-%d').isin(dim_dates_set)).sum())

    fail_any_mask = pd.Series([False]*n_total)
    if has_var:
        fail_any_mask |= ~df['Variedad'].astype(str).str.strip().apply(norm_variedad).isin(dim_var_norm)
    if cm and ct and cv:
        def _bad(row):
            try:
                k = (int(float(row[cm])), int(float(row[ct])), int(float(row[cv])))
                return k not in db_combos
            except: return True
        fail_any_mask |= df.apply(_bad, axis=1)
    if has_fecha:
        f = pd.to_datetime(df['Fecha'], errors='coerce')
        fail_any_mask |= ~f.dt.strftime('%Y-%m-%d').isin(dim_dates_set)
    cargables = n_total - int(fail_any_mask.sum())
    md.append(f'| `{fname}` | {n_total:,} | {fail_var:,} | {fail_geo:,} | {fail_t:,} | **{cargables:,}** ({100.0*cargables/n_total:.1f}%) |')


# ── Conclusiones ─────────────────────────────────────────────────────────────
section('Conclusiones y proximo paso', level=1)
md.append('\n1. **Dim_Tiempo**: faltan ~1 461 dias (2016-01-01 a 2019-12-31). Script trivial.')
md.append('2. **Dim_Campana**: faltan 2016-2019. Normalizar formatos antes de cargar.')
md.append('3. **Dim_Variedad**: corregir primero los clusters duplicados ya cargados; luego agregar las realmente faltantes.')
md.append('4. **Dim_Personal**: cargar evaluadores desde `fact_Evaluacion_vegetativa.xlsx`.')
md.append('5. **Dim_Geografia**: necesita poblarse con las combinaciones historicas para que las facts entren.')
md.append('6. **Dim_Estado_Fenologico**: agregar `Yema Hinchada` + definir alias para `Boton`, `Fase 1`, `Fase 2`.')

# Escribir reporte
with open(OUT_MD, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(md))
print(f'OK  Reporte:  {OUT_MD}')
print(f'OK  CSVs:    {OUT_CSV}/  ({len(os.listdir(OUT_CSV))} archivos)')
