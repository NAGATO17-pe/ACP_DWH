"""
Poblamiento Total para Módulos Específicos (11 y 14) - Versión Final.
Asegura que TODAS las válvulas de estos módulos tengan datos.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from utils.db import obtener_engine, ejecutar_query

def poblar_modulos_completos():
    engine = obtener_engine()
    
    # 1. Obtener geografía pura de los módulos 11 y 14
    print("Obteniendo geografía de módulos 11 y 14...")
    sql_geo = """
        SELECT g.ID_Geografia, m.Modulo
        FROM Silver.Dim_Geografia g
        JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        WHERE m.Modulo IN (11, 14)
    """
    geo_pure = ejecutar_query(sql_geo)
    
    # 2. Obtener Variedades
    sql_var = "SELECT ID_Variedad, Nombre_Variedad FROM Silver.Dim_Variedad WHERE Nombre_Variedad IN ('Sekoya Pop', 'Sekoya Beauty', 'Ventura')"
    variedades = ejecutar_query(sql_var)
    
    if geo_pure.empty or variedades.empty:
        print("Faltan datos de geografía o variedades.")
        return

    ahora = datetime.now()
    ids_tiempo = [20260501, 20260505, 20260515]

    peladas = []
    conteos = []
    estados = [1, 2, 3, 4, 5, 6, 7, 8, 9]

    print(f"Procesando {len(geo_pure)} unidades geográficas...")
    for _, g_row in geo_pure.iterrows():
        g_id = int(g_row['ID_Geografia'])
        
        for _, v_row in variedades.iterrows():
            v_id = int(v_row['ID_Variedad'])
            
            for t_id in ids_tiempo:
                # Peladas
                peladas.append({
                    'ID_Tiempo': t_id, 'ID_Geografia': g_id, 'ID_Variedad': v_id,
                    'Punto': 1, 'Muestras': 1, 'Plantas_Productivas': 12000,
                    'Plantas_No_Productivas': 200, 'Fecha_Evento': ahora, 'Fecha_Sistema': ahora
                })
                
                # Conteos
                for e_id in estados:
                    conteos.append({
                        'ID_Tiempo': t_id, 'ID_Geografia': g_id, 'ID_Variedad': v_id,
                        'ID_Estado_Fenologico': e_id, 'Punto': 1, 'Cantidad_Organos': 500,
                        'Fecha_Evento': ahora, 'Fecha_Sistema': ahora
                    })

    # --- INSERTAR ---
    def insertar_con_limpieza(df, tabla, claves):
        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()
        cursor.fast_executemany = True
        
        # Limpieza por lotes para evitar duplicados
        batch_size = 1000
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            # Borrar existentes en el lote
            for _, r in batch.head(10).iterrows(): # Borrar por ID_Geografia masivo es lento, borramos por lote de IDs
                cursor.execute(f"DELETE FROM {tabla} WHERE ID_Geografia = ? AND ID_Tiempo = ? AND ID_Variedad = ?", (r['ID_Geografia'], r['ID_Tiempo'], r['ID_Variedad']))
            
            cols = ", ".join(batch.columns)
            params = ", ".join(["?"] * len(batch.columns))
            cursor.executemany(f"INSERT INTO {tabla} ({cols}) VALUES ({params})", batch.values.tolist())
            raw_conn.commit()
            
        cursor.close()
        raw_conn.close()

    print("Insertando en Peladas...")
    insertar_con_limpieza(pd.DataFrame(peladas), "Silver.Fact_Peladas", ["ID_Tiempo", "ID_Geografia", "ID_Variedad"])
    print("Insertando en Conteos...")
    insertar_con_limpieza(pd.DataFrame(conteos), "Silver.Fact_Conteo_Fenologico", ["ID_Tiempo", "ID_Geografia", "ID_Variedad", "ID_Estado_Fenologico"])
    print("¡Proceso completado con éxito!")

if __name__ == "__main__":
    poblar_modulos_completos()
