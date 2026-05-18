"""
Test de verificacion de las optimizaciones ETL.

1. Verifica que los nuevos indices existen y tienen la estructura correcta.
2. Verifica que el lookup de geografia con diccionario O(1) produce los mismos
   resultados que el metodo anterior.
3. Mide latencia de queries criticas para Gold.
"""
import os
import sys
import time
import pyodbc
from dotenv import load_dotenv

# Agregar ETL al path para poder importar modulos
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

load_dotenv("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/.env")

server = os.getenv("ACP_DB_SERVER")
database = os.getenv("ACP_DB_DATABASE")
driver = os.getenv("ACP_DB_DRIVER", "ODBC Driver 18 for SQL Server")

conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"

def test_indices():
    """Verifica que los indices refactorizados y nuevos existen."""
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    indices_esperados = {
        'IX_FactCosecha_Tiempo_Variedad': 'Fact_Cosecha_SAP',
        'IX_FactConteoFen_Tiempo_Estado': 'Fact_Conteo_Fenologico',
        'IX_FactPeladas_Tiempo_Variedad': 'Fact_Peladas',
        'IX_FactFisiologia_Tiempo_Variedad': 'Fact_Fisiologia',
        'IX_FactPesos_Gold_Cobertura': 'Fact_Evaluacion_Pesos',
        'IX_FactMaduracion_Gold_Cobertura': 'Fact_Maduracion',
    }
    
    print("=" * 60)
    print("TEST 1: Verificacion de Indices")
    print("=" * 60)
    
    ok = True
    for idx_name, table_name in indices_esperados.items():
        cursor.execute(f"""
            SELECT COUNT(*) FROM sys.indexes i
            JOIN sys.objects o ON i.object_id = o.object_id
            JOIN sys.schemas s ON o.schema_id = s.schema_id
            WHERE i.name = '{idx_name}' AND s.name = 'Silver' AND o.name = '{table_name}'
        """)
        exists = cursor.fetchone()[0] > 0
        status = "[OK]" if exists else "[FAIL]"
        if not exists:
            ok = False
        print(f"  {status} {idx_name} en Silver.{table_name}")
    
    conn.close()
    return ok


def test_lookup_geografia():
    """Verifica que el nuevo lookup O(1) resuelve correctamente."""
    print()
    print("=" * 60)
    print("TEST 2: Lookup Geografia O(1) vs Pandas")
    print("=" * 60)
    
    from config.conexion import obtener_engine
    from mdm.lookup import _cargar_geografia, _cargar_indice_geografia, limpiar_cache
    
    limpiar_cache()
    engine = obtener_engine()
    
    # Cargar el DataFrame original
    df_geo = _cargar_geografia(engine)
    print(f"  Registros en Dim_Geografia vigente: {len(df_geo)}")
    
    # Cargar el indice de diccionario
    t0 = time.perf_counter()
    indice = _cargar_indice_geografia(engine)
    t_build = (time.perf_counter() - t0) * 1000
    print(f"  Tiempo para construir indice diccionario: {t_build:.2f} ms")
    print(f"  Claves unicas (Modulo,Turno,Valvula): {len(indice)}")
    
    # Verificar: para cada fila del DataFrame, el diccionario debe encontrarla
    errores = 0
    for _, fila in df_geo.iterrows():
        clave = (
            int(fila['ID_Modulo_Catalogo']),
            int(fila['ID_Turno_Catalogo']),
            int(fila['ID_Valvula_Catalogo']),
        )
        candidatos = indice.get(clave, [])
        ids_encontrados = [c['ID_Geografia'] for c in candidatos]
        id_esperado = int(fila['ID_Geografia'])
        
        if id_esperado not in ids_encontrados:
            errores += 1
            if errores <= 3:  # Solo mostrar primeros 3 errores
                print(f"  [FAIL] ID_Geografia={id_esperado} no encontrado para clave={clave}")
    
    if errores == 0:
        print(f"  [OK] Todas las {len(df_geo)} geografias resueltas correctamente via diccionario")
    else:
        print(f"  [FAIL] {errores} geografias no resueltas")
    
    # Benchmark: comparar velocidad de resolucion
    # Tomar 100 muestras del DataFrame
    muestra = df_geo.sample(min(100, len(df_geo)))
    
    # Metodo antiguo: Pandas mask
    t0 = time.perf_counter()
    for _, fila in muestra.iterrows():
        m, t, v = int(fila['ID_Modulo_Catalogo']), int(fila['ID_Turno_Catalogo']), int(fila['ID_Valvula_Catalogo'])
        mascara = (
            (df_geo['ID_Modulo_Catalogo'] == m) &
            (df_geo['ID_Turno_Catalogo'] == t) &
            (df_geo['ID_Valvula_Catalogo'] == v)
        )
        _ = df_geo[mascara]
    t_pandas = (time.perf_counter() - t0) * 1000
    
    # Metodo nuevo: diccionario
    t0 = time.perf_counter()
    for _, fila in muestra.iterrows():
        m, t, v = int(fila['ID_Modulo_Catalogo']), int(fila['ID_Turno_Catalogo']), int(fila['ID_Valvula_Catalogo'])
        _ = indice.get((m, t, v), [])
    t_dict = (time.perf_counter() - t0) * 1000
    
    speedup = t_pandas / t_dict if t_dict > 0 else float('inf')
    print(f"  Benchmark ({len(muestra)} lookups):")
    print(f"    Pandas mask: {t_pandas:.2f} ms")
    print(f"    Diccionario: {t_dict:.2f} ms")
    print(f"    Speedup: {speedup:.1f}x mas rapido")
    
    return errores == 0


def test_latencia_gold():
    """Mide latencia de queries criticas para Gold."""
    print()
    print("=" * 60)
    print("TEST 3: Latencia de Queries Gold")
    print("=" * 60)
    
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    queries = {
        "Mart_Fenologia (subquery Pesos)": """
            SELECT TOP 10 ID_Tiempo, ID_Geografia, ID_Variedad,
                   SUM(Cantidad_Bayas_Muestra) as Cant
            FROM Silver.Fact_Evaluacion_Pesos WITH (NOLOCK)
            GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
        """,
        "Mart_Fenologia (subquery Maduracion)": """
            SELECT TOP 10 m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad,
                   MAX(c.Color_Cinta) as Color
            FROM Silver.Fact_Maduracion m WITH (NOLOCK)
            JOIN Silver.Dim_Cinta c WITH (NOLOCK) ON c.ID_Cinta = m.ID_Cinta
            GROUP BY m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad
        """,
        "Mart_Cosecha (JOIN Proyecciones)": """
            SELECT TOP 10 cs.ID_Tiempo, cs.ID_Geografia, cs.ID_Variedad,
                   cs.Kg_Neto_MP, p.Kg_Proyectados
            FROM Silver.Fact_Cosecha_SAP cs WITH (NOLOCK)
            LEFT JOIN Silver.Fact_Proyecciones p WITH (NOLOCK)
                ON p.ID_Tiempo = cs.ID_Tiempo
                AND p.ID_Variedad = cs.ID_Variedad
                AND p.ID_Geografia = cs.ID_Geografia
                AND p.ID_Escenario = 4
        """,
        "Mart_Fisiologia (agregacion)": """
            SELECT TOP 10 f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad,
                   f.Tercio, AVG(f.Brotes_Productivos) as BP
            FROM Silver.Fact_Fisiologia f WITH (NOLOCK)
            GROUP BY f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, f.Tercio
        """,
    }
    
    for nombre, sql in queries.items():
        t0 = time.perf_counter()
        cursor.execute(sql)
        cursor.fetchall()
        latencia = (time.perf_counter() - t0) * 1000
        print(f"  {nombre}: {latencia:.2f} ms")
    
    conn.close()
    return True


if __name__ == "__main__":
    print()
    print("=" * 60)
    print("  SUITE DE VERIFICACION - OPTIMIZACIONES ETL")
    print("=" * 60)
    print()
    
    r1 = test_indices()
    r2 = test_lookup_geografia()
    r3 = test_latencia_gold()
    
    print()
    print("=" * 60)
    print("  RESULTADO FINAL")
    print("=" * 60)
    all_ok = r1 and r2 and r3
    print(f"  Indices SQL:          {'OK' if r1 else 'FAIL'}")
    print(f"  Lookup Geografia O(1): {'OK' if r2 else 'FAIL'}")
    print(f"  Latencia Gold:        {'OK' if r3 else 'FAIL'}")
    print(f"  Estado General:       {'TODAS LAS OPTIMIZACIONES VERIFICADAS' if all_ok else 'HAY FALLOS'}")
    print("=" * 60)
