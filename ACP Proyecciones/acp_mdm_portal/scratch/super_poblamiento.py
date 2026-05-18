"""
Super-Poblamiento Masivo (VERSIÓN DEFINITIVA CON LIMPIEZA).
"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.db import obtener_engine

def super_poblar():
    engine = obtener_engine()
    with engine.connect() as conn:
        geo = pd.read_sql("SELECT TOP 200 ID_Geografia FROM Silver.Dim_Geografia", conn)
        variedades = pd.read_sql("SELECT ID_Variedad FROM Silver.Dim_Variedad WHERE Nombre_Variedad IN ('Sekoya Pop', 'Sekoya Beauty', 'Ventura')", conn)
        
    if geo.empty or variedades.empty:
        print("Faltan dimensiones base.")
        return

    ahora = datetime.now()

    # --- POBLAR FACT_PELADAS ---
    print("Preparando Fact_Peladas...")
    peladas = []
    for g_id in geo['ID_Geografia'].unique():
        for v_id in variedades['ID_Variedad'].unique():
            for t_id in [20260201, 20260501, 20260505]:
                peladas.append({
                    'ID_Tiempo': t_id,
                    'ID_Geografia': g_id,
                    'ID_Variedad': v_id,
                    'Punto': 1,
                    'Muestras': 1,
                    'Plantas_Productivas': np.random.randint(8000, 14000),
                    'Plantas_No_Productivas': np.random.randint(100, 500),
                    'Fecha_Evento': ahora,
                    'Fecha_Sistema': ahora
                })
    
    # --- POBLAR FACT_CONTEO_FENOLOGICO ---
    print("Preparando Fact_Conteo_Fenologico...")
    conteos = []
    estados = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    semanas_eval = [20260201, 20260301, 20260401, 20260501, 20260505, 20260515, 20260601]
    
    for t_id in semanas_eval:
        for g_id in geo['ID_Geografia'].unique():
            for v_id in variedades['ID_Variedad'].unique():
                for e_id in estados:
                    cantidad = np.random.randint(400, 800) 
                    conteos.append({
                        'ID_Tiempo': t_id,
                        'ID_Geografia': g_id,
                        'ID_Variedad': v_id,
                        'ID_Estado_Fenologico': e_id,
                        'Punto': 1,
                        'Cantidad_Organos': cantidad,
                        'Fecha_Evento': ahora,
                        'Fecha_Sistema': ahora
                    })

    def insertar_con_merge(df, tabla, claves):
        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()
        
        # SQL Server MERGE o DELETE/INSERT para pruebas
        # Por simplicidad en script de poblamiento, usamos DELETE e INSERT por lote
        print(f"Limpiando y cargando {tabla}...")
        
        # Insertar por pedazos para no saturar
        batch_size = 500
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i : i + batch_size]
            
            # Borrar existentes en el batch para evitar duplicados de PK
            for _, row in batch.iterrows():
                where = " AND ".join([f"{k} = {row[k]}" for k in claves])
                cursor.execute(f"DELETE FROM {tabla} WHERE {where}")
            
            # Insertar batch
            cols = ", ".join(batch.columns)
            params = ", ".join(["?"] * len(batch.columns))
            sql = f"INSERT INTO {tabla} ({cols}) VALUES ({params})"
            cursor.executemany(sql, batch.values.tolist())
            raw_conn.commit()
            
        cursor.close()
        raw_conn.close()
        print(f"Completado {tabla}: {len(df)} registros.")

    insertar_con_merge(pd.DataFrame(peladas), "Silver.Fact_Peladas", ["ID_Tiempo", "ID_Geografia", "ID_Variedad", "Punto"])
    insertar_con_merge(pd.DataFrame(conteos), "Silver.Fact_Conteo_Fenologico", ["ID_Tiempo", "ID_Geografia", "ID_Variedad", "ID_Estado_Fenologico", "Punto"])

if __name__ == "__main__":
    super_poblar()
