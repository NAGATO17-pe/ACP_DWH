import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def inspect_peladas_future():
    print("\n--- Inspección de datos FUTUROS en Fact_Peladas ---")
    sql = """
        SELECT ID_Tiempo, COUNT(*) as Filas, MIN(Fecha_Sistema) as Min_FS, MAX(Fecha_Sistema) as Max_FS
        FROM Silver.Fact_Peladas
        WHERE ID_Tiempo > 20260511
        GROUP BY ID_Tiempo
        ORDER BY ID_Tiempo
    """
    df = ejecutar_query(sql)
    print(df)

if __name__ == "__main__":
    inspect_peladas_future()
