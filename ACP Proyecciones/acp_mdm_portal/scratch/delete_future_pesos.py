import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_comando, ejecutar_query

def delete_future_pesos():
    print("\n--- Iniciando limpieza de datos FUTUROS en Fact_Evaluacion_Pesos ---")
    
    # Primero contamos para confirmar
    count_sql = "SELECT COUNT(*) as n FROM Silver.Fact_Evaluacion_Pesos WHERE ID_Tiempo >= 20260518"
    df_count = ejecutar_query(count_sql)
    total_a_borrar = df_count.iloc[0]['n']
    
    if total_a_borrar == 0:
        print("No se encontraron registros para borrar desde el 18/05/2026.")
        return

    print(f"Se han identificado {total_a_borrar} filas para eliminar.")
    
    # Ejecutamos el borrado
    delete_sql = "DELETE FROM Silver.Fact_Evaluacion_Pesos WHERE ID_Tiempo >= 20260518"
    filas_afectadas = ejecutar_comando(delete_sql)
    
    print(f"Éxito: Se eliminaron {filas_afectadas} filas correctamente.")

if __name__ == "__main__":
    delete_future_pesos()
