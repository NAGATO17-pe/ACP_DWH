"""
normalizar_campana.py
=====================
Normaliza los valores de la columna "Campana" de los archivos historicos
y actualiza Dim_Campana con los años faltantes.

Reglas:
  2022.0          → 2022  (Excel serializa int como float)
  2025.3 / 2025.6 → 2025  (sub-periodo: tomar parte entera)
  2021-2022       → 2021  (rango: tomar primer año = inicio de campaña)
  2021 - 2022     → 2021  (ídem con espacios)
  2026-2027       → 2026
  2022            → 2022  (ya está bien)

Uso:
  from normalizar_campana import campana_a_anio
  anio = campana_a_anio("2022 - 2023")  # → 2022
"""

import re
import os
import urllib
import pandas as pd
from sqlalchemy import create_engine, text

CAD = ('DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;'
       'DATABASE=ACP_DataWarehose_Proyecciones;Trusted_Connection=yes;TrustServerCertificate=yes;')
ENG = create_engine('mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(CAD))

# Regex: extrae el primer grupo de 4 dígitos que empieza con 19xx o 20xx
_RE_YEAR = re.compile(r'\b((?:19|20)\d{2})\b')


def campana_a_anio(valor) -> int | None:
    """
    Normaliza cualquier formato de campaña a un Anio_Cosecha entero.
    Retorna None si no se puede parsear.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    s = str(valor).strip()
    # Buscar todos los años de 4 dígitos
    matches = _RE_YEAR.findall(s)
    if not matches:
        return None
    # Siempre tomar el primer año encontrado
    return int(matches[0])


def imprimir_mapping():
    """Muestra la tabla completa de mapeo valor → Anio_Cosecha."""
    CSV = os.path.join(os.path.dirname(__file__), 'audit_csv', '02_dim_campana_valores_archivo.csv')
    df = pd.read_csv(CSV)
    df['Anio_Cosecha'] = df['Valor_en_archivo'].apply(campana_a_anio)
    df = df.sort_values(['Anio_Cosecha', 'Frecuencia'], ascending=[True, False])
    print('\nMapping completo  Valor_en_archivo -> Anio_Cosecha')
    print('-' * 55)
    print(df[['Valor_en_archivo', 'Anio_Cosecha', 'Frecuencia']].to_string(index=False))
    sin_mapeo = df[df['Anio_Cosecha'].isna()]
    if not sin_mapeo.empty:
        print(f'\nATENCION: {len(sin_mapeo)} valores sin mapeo posible:')
        print(sin_mapeo.to_string(index=False))
    return df


def asegurar_campanas_en_db(df_mapping: pd.DataFrame):
    """
    Inserta en Dim_Campana los Anio_Cosecha que faltan.
    Es idempotente (WHERE NOT EXISTS).
    """
    anios = sorted(df_mapping['Anio_Cosecha'].dropna().unique().astype(int))
    print(f'\nAños necesarios en Dim_Campana: {anios}')
    insertados = 0
    for anio in anios:
        with ENG.begin() as c:
            n = c.execute(text(f"""
                IF NOT EXISTS (SELECT 1 FROM Silver.Dim_Campana WHERE Anio_Cosecha = {anio})
                BEGIN
                    INSERT INTO Silver.Dim_Campana (Anio_Cosecha, Nombre_Campana, Estado, Es_Activa)
                    VALUES ({anio}, N'Campaña {anio}',
                            CASE WHEN {anio} < YEAR(GETDATE()) THEN N'Cerrada' ELSE N'Activa' END,
                            CASE WHEN {anio} >= YEAR(GETDATE()) THEN 1 ELSE 0 END);
                END
            """)).rowcount
        if n:
            print(f'  INSERT Campaña {anio}')
            insertados += 1
    print(f'Insertados: {insertados} campañas nuevas')

    # Estado final
    with ENG.connect() as c:
        dim = pd.read_sql(text("SELECT * FROM Silver.Dim_Campana ORDER BY Anio_Cosecha"), c)
    print('\nDim_Campana final:')
    print(dim.to_string(index=False))
    return dim


def generar_lookup(df_mapping: pd.DataFrame, dim_campana: pd.DataFrame) -> dict:
    """
    Retorna dict {valor_original (str) : ID_Campana} listo para usar en el ETL.
    Ejemplo: {"2022-2023": 6, "2022.0": 6, "2022": 6}
    """
    anio_to_id = dict(zip(dim_campana['Anio_Cosecha'], dim_campana['ID_Campana']))
    lookup = {}
    for _, row in df_mapping.iterrows():
        anio = row['Anio_Cosecha']
        if pd.notna(anio):
            cid = anio_to_id.get(int(anio))
            if cid is not None:
                lookup[str(row['Valor_en_archivo']).strip()] = cid
    return lookup


if __name__ == '__main__':
    print('=' * 60)
    print('  Normalización de Campana')
    print('=' * 60)

    df_map   = imprimir_mapping()
    dim_c    = asegurar_campanas_en_db(df_map)
    lookup   = generar_lookup(df_map, dim_c)

    print(f'\nLookup generado: {len(lookup)} entradas')
    print('\nPrueba rápida:')
    for ejemplo in ['2022', '2022.0', '2022-2023', '2022 - 2023', '2025.3', '2026-2027']:
        print(f'  {ejemplo!r:20s} → ID_Campana = {lookup.get(ejemplo, "SIN MAPEO")}')
