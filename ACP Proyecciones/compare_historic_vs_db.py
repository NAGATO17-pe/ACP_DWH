"""
compare_historic_vs_db.py
=========================
Compara los archivos de Data Historica contra la base ACP_DataWarehose_Proyecciones.

Salida: resumen ejecutivo por archivo (totales, cobertura anual, distribucion semanal,
gaps, consistencia fecha<->semana ISO cuando hay columna Fecha).
"""
import os
import urllib
from collections import OrderedDict

import pandas as pd
from sqlalchemy import create_engine, text

BASE = r'D:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\data\Data Historica'

CAD = ('DRIVER={ODBC Driver 18 for SQL Server};'
       'SERVER=localhost;DATABASE=ACP_DataWarehose_Proyecciones;'
       'Trusted_Connection=yes;TrustServerCertificate=yes;')
URL = 'mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(CAD)
ENG = create_engine(URL)


def _norm(s: str) -> str:
    return s.strip().lower().replace(' ', '_')


def _read_file(name: str) -> pd.DataFrame:
    p = os.path.join(BASE, name)
    if name.endswith('.csv'):
        df = pd.read_csv(p, sep=';', encoding='utf-8-sig')
    else:
        df = pd.read_excel(p, sheet_name=0)
    # Fix mojibake columns: Excel files have 'Campa?a', 'A?o' etc.
    rename = {}
    for c in df.columns:
        nc = (c.replace('﻿', '')
                .replace('Campa\xf1a', 'Campana').replace('Campa?a', 'Campana')
                .replace('Campa\xa9a', 'Campana').replace('Campa\x91a', 'Campana')
                .replace('A\xf1o', 'Anio').replace('A?o', 'Anio')
                .replace('M\xf3dulo', 'Modulo').replace('M?dulo', 'Modulo')
                .replace('V\xe1lvula', 'Valvula').replace('V?lvula', 'Valvula')
                .replace('\xc1rea', 'Area').replace('?rea', 'Area')
                .replace('CAMPA\xd1A', 'Campana').replace('CAMPA?A', 'Campana'))
        # Generic: strip any non-ascii fallback char ('?')
        rename[c] = nc.strip()
    df = df.rename(columns=rename)
    return df


def db_table_summary(table: str, fecha_col: str = 'Fecha_Evento') -> pd.DataFrame:
    """Counts per (Anio, Semana_ISO) joining via ID_Tiempo."""
    q = text(f"""
        SELECT t.Anio AS Anio, t.Semana_ISO AS Semana, COUNT(*) AS Filas_DB
        FROM Silver.{table} f
        LEFT JOIN Silver.Dim_Tiempo t ON f.ID_Tiempo = t.ID_Tiempo
        GROUP BY t.Anio, t.Semana_ISO
        ORDER BY t.Anio, t.Semana_ISO
    """)
    with ENG.connect() as c:
        return pd.read_sql(q, c)


def db_table_total(table: str) -> int:
    with ENG.connect() as c:
        return c.execute(text(f"SELECT COUNT(*) FROM Silver.{table}")).scalar()


def section(title):
    return '\n' + '='*90 + f'\n  {title}\n' + '='*90


def analyze(file_name, table, file_year_col=None, file_week_col=None,
            file_date_col=None, file_campana_col=None, week_parser=None):
    out = []
    out.append(section(f'{file_name}  ->  Silver.{table}'))

    df = _read_file(file_name)
    total_file = len(df)
    total_db = db_table_total(table)
    out.append(f'Filas archivo : {total_file:>10,}')
    out.append(f'Filas DB      : {total_db:>10,}')
    out.append(f'Delta (DB-Arc): {total_db - total_file:>10,}')

    # Parse year / week from file
    if file_year_col and file_week_col:
        anio = pd.to_numeric(df[file_year_col], errors='coerce')
        if week_parser:
            sem = df[file_week_col].apply(week_parser)
        else:
            sem = pd.to_numeric(df[file_week_col], errors='coerce')
        file_pivot = (pd.DataFrame({'Anio': anio, 'Semana': sem})
                        .dropna().astype(int)
                        .groupby(['Anio', 'Semana']).size()
                        .rename('Filas_Archivo').reset_index())
    elif file_date_col:
        f = pd.to_datetime(df[file_date_col], errors='coerce')
        anio = f.dt.isocalendar().year
        sem = f.dt.isocalendar().week
        file_pivot = (pd.DataFrame({'Anio': anio, 'Semana': sem})
                        .dropna().astype(int)
                        .groupby(['Anio', 'Semana']).size()
                        .rename('Filas_Archivo').reset_index())
    else:
        file_pivot = None

    # DB pivot
    db_pivot = db_table_summary(table)

    # Coverage report
    if file_pivot is not None:
        years_f = sorted(file_pivot['Anio'].unique())
        years_d = sorted(db_pivot['Anio'].dropna().unique().tolist())
        out.append(f'Anios archivo : {years_f}')
        out.append(f'Anios DB      : {years_d}')

        merged = file_pivot.merge(db_pivot, on=['Anio', 'Semana'], how='outer').fillna(0)
        merged['Filas_Archivo'] = merged['Filas_Archivo'].astype(int)
        merged['Filas_DB'] = merged['Filas_DB'].astype(int)
        merged['Delta'] = merged['Filas_DB'] - merged['Filas_Archivo']

        # Per-year totals
        per_year = merged.groupby('Anio').agg(
            Sem_archivo=('Filas_Archivo', lambda s: int((s > 0).sum())),
            Sem_DB=('Filas_DB', lambda s: int((s > 0).sum())),
            Filas_archivo=('Filas_Archivo', 'sum'),
            Filas_DB=('Filas_DB', 'sum'),
        ).reset_index()
        per_year['Delta'] = per_year['Filas_DB'] - per_year['Filas_archivo']
        out.append('\nResumen por anio (semanas con datos / filas):')
        out.append(per_year.to_string(index=False))

        # Gaps
        only_file = merged[(merged['Filas_Archivo'] > 0) & (merged['Filas_DB'] == 0)]
        only_db = merged[(merged['Filas_DB'] > 0) & (merged['Filas_Archivo'] == 0)]
        out.append(f'\nSemanas en archivo y NO en DB : {len(only_file)}')
        if len(only_file):
            sample = only_file.head(15)[['Anio', 'Semana', 'Filas_Archivo']]
            out.append(sample.to_string(index=False))
        out.append(f'\nSemanas en DB y NO en archivo : {len(only_db)}')
        if len(only_db):
            sample = only_db.head(15)[['Anio', 'Semana', 'Filas_DB']]
            out.append(sample.to_string(index=False))
    else:
        # No year/week in file: compare by Campana
        if file_campana_col and file_campana_col in df.columns:
            file_cmp = (df.groupby(file_campana_col).size()
                          .rename('Filas_Archivo').reset_index())
            file_cmp = file_cmp.rename(columns={file_campana_col: 'Anio'})
            file_cmp['Anio'] = pd.to_numeric(file_cmp['Anio'], errors='coerce')
            file_cmp = file_cmp.dropna(subset=['Anio'])
            file_cmp['Anio'] = file_cmp['Anio'].astype(int)
            with ENG.connect() as c:
                db_cmp = pd.read_sql(text(f"""
                    SELECT t.Anio AS Anio, COUNT(*) AS Filas_DB
                    FROM Silver.{table} f
                    LEFT JOIN Silver.Dim_Tiempo t ON f.ID_Tiempo = t.ID_Tiempo
                    GROUP BY t.Anio
                    ORDER BY t.Anio
                """), c)
            merged_y = file_cmp.merge(db_cmp, on='Anio', how='outer').fillna(0)
            merged_y['Filas_Archivo'] = merged_y['Filas_Archivo'].astype(int)
            merged_y['Filas_DB'] = merged_y['Filas_DB'].astype(int)
            merged_y['Delta'] = merged_y['Filas_DB'] - merged_y['Filas_Archivo']
            out.append('\nComparacion por Campana/Anio (archivo no tiene Fecha/Semana):')
            out.append(merged_y.to_string(index=False))
        else:
            out.append('\n(Sin Fecha ni Anio/Semana parseable; solo conteo total.)')

    # Date<->ISO-week consistency (if file has both Fecha and Semana declared)
    if file_date_col and file_week_col and file_week_col in df.columns:
        f = pd.to_datetime(df[file_date_col], errors='coerce')
        sem_dec = pd.to_numeric(df[file_week_col], errors='coerce')
        sem_iso = f.dt.isocalendar().week
        mask = f.notna() & sem_dec.notna()
        if mask.any():
            equal = (sem_iso[mask].astype(int) == sem_dec[mask].astype(int))
            pct = 100.0 * equal.sum() / mask.sum()
            out.append(f'\nConsistencia Fecha <-> Semana declarada: {equal.sum():,}/{mask.sum():,} ({pct:.2f}%) coinciden con ISO week')
            if equal.sum() != mask.sum():
                bad = pd.DataFrame({
                    'Fecha': f[mask],
                    'Semana_declarada': sem_dec[mask].astype(int),
                    'Semana_ISO_calc': sem_iso[mask].astype(int),
                })
                bad = bad[bad['Semana_declarada'] != bad['Semana_ISO_calc']]
                ejemplos = (bad.groupby(['Semana_declarada', 'Semana_ISO_calc'])
                              .size().rename('n').reset_index()
                              .sort_values('n', ascending=False).head(10))
                out.append('Discrepancias mas frecuentes (declarada -> ISO calc):')
                out.append(ejemplos.to_string(index=False))

    return '\n'.join(out)


def _parse_sem_str(v):
    """Parse 'Sem 31' -> 31, returns NaN otherwise."""
    if pd.isna(v):
        return float('nan')
    s = str(v).strip().lower().replace('sem', '').strip()
    try:
        return int(s)
    except ValueError:
        return float('nan')


def main():
    parts = []
    parts.append('REPORTE COMPARATIVO  Data Historica  vs  ACP_DataWarehose_Proyecciones')
    parts.append('Generado: ' + pd.Timestamp.now().isoformat(timespec='seconds'))

    parts.append(analyze(
        'fact_Fenologia.xlsx', 'Fact_Conteo_Fenologico',
        file_year_col='Anio', file_week_col='Semana',
    ))
    parts.append(analyze(
        'fact_Evaluacion_vegetativa.xlsx', 'Fact_Evaluacion_Vegetativa',
        file_date_col='Fecha', file_week_col='Semana',
    ))
    parts.append(analyze(
        'fact_Censo_Plantas.xlsx', 'Fact_Censo_Plantas',
        file_campana_col='Campana',
    ))
    parts.append(analyze(
        'fact_calidad_poda.csv', 'Fact_Ciclo_Poda',
        file_year_col='Anio', file_week_col='Sem Poda',
    ))
    parts.append(analyze(
        'Fact_pesos.xlsx', 'Fact_Evaluacion_Pesos',
        file_year_col='Anio', file_week_col='Semana',
        week_parser=_parse_sem_str,
    ))
    parts.append(analyze(
        'historico_BI_Cosecha3.xlsx', 'Fact_Cosecha_SAP',
        file_date_col='Fecha', file_week_col='Semana',
    ))

    report = '\n'.join(parts)
    print(report)
    out_path = os.path.join(os.path.dirname(__file__), 'REPORTE_DATA_HISTORICA_vs_DB.txt')
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(report)
    print(f'\n\nReporte guardado en: {out_path}')


if __name__ == '__main__':
    main()
