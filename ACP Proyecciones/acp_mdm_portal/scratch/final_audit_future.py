import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def final_audit():
    print("\n--- Auditoría Final de Datos Futuros (> 11/05/2026) ---")
    tablas = [
        "Silver.Fact_Conteo_Fenologico",
        "Silver.Fact_Peladas",
        "Silver.Fact_Evaluacion_Pesos"
    ]
    for t in tablas:
        res = ejecutar_query(f"SELECT COUNT(*) as n FROM {t} WHERE ID_Tiempo > 20260511")
        print(f"{t}: {res.iloc[0]['n']} filas encontradas.")

if __name__ == "__main__":
    final_audit()
