"""Verifica los datos insertados por el poblamiento."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import ejecutar_query

print("=" * 70)
print("VERIFICACION POST-POBLAMIENTO")
print("=" * 70)

# 1. Conteo por semana
df = ejecutar_query("""
    SELECT ID_Tiempo, COUNT(*) as registros, COUNT(DISTINCT ID_Variedad) as variedades,
           COUNT(DISTINCT ID_Geografia) as geografias
    FROM Silver.Fact_Conteo_Fenologico
    WHERE ID_Tiempo BETWEEN 20260201 AND 20260630
    GROUP BY ID_Tiempo
    ORDER BY ID_Tiempo
""")
print(f"\n[1] Fact_Conteo_Fenologico ({len(df)} semanas):")
for _, r in df.iterrows():
    print(f"  {r['ID_Tiempo']}: {r['registros']:>5} registros, {r['variedades']} variedades, {r['geografias']} geos")
print(f"  TOTAL: {df['registros'].sum():,} registros")

# 2. Peladas
df2 = ejecutar_query("""
    SELECT ID_Tiempo, COUNT(*) as registros
    FROM Silver.Fact_Peladas
    WHERE ID_Tiempo BETWEEN 20260201 AND 20260630
    GROUP BY ID_Tiempo ORDER BY ID_Tiempo
""")
print(f"\n[2] Fact_Peladas ({len(df2)} semanas):")
print(f"  TOTAL: {df2['registros'].sum():,} registros")

# 3. Pesos
df3 = ejecutar_query("""
    SELECT ID_Tiempo, COUNT(*) as registros
    FROM Silver.Fact_Evaluacion_Pesos
    WHERE ID_Tiempo BETWEEN 20260201 AND 20260630
    GROUP BY ID_Tiempo ORDER BY ID_Tiempo
""")
print(f"\n[3] Fact_Evaluacion_Pesos ({len(df3)} semanas):")
print(f"  TOTAL: {df3['registros'].sum():,} registros")

# 4. Cosecha SAP
df4 = ejecutar_query("""
    SELECT ID_Tiempo, COUNT(*) as registros, SUM(Kg_Neto_MP) as kg_total
    FROM Silver.Fact_Cosecha_SAP
    WHERE ID_Tiempo BETWEEN 20260101 AND 20260630
    GROUP BY ID_Tiempo ORDER BY ID_Tiempo
""")
print(f"\n[4] Fact_Cosecha_SAP ({len(df4)} semanas):")
print(f"  TOTAL: {df4['registros'].sum():,} registros, {df4['kg_total'].sum():,.0f} kg")

# 5. Proyecciones
df5 = ejecutar_query("""
    SELECT ID_Tiempo, COUNT(*) as registros
    FROM Silver.Fact_Proyecciones
    WHERE Version_Modelo = 'SixWeek-v1.0-test'
    GROUP BY ID_Tiempo ORDER BY ID_Tiempo
""")
print(f"\n[5] Fact_Proyecciones (test) ({len(df5)} semanas):")
print(f"  TOTAL: {df5['registros'].sum():,} registros")

# 6. Verificar integridad referencial
print("\n[6] Integridad Referencial:")
for fact in ['Fact_Conteo_Fenologico', 'Fact_Peladas', 'Fact_Evaluacion_Pesos']:
    orphans = ejecutar_query(f"""
        SELECT COUNT(*) as cnt FROM Silver.{fact} f
        LEFT JOIN Silver.Dim_Geografia g ON f.ID_Geografia = g.ID_Geografia
        WHERE g.ID_Geografia IS NULL AND f.ID_Tiempo BETWEEN 20260201 AND 20260630
    """)
    cnt = orphans.iloc[0]['cnt']
    status = "OK" if cnt == 0 else f"WARN: {cnt} huerfanas"
    print(f"  {fact}: {status}")

print("\n" + "=" * 70)
print("[OK] Verificacion completa.")
