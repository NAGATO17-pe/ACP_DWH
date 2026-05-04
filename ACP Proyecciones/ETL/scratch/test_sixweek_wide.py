"""
Test con ventana ampliada para validar contra datos reales disponibles.
Maduracion tiene datos hasta 2026-03-27.
Peladas tiene datos hasta 2025-12-24.
Se usa ventana de 20 semanas para capturar ambas.
"""
import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

from config.conexion import obtener_engine
from silver.facts.fact_sixweek import (
    _extraer_maduracion,
    _extraer_peladas,
    _extraer_kg_base,
    _calcular_proyeccion,
    _construir_payload,
)

engine = obtener_engine()

# Usar ventana amplia para tocar los datos que existen
# Maduracion max: 20260327, Peladas max: 20251224 -> usar desde 20251001
ID_TIEMPO_MIN = 20251001

print(f"\n[TEST] Ventana ampliada: ID_Tiempo >= {ID_TIEMPO_MIN}")

df_mad = _extraer_maduracion(engine, ID_TIEMPO_MIN)
df_pel = _extraer_peladas(engine, ID_TIEMPO_MIN)
df_kg  = _extraer_kg_base(engine, ID_TIEMPO_MIN)

print(f"\n  Fact_Maduracion  -> {len(df_mad)} filas")
print(f"  Fact_Peladas     -> {len(df_pel)} filas")
print(f"  Fact_Cosecha_SAP -> {len(df_kg)} filas (kg_base)")

if df_mad.empty:
    print("  AVISO: Maduracion vacia incluso con ventana amplia. Datos insuficientes.")
    sys.exit(0)

if df_pel.empty:
    print("  AVISO: Peladas vacia. Sin pct_productivas -> no se pueden calcular proyecciones.")
    # Mostrar al menos la maduracion calculada
    print("\n  Muestra Maduracion (top 5):")
    print(df_mad.head(5).to_string(index=False))
    sys.exit(0)

print("\n  Muestra Maduracion (top 5):")
print(df_mad.head(5).to_string(index=False))

print("\n  Muestra Peladas (top 5):")
print(df_pel.head(5).to_string(index=False))

# Calcular proyeccion (aunque no haya kg_base, la formula queda en 0)
if df_kg.empty:
    print("\n  AVISO: Fact_Cosecha_SAP vacia. kg_base = 0 para todas las combinaciones.")
    print("  La proyeccion de kg sera 0 sin historico de cosecha.")
    # Crear un kg_base artificial para visualizar la estructura del resultado
    import pandas as pd
    combos_uniq = df_mad[["ID_Geografia","ID_Variedad"]].drop_duplicates()
    df_kg = combos_uniq.copy()
    df_kg["kg_base"] = 1000.0  # valor de prueba para ver estructura
    print("  [SIMULACION] Se usa kg_base=1000 para mostrar el calculo.")

df_proy = _calcular_proyeccion(df_mad, df_pel, df_kg, 0.9906, 1.0107)
print(f"\n  Proyecciones calculadas: {len(df_proy)} combinaciones")

if not df_proy.empty:
    print("\n  Top 5 proyecciones:")
    cols = ["ID_Tiempo","ID_Geografia","ID_Variedad","pct_maduracion","pct_productivas","kg_base","Kg_Proyectados","Kg_Pesimista","Kg_Optimista"]
    print(df_proy[cols].head(5).to_string(index=False))

    # Construir payload sin insertar (solo ver la estructura)
    payload = _construir_payload(df_proy, engine, 4)
    print(f"\n  Payload generado: {len(payload)} registros listos para insertar")
    if payload:
        print("\n  Primer registro del payload:")
        for k, v in list(payload[0].items()):
            print(f"    {k:22} : {v}")
