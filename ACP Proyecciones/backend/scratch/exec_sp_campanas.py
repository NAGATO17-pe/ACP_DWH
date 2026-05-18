import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine
from sqlalchemy import text
import pandas as pd

engine = obtener_engine()
with engine.begin() as conn:
    print("Ejecutando Silver.sp_Sincronizar_Periodos_Campana...")
    conn.execute(text("EXEC Silver.sp_Sincronizar_Periodos_Campana"))
    
    print("\n--- Verificación: Dim_Campana ---")
    df_c = pd.read_sql("SELECT * FROM Silver.Dim_Campana", conn)
    print(df_c)
    
    print("\n--- Verificación: Bridge_Modulo_Campana (Muestra) ---")
    df_b = pd.read_sql("SELECT TOP 10 * FROM Silver.Bridge_Modulo_Campana", conn)
    print(df_b)
