import os
import time
import pyodbc
from dotenv import load_dotenv

# Cargar variables de entorno de la raiz del proyecto
load_dotenv("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/.env")

def get_conn():
    server = os.getenv("ACP_DB_SERVER")
    database = os.getenv("ACP_DB_DATABASE")
    driver = os.getenv("ACP_DB_DRIVER", "ODBC Driver 18 for SQL Server")
    
    # Windows Auth
    conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    return pyodbc.connect(conn_str)

def run_test():
    print("--- TEST DE SQL DIRECTO (OPTIMIZACIONES APLICADAS) ---")
    conn = get_conn()
    cursor = conn.cursor()
    
    # 1. Test Geografia con JOINs, COUNT(*) OVER() y NOLOCK
    print("\n1. Test Geografia (Single-Trip Pagination with JOINs)...")
    sql = """
        SELECT TOP 10 
            fn.Fundo AS fundo, md.Modulo AS modulo, COUNT(*) OVER() AS total_rows
        FROM Silver.Dim_Geografia g WITH (NOLOCK)
        JOIN Silver.Dim_Fundo_Catalogo fn WITH (NOLOCK) ON g.ID_Fundo_Catalogo = fn.ID_Fundo_Catalogo
        JOIN Silver.Dim_Modulo_Catalogo md WITH (NOLOCK) ON g.ID_Modulo_Catalogo = md.ID_Modulo_Catalogo
        WHERE g.Es_Vigente = 1
        ORDER BY fn.Fundo, md.Modulo
    """
    inicio = time.perf_counter()
    cursor.execute(sql)
    rows = cursor.fetchall()
    fin = time.perf_counter()
    
    if rows:
        total = rows[0].total_rows
        print(f"   [OK] Total reportado: {total} registros.")
        print(f"   [OK] Filas recuperadas: {len(rows)}")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")

    # 2. Test Conteo Fenologico con el nuevo Indice
    print("\n2. Test Conteo Fenologico (Performance Index)...")
    sql = """
        SELECT TOP 10 ID_Tiempo, ID_Geografia, SUM(Cantidad_Organos) as total
        FROM Silver.Fact_Conteo_Fenologico WITH (NOLOCK)
        WHERE ID_Tiempo = (SELECT MAX(ID_Tiempo) FROM Silver.Fact_Conteo_Fenologico WITH (NOLOCK))
        GROUP BY ID_Tiempo, ID_Geografia
    """
    inicio = time.perf_counter()
    cursor.execute(sql)
    rows = cursor.fetchall()
    fin = time.perf_counter()
    print(f"   [OK] Filas recuperadas: {len(rows)}")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")

    # 3. Test Peladas con NOLOCK
    print("\n3. Test Peladas (NOLOCK)...")
    sql = """
        SELECT TOP 10 ID_Tiempo, ID_Geografia, Plantas_Productivas
        FROM Silver.Fact_Peladas WITH (NOLOCK)
        ORDER BY ID_Tiempo DESC
    """
    inicio = time.perf_counter()
    cursor.execute(sql)
    rows = cursor.fetchall()
    fin = time.perf_counter()
    print(f"   [OK] Filas recuperadas: {len(rows)}")
    print(f"   Latencia: {(fin - inicio)*1000:.2f} ms")

    conn.close()
    print("\nOK: Tests SQL finalizados con exito.")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"Error: {e}")
