"""
populate_dims.py
================
Pobla todas las Dims con los datos de auditoría (audit_csv/).
Orden de ejecución:
  1. Dim_Tiempo         — fechas 2016-01-01 ... 2019-12-31
  2. Dim_Campana        — campañas 2016-2019
  3. Dim_Variedad       — consolida duplicados + agrega faltantes
  4. Dim_Estado_Fenologico — agrega 'Yema Hinchada'
  5. Dim_Personal       — 220 evaluadores desde CSV
  6. Dim_Geografia      — 144 combinaciones Mod/Tur/Val faltantes

Cada paso es idempotente (usa WHERE NOT EXISTS).
"""

import os
import urllib
import datetime
import calendar
import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR  = os.path.join(BASE_DIR, 'audit_csv')

CAD = ('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
       'DATABASE=ACP_DataWarehose_Proyecciones;Trusted_Connection=yes;TrustServerCertificate=yes;')
ENG = create_engine('mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(CAD))


def run(sql: str, desc: str = '') -> int:
    with ENG.begin() as c:
        r = c.execute(text(sql))
        n = r.rowcount
    label = f'[{desc}]' if desc else ''
    print(f'  {label:<35} => {n} filas afectadas')
    return n


def section(title: str):
    print('\n' + '='*70)
    print(f'  {title}')
    print('='*70)


# ===========================================================================
# 1. DIM_TIEMPO — fechas 2016-01-01 ... 2019-12-31
# Columnas reales: ID_Tiempo(int YYYYMMDD), Fecha, Anio, Mes, Semana_ISO,
#                  Semana_Cosecha(nullable), Dia_Semana, Nombre_Mes, Es_Fin_Semana
# ===========================================================================
section('1. Dim_Tiempo — rellenar 2016-01-01 .. 2019-12-31')

# Generar fechas en Python y bulk-insert vía pandas

# Fechas existentes en DB para no duplicar
with ENG.connect() as c:
    existing = set(pd.read_sql(
        text("SELECT Fecha FROM Silver.Dim_Tiempo WHERE Fecha BETWEEN '2016-01-01' AND '2019-12-31'"),
        c
    )['Fecha'].astype(str))

rows = []
d = datetime.date(2016, 1, 1)
fin = datetime.date(2019, 12, 31)
# weekday(): Mon=0 ... Sun=6  →  SQL Server DATEPART(WEEKDAY) con @@DATEFIRST=7: Sun=1,...,Sat=7
# Python: weekday()+2 gives Mon=2,...,Sun=1 (mapped to SQL Server default)
_py_to_ssweekday = {0:2, 1:3, 2:4, 3:5, 4:6, 5:7, 6:1}  # Mon-Sun → 2-7,1

while d <= fin:
    ds = str(d)
    if ds not in existing:
        iso_cal   = d.isocalendar()           # (iso_year, iso_week, iso_weekday)
        iso_week  = iso_cal[1]
        dia_semana = _py_to_ssweekday[d.weekday()]
        es_fin    = 1 if d.weekday() >= 5 else 0
        rows.append({
            'ID_Tiempo':   int(d.strftime('%Y%m%d')),
            'Fecha':       ds,
            'Anio':        d.year,
            'Mes':         d.month,
            'Semana_ISO':  iso_week,
            'Semana_Cosecha': None,
            'Dia_Semana':  dia_semana,
            'Nombre_Mes':  d.strftime('%B'),   # English month name (matches existing sample)
            'Es_Fin_Semana': es_fin,
        })
    d += datetime.timedelta(days=1)

n = len(rows)
if n:
    df_t = pd.DataFrame(rows)
    df_t.to_sql('Dim_Tiempo', ENG, schema='Silver', if_exists='append', index=False)
print(f'  [Dim_Tiempo] => {n} fechas insertadas (2016-2019)')


# ===========================================================================
# 2. DIM_CAMPANA — 2016, 2017, 2018, 2019
# Columnas: ID_Campana(identity), Anio_Cosecha, Nombre_Campana, Estado, Es_Activa
# ===========================================================================
section('2. Dim_Campana — campañas 2016-2019')

campanas = [
    (2016, 'Campaña 2016', 'Cerrada', 0),
    (2017, 'Campaña 2017', 'Cerrada', 0),
    (2018, 'Campaña 2018', 'Cerrada', 0),
    (2019, 'Campaña 2019', 'Cerrada', 0),
]
for anio, nombre, estado, activa in campanas:
    run(f"""
        IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Campana WHERE Anio_Cosecha = {anio})
            INSERT INTO Silver.Dim_Campana (Anio_Cosecha, Nombre_Campana, Estado, Es_Activa)
            VALUES ({anio}, N'{nombre}', N'{estado}', {activa});
    """, f'Campaña {anio}')


# ===========================================================================
# 3. DIM_VARIEDAD — consolidar duplicados y agregar faltantes
# Columnas: ID_Variedad(identity), Nombre_Variedad, Breeder, Es_Activa,
#           Fecha_Creacion, Fecha_Modificacion
# ===========================================================================
section('3. Dim_Variedad — duplicados y faltantes')

# 3a. Consolidar 3 clusters duplicados conocidos
#   (keep_id, drop_id, descripcion)
DUPLICATES = [
    (39, 88, 'FL 19-006 / FL19 - 006'),
    (77, 10, 'MEGA CRISP / Megacrisp'),
    (78, 29, 'MEGA EARLY / Megaearly'),
]

FACT_TABLES_VAR = [
    'Fact_areas_plantas', 'Fact_Censo_Plantas', 'Fact_Conteo_Fenologico',
    'Fact_Cosecha_SAP', 'Fact_Evaluacion_Pesos', 'Fact_Evaluacion_Vegetativa',
    'Fact_Ciclo_Poda', 'Fact_Fisiologia', 'Fact_Induccion_Floral',
    'Fact_Maduracion', 'Fact_Peladas', 'Fact_Proyecciones',
    'Fact_Tareo', 'Fact_Tasa_Crecimiento_Brotes',
]

for keep, drop, desc in DUPLICATES:
    print(f'\n  Consolidando: {desc} (keep={keep}, drop={drop})')
    for tbl in FACT_TABLES_VAR:
        with ENG.connect() as c:
            has = c.execute(text(f"""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA='Silver' AND TABLE_NAME='{tbl}' AND COLUMN_NAME='ID_Variedad'
            """)).scalar()
        if has:
            run(f"UPDATE Silver.{tbl} SET ID_Variedad={keep} WHERE ID_Variedad={drop}",
                f'remap {tbl}')
    run(f"DELETE FROM Silver.Dim_Variedad WHERE ID_Variedad={drop}",
        f'delete dup ID={drop}')


# 3b. Agregar variedades faltantes (históricas, no existen en DB)
# Sub-lotes y variantes se insertan como entidades propias para mantener trazabilidad.
VARIEDADES_NUEVAS = [
    'FCM15-005 (2022)',
    'FCM15-005 (2023)',
    'MEGACRISP (T111-519)',
    'MAGAGEM (T111-219)',
    'MANILA 2° SIEMBRA',
    'ATLAS BLUE 2° SIEMBRA',
    'JUPITER',
    'BIANCA',
    'FCM 15-087',
    'SIN SEMBRAR',
    'FL 03-228',
    'U. DE LA FLORIDA',
    'INDIGO CRISP',
    'MAGA GEM',
    'FALCONE',
]

print()
for nombre in VARIEDADES_NUEVAS:
    safe = nombre.replace("'", "''")
    run(f"""
        IF NOT EXISTS (
            SELECT 1 FROM Silver.Dim_Variedad
            WHERE UPPER(LTRIM(RTRIM(Nombre_Variedad))) = UPPER(N'{safe}')
        )
        INSERT INTO Silver.Dim_Variedad (Nombre_Variedad, Es_Activa)
        VALUES (N'{safe}', 1);
    """, f'Variedad "{nombre}"')


# ===========================================================================
# 4. DIM_ESTADO_FENOLOGICO — agregar Yema Hinchada
# ===========================================================================
section('4. Dim_Estado_Fenologico — Yema Hinchada')

run("""
    IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Estado_Fenologico WHERE Nombre_Estado = 'Yema Hinchada')
        INSERT INTO Silver.Dim_Estado_Fenologico (Nombre_Estado, Orden_Estado)
        VALUES ('Yema Hinchada', -1);
""", 'Yema Hinchada')

with ENG.connect() as c:
    df = pd.read_sql(text("SELECT * FROM Silver.Dim_Estado_Fenologico ORDER BY Orden_Estado"), c)
print('\n  Estado actual:')
print(df.to_string(index=False))


# ===========================================================================
# 5. DIM_PERSONAL — 220 evaluadores desde CSV
# Columnas: ID_Personal(identity), DNI, Nombre_Completo, Rol, Sexo, ...
# CSV header: DNI, Nombre, Evaluaciones
# ===========================================================================
section('5. Dim_Personal — cargar evaluadores faltantes')

csv_p = os.path.join(CSV_DIR, '04_dim_personal_FALTANTES.csv')
df_p = pd.read_csv(csv_p, dtype={'DNI': str})
print(f'  CSV: {len(df_p)} evaluadores')

inserted_p = 0
for _, row in df_p.iterrows():
    dni    = str(row['DNI']).strip().replace("'", "''")
    nombre = str(row['Nombre']).strip().replace("'", "''")
    n = run(f"""
        IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Personal WHERE DNI = N'{dni}')
            INSERT INTO Silver.Dim_Personal (DNI, Nombre_Completo, Rol)
            VALUES (N'{dni}', N'{nombre}', N'Evaluador');
    """, f'DNI {dni}')
    inserted_p += n

print(f'  Total insertados: {inserted_p}')


# ===========================================================================
# 6. DIM_GEOGRAFIA — 144 combinaciones Mod/Tur/Val faltantes
# INSERT batch usando JOIN a catálogos para resolver IDs
# ===========================================================================
section('6. Dim_Geografia — 144 combinaciones faltantes')

csv_g = os.path.join(CSV_DIR, '05_dim_geografia_FALTANTES.csv')
df_g = pd.read_csv(csv_g)
print(f'  CSV: {len(df_g)} combinaciones')

values_str = ',\n        '.join(
    f'({int(r["Modulo"])},{int(r["Turno"])},{int(r["Valvula"])})'
    for _, r in df_g.iterrows()
)

sql_geo = f"""
INSERT INTO Silver.Dim_Geografia (
    ID_Fundo_Catalogo,
    ID_Sector_Catalogo,
    ID_Modulo_Catalogo,
    ID_Turno_Catalogo,
    ID_Valvula_Catalogo,
    ID_Cama_Catalogo,
    Es_Test_Block,
    Nivel_Granularidad,
    Fecha_Inicio_Vigencia,
    Es_Vigente
)
SELECT
    1,                  -- Arandano Acp
    6,                  -- Sin_Sector_Mapa (patron de historicos sin sector asignado)
    m.ID_Modulo_Catalogo,
    t.ID_Turno_Catalogo,
    v.ID_Valvula_Catalogo,
    0,                  -- SIN_CAMA
    0,                  -- Es_Test_Block = false
    'HASTA_VALVULA',
    '2016-01-01',
    1                   -- Es_Vigente
FROM (VALUES
    {values_str}
) AS x(Modulo, Turno, Valvula)
JOIN Silver.Dim_Modulo_Catalogo  m ON m.Modulo = x.Modulo
JOIN Silver.Dim_Turno_Catalogo   t ON t.Turno  = x.Turno
JOIN Silver.Dim_Valvula_Catalogo v ON TRY_CAST(v.Valvula AS INT) = x.Valvula
WHERE NOT EXISTS (
    SELECT 1 FROM Silver.Dim_Geografia g
    WHERE g.ID_Modulo_Catalogo  = m.ID_Modulo_Catalogo
      AND g.ID_Turno_Catalogo   = t.ID_Turno_Catalogo
      AND g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
      AND g.ID_Cama_Catalogo    = 0
);
"""

run(sql_geo, 'Dim_Geografia batch')


# ===========================================================================
# RESUMEN FINAL
# ===========================================================================
section('RESUMEN FINAL — conteos post-carga')

checks = [
    ('Silver.Dim_Tiempo',            "WHERE Fecha BETWEEN '2016-01-01' AND '2019-12-31'", '2016-2019'),
    ('Silver.Dim_Campana',           'WHERE Anio_Cosecha BETWEEN 2016 AND 2019',           '2016-2019'),
    ('Silver.Dim_Variedad',          '',                                                   'total'),
    ('Silver.Dim_Personal',          "WHERE DNI NOT IN ('00000000')",                      'evaluadores reales'),
    ('Silver.Dim_Estado_Fenologico', '',                                                   'total'),
    ('Silver.Dim_Geografia',         '',                                                   'total'),
]
with ENG.connect() as c:
    for tbl, where, label in checks:
        n = c.execute(text(f"SELECT COUNT(*) FROM {tbl} {where}")).scalar()
        print(f'  {tbl.split(".")[1]:<28} {label:<25} => {n:,}')

print('\nDone. Todos los Dims están listos para la carga de Facts con FK estricto.')
