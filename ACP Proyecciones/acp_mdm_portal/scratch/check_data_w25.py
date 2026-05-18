import sys
import os
from datetime import datetime

# Añadir el path del proyecto para importar utils
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def check():
    target_date = 20260615
    print(f"--- Diagnóstico para ID_Tiempo: {target_date} ---")
    
    # Tablas individuales
    tablas = [
        "Silver.Fact_Conteo_Fenologico",
        "Silver.Fact_Peladas",
        "Silver.Fact_Evaluacion_Pesos"
    ]
    
    for t in tablas:
        res = ejecutar_query(f"SELECT COUNT(*) as n FROM {t} WHERE ID_Tiempo = {target_date}")
        count = res.iloc[0]['n'] if not res.empty else 0
        print(f"{t}: {count} filas")

    # Buscar en toda la Semana 25 (15 al 21 de junio)
    print("\n--- Registros de CONTEO en toda la Semana 25 (Jun 15-21) ---")
    sql_w25 = """
        SELECT ID_Tiempo, COUNT(*) as Filas
        FROM Silver.Fact_Conteo_Fenologico
        WHERE ID_Tiempo BETWEEN 20260615 AND 20260621
        GROUP BY ID_Tiempo
        ORDER BY ID_Tiempo
    """
    df_w25 = ejecutar_query(sql_w25)
    if df_w25.empty:
        print("No se encontraron CONTEOS en ningún día de la Semana 25.")
    else:
        print(df_w25)

    # Próximas fechas con Conteos
    print("\n--- Fechas más cercanas con CONTEOS (Cualquier semana) ---")
    sql_prox = """
        SELECT TOP 5 ID_Tiempo, COUNT(*) as Filas
        FROM Silver.Fact_Conteo_Fenologico
        GROUP BY ID_Tiempo
        ORDER BY ABS(ID_Tiempo - 20260615) ASC
    """
    df_prox = ejecutar_query(sql_prox)
    print(df_prox)

if __name__ == "__main__":
    check()
