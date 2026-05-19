"""Diagnóstico completo: tablas Bronce disponibles y columnas de Evaluacion_Vegetativa."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
with engine.connect() as conn:
    # 1. Tablas en Bronce
    tablas = conn.execute(text("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'Bronce' ORDER BY TABLE_NAME
    """)).fetchall()
    print("=== TABLAS EN BRONCE ===")
    for t in tablas:
        cnt = conn.execute(text(f"SELECT COUNT(*) FROM Bronce.[{t[0]}]")).scalar()
        print(f"  {t[0]:<40} {cnt:>8,} registros")

    # 2. Columnas de Bronce.Evaluacion_Vegetativa
    cols_veg = conn.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Bronce' AND TABLE_NAME = 'Evaluacion_Vegetativa'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
    print("\n=== COLUMNAS Bronce.Evaluacion_Vegetativa ===")
    for c in cols_veg:
        print(f"  {c[0]:<40} {c[1]}")

    # 3. Columnas Silver.Fact_Floracion
    cols_flor = conn.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Floracion'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
    print("\n=== COLUMNAS Silver.Fact_Floracion ===")
    for c in cols_flor:
        print(f"  {c[0]:<40} {c[1]}")

    # 4. Columnas Silver.Fact_Evaluacion_Vegetativa
    cols_ev = conn.execute(text("""
        SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Fact_Evaluacion_Vegetativa'
        ORDER BY ORDINAL_POSITION
    """)).fetchall()
    print("\n=== COLUMNAS Silver.Fact_Evaluacion_Vegetativa ===")
    for c in cols_ev:
        print(f"  {c[0]:<40} {c[1]}")

    # 5. Muestra de Bronce.Evaluacion_Vegetativa
    muestra = conn.execute(text("""
        SELECT TOP 2 * FROM Bronce.Evaluacion_Vegetativa
    """)).fetchall()
    print("\n=== MUESTRA Bronce.Evaluacion_Vegetativa (TOP 2) ===")
    for r in muestra:
        d = dict(r._mapping)
        for k, v in d.items():
            if v is not None and str(v).strip() not in ('', 'None'):
                print(f"  {k}: {v}")
        print("  ---")
