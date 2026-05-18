import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def inspect_june():
    print("\n--- Inspección de datos de JUNIO en Fact_Evaluacion_Pesos ---")
    # Intentamos traer los registros de junio para ver qué son
    sql = """
        SELECT TOP 10 
            p.*,
            v.Nombre_Variedad
        FROM Silver.Fact_Evaluacion_Pesos p
        JOIN Silver.Dim_Variedad v ON p.ID_Variedad = v.ID_Variedad
        WHERE p.ID_Tiempo >= 20260601
        ORDER BY p.ID_Tiempo ASC
    """
    df = ejecutar_query(sql)
    if df.empty:
        print("No se encontraron registros de junio.")
    else:
        print(df.to_string())

if __name__ == "__main__":
    inspect_june()
