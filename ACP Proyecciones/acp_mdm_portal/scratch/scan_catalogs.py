"""Escanea catálogos existentes para el poblamiento."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import ejecutar_query

# 1. Geografías vigentes
geo = ejecutar_query("""
    SELECT g.ID_Geografia, g.ID_Modulo_Catalogo, g.ID_Turno_Catalogo, g.ID_Valvula_Catalogo,
           g.ID_Fundo_Catalogo, g.ID_Sector_Catalogo, g.ID_Cama_Catalogo,
           m.Modulo, t.Turno, v.Valvula
    FROM Silver.Dim_Geografia g
    JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
    JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
    JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
    WHERE g.Es_Vigente = 1 AND m.Modulo > 0 AND t.Turno > 0
""")
print(f"Geografias vigentes: {len(geo)}")
print(f"Modulos unicos: {sorted(geo['Modulo'].unique().tolist())}")
print(f"Turnos unicos: {sorted(geo['Turno'].unique().tolist())}")
valvs = sorted(geo['Valvula'].unique().tolist())
print(f"Valvulas ({len(valvs)}): {valvs[:30]}")

# 2. Variedades
var = ejecutar_query("SELECT ID_Variedad, Nombre_Variedad FROM Silver.Dim_Variedad WHERE Es_Activa = 1")
for r in var.to_dict(orient="records"):
    print(f"  Variedad: {r}")

# 3. Conteos existentes
cnt = ejecutar_query("SELECT DISTINCT ID_Tiempo FROM Silver.Fact_Conteo_Fenologico ORDER BY ID_Tiempo")
print(f"ID_Tiempo en Conteo existente: {cnt['ID_Tiempo'].tolist()}")

# 4. Peladas existentes
pel = ejecutar_query("SELECT DISTINCT ID_Tiempo FROM Silver.Fact_Peladas ORDER BY ID_Tiempo")
print(f"ID_Tiempo en Peladas existente: {pel['ID_Tiempo'].tolist()}")

# 5. Pesos existentes
pes = ejecutar_query("SELECT DISTINCT ID_Tiempo FROM Silver.Fact_Evaluacion_Pesos ORDER BY ID_Tiempo")
print(f"ID_Tiempo en Pesos existente: {pes['ID_Tiempo'].tolist()}")

# 6. Cosecha SAP existentes
sap = ejecutar_query("SELECT DISTINCT ID_Tiempo FROM Silver.Fact_Cosecha_SAP ORDER BY ID_Tiempo")
print(f"ID_Tiempo en Cosecha SAP existente: {sap['ID_Tiempo'].tolist()}")

# 7. Proyecciones existentes
pro = ejecutar_query("SELECT DISTINCT ID_Tiempo FROM Silver.Fact_Proyecciones ORDER BY ID_Tiempo")
print(f"ID_Tiempo en Proyecciones existente: {pro['ID_Tiempo'].tolist()}")

# 8. Sample de una geografia para ver el patron
sample = geo.head(30)[['ID_Geografia', 'Modulo', 'Turno', 'Valvula']].to_dict(orient='records')
print(f"\nSample Geografias:")
for s in sample:
    print(f"  {s}")

# 9. Dim_Tiempo range check
dt = ejecutar_query("SELECT MIN(ID_Tiempo) as mn, MAX(ID_Tiempo) as mx FROM Silver.Dim_Tiempo")
print(f"\nDim_Tiempo rango: {dt.to_dict(orient='records')}")

# 10. Max IDs for identity columns
for tbl, col in [
    ("Fact_Conteo_Fenologico", "ID_Conteo_Fenologico"),
    ("Fact_Peladas", "ID_Peladas"),
    ("Fact_Evaluacion_Pesos", "ID_Evaluacion_Pesos"),
    ("Fact_Cosecha_SAP", "ID_Cosecha_SAP"),
    ("Fact_Proyecciones", "ID_Proyeccion"),
]:
    try:
        r = ejecutar_query(f"SELECT MAX({col}) as mx, COUNT(*) as cnt FROM Silver.{tbl}")
        print(f"  {tbl}: max_id={r.iloc[0]['mx']}, count={r.iloc[0]['cnt']}")
    except Exception as e:
        print(f"  {tbl}: ERROR {e}")
