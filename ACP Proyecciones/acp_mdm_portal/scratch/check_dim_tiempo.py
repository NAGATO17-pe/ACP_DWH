import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def check_dim_tiempo():
    print("\n--- Columnas de Dim_Tiempo ---")
    df = ejecutar_query("SELECT TOP 1 * FROM Silver.Dim_Tiempo")
    print(df.columns.tolist())

if __name__ == "__main__":
    check_dim_tiempo()
