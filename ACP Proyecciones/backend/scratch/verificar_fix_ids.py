import sys
import pandas as pd
from sqlalchemy.engine import Engine
from unittest.mock import MagicMock

# Rutas
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from silver.facts.fact_induccion_floral import ProcesadorInduccionFloral

def verificar_fix():
    print("Simulando datos de Bronce.Induccion_Floral...")
    # Mock data con duplicados tecnicos
    data = {
        'ID_Registro_Origen': [1001, 1002, 1003], # 1003 es duplicado de 1002
        'Modulo_Raw': ['M1', 'M1', 'M1'],
        'Fecha_Raw': ['2026-01-01', '2026-01-01', '2026-01-01'],
        'Variedad_Raw': ['Biloxi', 'Ventura', 'Ventura'], # Duplicado por Modulo+Fecha+Variedad
        'DNI_Raw': ['123', '456', '456'],
        'Tipo_Evaluacion_Raw': ['T1', 'T1', 'T1'],
        'Consumidor_Raw': ['C1', 'C1', 'C1']
    }
    df = pd.DataFrame(data)
    
    # Mock Engine y Config
    mock_engine = MagicMock(spec=Engine)
    
    # Instanciar procesador
    proc = ProcesadorInduccionFloral(mock_engine, columna_id='ID_Induccion_Floral')
    
    print(f"IDs procesados antes: {proc.ids_procesados}")
    
    # Ejecutar limpieza
    columnas_clave = ['Modulo_Raw', 'Fecha_Raw', 'Variedad_Raw', 'DNI_Raw', 'Tipo_Evaluacion_Raw', 'Consumidor_Raw']
    try:
        df_limpio = proc.pre_limpiar_duplicados_batch(df, columnas_clave)
        print("\n--- Resultados del Fix ---")
        print(f"Filas originales: {len(df)}")
        print(f"Filas tras limpieza: {len(df_limpio)}")
        print(f"IDs en tracking para PROCESADO: {proc.ids_procesados}")
        
        if 1003 in proc.ids_procesados:
            print("\n[OK] El ID duplicado (1003) fue capturado correctamente para ser marcado como procesado.")
        else:
            print("\n[ERROR] El ID duplicado no fue capturado.")
            
    except KeyError as e:
        print(f"\n[ERROR] Se detectó un KeyError: {e}")
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {e}")

if __name__ == "__main__":
    verificar_fix()
