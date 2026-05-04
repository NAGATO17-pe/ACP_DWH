
import os
import sys
import urllib
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

# Add the ETL directory to sys.path
sys.path.append('D:/Proyecto2026/ACP_DWH/ACP Proyecciones/ETL')

from mdm.lookup import obtener_id_campana

def get_engine():
    load_dotenv("D:/Proyecto2026/ACP_DWH/ACP Proyecciones/.env")
    servidor = os.getenv('ACP_DB_SERVER', 'LCP-PAG-PRACTIC')
    base     = os.getenv('ACP_DB_DATABASE', 'ACP_DataWarehose_Proyecciones')
    driver   = os.getenv('ACP_DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    trusted  = os.getenv('ACP_DB_TRUSTED', 'True')

    if trusted.lower() == 'true':
        cadena = f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};Trusted_Connection=yes;TrustServerCertificate=yes;'
    else:
        usuario  = os.getenv('ACP_DB_USER')
        clave    = os.getenv('ACP_DB_PASSWORD')
        cadena = f'DRIVER={{{driver}}};SERVER={servidor};DATABASE={base};UID={usuario};PWD={clave};TrustServerCertificate=yes;'

    url = 'mssql+pyodbc:///?odbc_connect=' + urllib.parse.quote_plus(cadena)
    return create_engine(url)

def verify_fix():
    engine = get_engine()
    # Case 1: Standard with Geo (resolved via Dim_Geografia -> Bridge)
    id_geo = 2
    id_var = 22
    fecha = '2026-01-02'
    
    print(f"--- CASE 1: Standard Geo Match ---")
    id_campana = obtener_id_campana(id_geo, id_var, fecha, engine)
    print(f"Result ID_Campana: {id_campana}")
    
    # Case 2: No Geo, but Catalog ID provided (match con Dim_Catalogo*)
    id_mod_cat = 19 # I saw this in the bridge sample earlier
    print(f"\n--- CASE 2: No Geo, Catalog ID Match (Mod={id_mod_cat}) ---")
    id_campana_cat = obtener_id_campana(None, id_var, fecha, engine, id_modulo_catalogo=id_mod_cat)
    print(f"Result ID_Campana (Catalog): {id_campana_cat}")

    # Case 3: No Geo, No Catalog, No Variety (Fallback to Annual)
    print(f"\n--- CASE 3: Full Fallback (Annual) ---")
    id_campana_ann = obtener_id_campana(None, None, fecha, engine)
    print(f"Result ID_Campana (Annual): {id_campana_ann}")
    
    if id_campana_ann == 3: # ID 3 is 2026
        print("\nSuccess! The multi-level resolution logic is working.")
    else:
        print("\nFailed. Check the logic or data.")

if __name__ == "__main__":
    verify_fix()
