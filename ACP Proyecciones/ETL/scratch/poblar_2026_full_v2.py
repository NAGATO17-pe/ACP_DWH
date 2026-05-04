import sys
import pandas as pd
from datetime import datetime, timedelta
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

def poblar_datos_reales_2026():
    engine = obtener_engine()
    
    # 1. Limpieza
    print("Limpiando tablas...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Proyecciones"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Maduracion"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Peladas"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Cosecha_SAP"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Evaluacion_Pesos"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Conteo_Fenologico"))

    # 2. Generación de fechas (cada lunes desde enero)
    fecha_inicio = datetime(2026, 1, 5) # Primer lunes
    hoy = datetime.now()
    fechas = []
    curr = fecha_inicio
    while curr <= hoy:
        fechas.append(curr)
        curr += timedelta(days=7)

    variedades = [7, 32, 89]
    geografias = [1, 2, 3]
    
    print(f"Poblando {len(fechas)} semanas para {len(variedades)} variedades...")

    mad_data = []
    pel_data = []
    pes_data = []
    cos_data = []
    con_data = []

    ts_now = datetime.now()

    for i, fecha in enumerate(fechas):
        id_tiempo = int(fecha.strftime("%Y%m%d"))
        pct_mad_base = min(0.1 + (i * 0.05), 0.95)
        
        for geo in geografias:
            for var in variedades:
                # 1. Maduracion (frutos maduros vs totales)
                totales = 20 # Reducimos volumen para evitar lentitud
                maduros = int(totales * pct_mad_base)
                for organo_id in range(totales):
                    estado = 9 if organo_id < maduros else 2
                    mad_data.append({
                        "ID_Geografia": geo, 
                        "ID_Tiempo": id_tiempo, 
                        "ID_Variedad": var, 
                        "ID_Estado_Fenologico": estado,
                        "ID_Cinta": 1,
                        "ID_Organo": organo_id + 1,
                        "Fecha_Evento": fecha,
                        "Fecha_Sistema": ts_now,
                        "Estado_DQ": "OK",
                        "ID_Campana": 3
                    })

                # 2. Peladas (Productividad)
                pel_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, 
                    "Plantas_Productivas": 850, "Plantas_No_Productivas": 150, 
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK",
                    "ID_Campana": 3
                })

                # 3. Pesos
                pes_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var,
                    "Peso_Promedio_Baya_g": 3.2 + (i * 0.05), 
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK",
                    "ID_Campana": 3
                })

                # 4. Cosecha SAP (Kg Base)
                cos_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var,
                    "Kg_Neto_MP": 1200 + (i * 20), 
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK",
                    "ID_Campana": 3
                })

                # 5. Conteo (Carga)
                con_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var,
                    "Cantidad_Organos": 45, "Punto": 1, "ID_Estado_Fenologico": 5,
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK",
                    "ID_Campana": 3
                })

    # Inserción masiva
    with engine.begin() as conn:
        print("Insertando Maduracion...")
        pd.DataFrame(mad_data).to_sql("Fact_Maduracion", conn, schema="Silver", if_exists="append", index=False, chunksize=1000)
        print("Insertando Peladas...")
        pd.DataFrame(pel_data).to_sql("Fact_Peladas", conn, schema="Silver", if_exists="append", index=False)
        print("Insertando Pesos...")
        pd.DataFrame(pes_data).to_sql("Fact_Evaluacion_Pesos", conn, schema="Silver", if_exists="append", index=False)
        print("Insertando Cosecha...")
        pd.DataFrame(cos_data).to_sql("Fact_Cosecha_SAP", conn, schema="Silver", if_exists="append", index=False)
        print("Insertando Conteo...")
        pd.DataFrame(con_data).to_sql("Fact_Conteo_Fenologico", conn, schema="Silver", if_exists="append", index=False)

    print("Carga completa finalizada con éxito.")

if __name__ == "__main__":
    poblar_datos_reales_2026()
