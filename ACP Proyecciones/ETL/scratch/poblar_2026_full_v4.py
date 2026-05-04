import sys
import pandas as pd
from datetime import datetime
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

def poblar_datos_v4():
    engine = obtener_engine()
    
    print("Limpiando tablas...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Proyecciones"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Maduracion"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Peladas"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Cosecha_SAP"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Evaluacion_Pesos"))
        conn.execute(text("TRUNCATE TABLE Silver.Fact_Conteo_Fenologico"))

    fechas = pd.date_range(start="2026-01-01", end=datetime.now(), freq="W-MON")
    variedades = [7, 32, 89]
    geografias = [1, 2, 3]
    ts_now = datetime.now()

    mad_data, pel_data, pes_data, cos_data, con_data = [], [], [], [], []

    for i, fecha in enumerate(fechas):
        id_tiempo = int(fecha.strftime("%Y%m%d"))
        pct_mad_base = min(0.1 + (i * 0.05), 0.95)
        
        for geo in geografias:
            for var in variedades:
                # Fact_Maduracion
                for o_id in range(1, 6): # Reducimos a 5 por eficiencia
                    mad_data.append({
                        "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, 
                        "ID_Estado_Fenologico": (9 if o_id <= 5*pct_mad_base else 2),
                        "ID_Cinta": 1, "ID_Organo": o_id, "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                    })

                # Fact_Peladas
                pel_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, "Punto": 1,
                    "Botones_Florales": 0, "Flores": 0, "Bayas_Pequenas": 0, "Bayas_Grandes": 0,
                    "Fase_1": 0, "Fase_2": 0, "Bayas_Cremas": 0, "Bayas_Maduras": 0, "Bayas_Cosechables": 0,
                    "Plantas_Productivas": 850, "Plantas_No_Productivas": 150, "Muestras": 1,
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

                # Fact_Cosecha_SAP
                cos_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, 
                    "ID_Condicion_Cultivo": 1, "Kg_Neto_MP": 1200 + (i*10),
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

                # Fact_Evaluacion_Pesos
                pes_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, "ID_Personal": -1,
                    "Peso_Promedio_Baya_g": 3.0 + (i*0.05),
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

                # Fact_Conteo_Fenologico
                con_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, "ID_Estado_Fenologico": 5,
                    "Cantidad_Organos": 45, "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

    with engine.begin() as conn:
        pd.DataFrame(mad_data).to_sql("Fact_Maduracion", conn, schema="Silver", if_exists="append", index=False, chunksize=1000)
        pd.DataFrame(pel_data).to_sql("Fact_Peladas", conn, schema="Silver", if_exists="append", index=False)
        pd.DataFrame(cos_data).to_sql("Fact_Cosecha_SAP", conn, schema="Silver", if_exists="append", index=False)
        pd.DataFrame(pes_data).to_sql("Fact_Evaluacion_Pesos", conn, schema="Silver", if_exists="append", index=False)
        pd.DataFrame(con_data).to_sql("Fact_Conteo_Fenologico", conn, schema="Silver", if_exists="append", index=False)

    print("Carga completa finalizada con éxito.")

if __name__ == "__main__":
    poblar_datos_v4()
