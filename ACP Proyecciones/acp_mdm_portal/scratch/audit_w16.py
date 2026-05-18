import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def audit_w16():
    print("\n--- Auditoría Detallada: Semana 16 (13/04 al 19/04) ---")
    
    # 1. Conteos
    print("\n1. Fact_Conteo_Fenologico:")
    sql_c = """
        SELECT ID_Tiempo, COUNT(*) as Filas
        FROM Silver.Fact_Conteo_Fenologico
        WHERE ID_Tiempo BETWEEN 20260413 AND 20260419
        GROUP BY ID_Tiempo
    """
    print(ejecutar_query(sql_c))

    # 2. Peladas
    print("\n2. Fact_Peladas:")
    sql_p = """
        SELECT ID_Tiempo, COUNT(*) as Filas
        FROM Silver.Fact_Peladas
        WHERE ID_Tiempo BETWEEN 20260413 AND 20260419
        GROUP BY ID_Tiempo
    """
    print(ejecutar_query(sql_p))

    # 3. Pesos
    print("\n3. Fact_Evaluacion_Pesos:")
    sql_w = """
        SELECT ID_Tiempo, COUNT(*) as Filas
        FROM Silver.Fact_Evaluacion_Pesos
        WHERE ID_Tiempo BETWEEN 20260413 AND 20260419
        GROUP BY ID_Tiempo
    """
    print(ejecutar_query(sql_w))

    # 4. Revisar si hay datos en Dim_Tiempo para esos IDs
    print("\n4. Dim_Tiempo (Verificación de integridad):")
    sql_dt = """
        SELECT ID_Tiempo, Semana_ISO, Anio, Fecha
        FROM Silver.Dim_Tiempo
        WHERE ID_Tiempo BETWEEN 20260413 AND 20260419
    """
    print(ejecutar_query(sql_dt))

if __name__ == "__main__":
    audit_w16()
