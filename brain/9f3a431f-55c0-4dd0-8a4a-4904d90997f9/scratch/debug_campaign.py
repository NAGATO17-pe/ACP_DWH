
import os
import urllib
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

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

def debug_campaigns():
    engine = get_engine()
    with engine.connect() as conn:
        print("--- Bridge_Modulo_Campana ---")
        df_bridge = pd.read_sql(text("SELECT TOP 10 * FROM Silver.Bridge_Modulo_Campana"), conn)
        print(df_bridge)
        
        print("\n--- Dim_Campana ---")
        df_campana = pd.read_sql(text("SELECT TOP 10 * FROM Silver.Dim_Campana"), conn)
        print(df_campana)
        
        print("\n--- Testing obtener_id_campana logic ---")
        # Let's try to find a real record to test
        query = """
        SELECT TOP 1 ID_Geografia, ID_Variedad, Fecha_Evento 
        FROM Silver.Fact_Maduracion 
        ORDER BY Fecha_Sistema DESC
        """
        fact = pd.read_sql(text(query), conn)
        if not fact.empty:
            id_geo = fact.iloc[0]['ID_Geografia']
            id_var = fact.iloc[0]['ID_Variedad']
            fecha = fact.iloc[0]['Fecha_Evento']
            print(f"Testing with: Geo={id_geo}, Var={id_var}, Fecha={fecha}")
            
            # Manual resolution steps
            geo_info = pd.read_sql(text(f"SELECT ID_Modulo_Catalogo FROM Silver.Dim_Geografia WHERE ID_Geografia = {id_geo}"), conn)
            if not geo_info.empty:
                id_mod_cat = geo_info.iloc[0]['ID_Modulo_Catalogo']
                print(f"ID_Modulo_Catalogo resolved: {id_mod_cat}")
                
                bridge_query = f"""
                SELECT * FROM Silver.Bridge_Modulo_Campana
                WHERE ID_Modulo_Catalogo = {id_mod_cat}
                  AND ID_Variedad = {id_var}
                  AND '{fecha}' BETWEEN Fecha_Inicio AND ISNULL(Fecha_Fin, '2099-12-31')
                """
                match = pd.read_sql(text(bridge_query), conn)
                print(f"Bridge matches: {len(match)}")
                print(match)
            else:
                print("ID_Geografia not found in Dim_Geografia!")
        else:
            print("No records found in Silver.Fact_Maduracion to test.")

if __name__ == "__main__":
    debug_campaigns()
