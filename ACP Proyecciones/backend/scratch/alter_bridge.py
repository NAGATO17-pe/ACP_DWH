import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
with engine.begin() as conn:
    print("Agregando columnas a Silver.Bridge_Modulo_Campana...")
    conn.execute(text("ALTER TABLE Silver.Bridge_Modulo_Campana ADD Semana_Poda_ISO INT, Anio_Poda_ISO INT"))
    print("Columnas agregadas con éxito.")
