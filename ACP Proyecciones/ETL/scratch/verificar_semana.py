from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
query_maduracion = text("""
    SELECT TOP 10 * FROM Silver.Fact_Maduracion 
    ORDER BY Fecha_Corte DESC
""")

try:
    with engine.connect() as conn:
        print("--- Matriz de Maduración Reciente ---")
        results = conn.execute(query_maduracion).fetchall()
        if results:
            keys = results[0]._mapping.keys()
            print(" | ".join(keys))
            for r in results:
                print(" | ".join([str(v) for v in r]))
        else:
            print("No se encontraron datos en Silver.Fact_Maduracion")
            
        print("\n--- Conteos Fenológicos para Semana 202619 ---")
        query_conteo = text("""
            SELECT TOP 5 * FROM Silver.Fact_Conteo_Fenologico 
            WHERE ID_Semana_ISO = 202619
        """)
        results_conteo = conn.execute(query_conteo).fetchall()
        if results_conteo:
            keys_conteo = results_conteo[0]._mapping.keys()
            print(" | ".join(keys_conteo))
            for r in results_conteo:
                print(" | ".join([str(v) for v in r]))
except Exception as e:
    print(f"Error: {e}")
