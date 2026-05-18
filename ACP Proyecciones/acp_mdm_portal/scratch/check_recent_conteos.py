import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def check_recent():
    print("\n--- Últimas 10 fechas con CONTEOS en la DB ---")
    sql = """
        SELECT TOP 10 ID_Tiempo, COUNT(*) as Filas
        FROM Silver.Fact_Conteo_Fenologico
        GROUP BY ID_Tiempo
        ORDER BY ID_Tiempo DESC
    """
    df = ejecutar_query(sql)
    print(df)

if __name__ == "__main__":
    check_recent()
