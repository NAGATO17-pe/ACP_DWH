import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def identify_future_data():
    print("\n--- Identificación de datos FUTUROS en Fact_Evaluacion_Pesos ---")
    # Hoy es 2026-05-11
    sql = """
        SELECT 
            ID_Tiempo, 
            MIN(Fecha_Evento) as Min_Fecha_Evento,
            MAX(Fecha_Evento) as Max_Fecha_Evento,
            COUNT(*) as Total_Filas,
            MIN(Fecha_Sistema) as Primera_Insercion,
            MAX(Fecha_Sistema) as Ultima_Insercion
        FROM Silver.Fact_Evaluacion_Pesos
        WHERE ID_Tiempo > 20260511
        GROUP BY ID_Tiempo
        ORDER BY ID_Tiempo
    """
    df = ejecutar_query(sql)
    if df.empty:
        print("No se encontraron datos futuros al 11/05/2026.")
    else:
        print(df.to_string())

if __name__ == "__main__":
    identify_future_data()
