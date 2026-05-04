"""
Test rapido de fact_sixweek.py contra la base de datos real.
Ejecutar desde: d:\\Proyecto2026\\ACP_DWH\\ACP Proyecciones\\ETL\\
"""
import sys
import os

# Asegurar que el ETL este en el path
ETL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ETL_DIR)

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

from config.conexion import obtener_engine, verificar_conexion
from silver.facts.fact_sixweek import (
    cargar_fact_sixweek,
    _extraer_maduracion,
    _extraer_peladas,
    _extraer_kg_base,
    _obtener_id_tiempo_semana_actual,
    _obtener_id_tiempo_hace_n_semanas,
    _margen_pesimista,
    _margen_optimista,
    _id_escenario_base,
    _semanas_historico,
)

def diagnosticar():
    print("\n" + "="*60)
    print("  DIAGNOSTICO Six-Week Projection")
    print("="*60)

    if not verificar_conexion():
        print("ERROR: Sin conexion a la base de datos.")
        return

    engine = obtener_engine()

    # Parametros
    margen_p = _margen_pesimista()
    margen_o = _margen_optimista()
    id_esc   = _id_escenario_base()
    semanas  = _semanas_historico()
    print(f"\n  Parametros:")
    print(f"    Margen pesimista : {margen_p}")
    print(f"    Margen optimista : {margen_o}")
    print(f"    ID Escenario     : {id_esc}")
    print(f"    Semanas historico: {semanas}")

    # Ventana temporal
    id_actual    = _obtener_id_tiempo_semana_actual(engine)
    id_historico = _obtener_id_tiempo_hace_n_semanas(engine, semanas)
    print(f"\n  Ventana temporal:")
    print(f"    ID_Tiempo semana actual  : {id_actual}")
    print(f"    ID_Tiempo hace {semanas} semanas : {id_historico}")

    if not id_historico:
        print("  ERROR: No se pudo determinar la ventana temporal. Revisa Silver.Dim_Tiempo.")
        return

    # Fuentes Silver
    df_mad = _extraer_maduracion(engine, id_historico)
    df_pel = _extraer_peladas(engine, id_historico)
    df_kg  = _extraer_kg_base(engine, id_historico)
    print(f"\n  Fuentes Silver:")
    print(f"    Fact_Maduracion  -> {len(df_mad)} filas de pct_maduracion")
    print(f"    Fact_Peladas     -> {len(df_pel)} filas de pct_productivas")
    print(f"    Fact_Cosecha_SAP -> {len(df_kg)} filas de kg_base")

    if df_mad.empty:
        print("  AVISO: Fact_Maduracion vacia en la ventana temporal.")
    else:
        print(f"\n  Muestra Maduracion (top 3):")
        print(df_mad.head(3).to_string(index=False))

    if df_kg.empty:
        print("  AVISO: No hay kg_base historico en Fact_Cosecha_SAP.")
    else:
        print(f"\n  Muestra kg_base (top 3):")
        print(df_kg.head(3).to_string(index=False))

    print("\n" + "-"*60)
    print("  EJECUTANDO cargar_fact_sixweek()...")
    print("-"*60)

    resultado = cargar_fact_sixweek(engine)

    print(f"\n  RESULTADO:")
    for k, v in resultado.items():
        if k != "cuarentena":
            print(f"    {k:20} : {v}")
    if resultado.get("cuarentena"):
        print(f"    cuarentena (n)   : {len(resultado['cuarentena'])}")

    print("\n" + "="*60)
    print("  FIN DEL DIAGNOSTICO")
    print("="*60 + "\n")


if __name__ == "__main__":
    diagnosticar()
