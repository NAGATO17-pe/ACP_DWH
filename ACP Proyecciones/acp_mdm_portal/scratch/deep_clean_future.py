import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_comando, ejecutar_query

def deep_clean_future():
    print("\n--- Limpieza PROFUNDA de datos FUTUROS (> 11/05/2026) ---")
    tablas = [
        "Silver.Fact_Conteo_Fenologico",
        "Silver.Fact_Peladas",
        "Silver.Fact_Evaluacion_Pesos"
    ]
    
    for t in tablas:
        # Borrar todo lo posterior a hoy
        sql = f"DELETE FROM {t} WHERE ID_Tiempo > 20260511"
        afectadas = ejecutar_comando(sql)
        print(f"{t}: {afectadas} filas eliminadas.")

    print("\n--- Verificación Final ---")
    for t in tablas:
        res = ejecutar_query(f"SELECT COUNT(*) as n FROM {t} WHERE ID_Tiempo > 20260511")
        print(f"{t}: {res.iloc[0]['n']} filas restantes.")

if __name__ == "__main__":
    deep_clean_future()
