import sys
import pandas as pd
from datetime import datetime
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

def poblar_datos_v6_fenologia():
    engine = obtener_engine()
    
    print("Limpiando para test de matriz fenológica...")
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
        
        for geo in geografias:
            for var in variedades:
                # Vamos a repartir 20 bayas en distintos estados para ver la curva
                # 4 Maduras, 4 Cremas, 4 Fase 2, 4 Fase 1, 4 Verdes
                distribucion = [
                    (9, 4), # Cosechable
                    (7, 4), # Crema
                    (6, 4), # Fase 2
                    (5, 4), # Fase 1
                    (4, 4)  # Verde
                ]
                
                organo_id = 1
                for estado, cant in distribucion:
                    for _ in range(cant):
                        mad_data.append({
                            "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, 
                            "ID_Estado_Fenologico": estado, "ID_Cinta": 1, "ID_Organo": organo_id, 
                            "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                        })
                        organo_id += 1

                # Resto de datos estándar con variabilidad
                pel_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, "Punto": 1,
                    "Botones_Florales": 0, "Flores": 0, "Bayas_Pequenas": 0, "Bayas_Grandes": 0,
                    "Fase_1": 0, "Fase_2": 0, "Bayas_Cremas": 0, "Bayas_Maduras": 0, "Bayas_Cosechables": 0,
                    "Plantas_Productivas": 800 + (geo*20), "Plantas_No_Productivas": 200, "Muestras": 1,
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

                cos_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, 
                    "ID_Condicion_Cultivo": 1, "Kg_Neto_MP": 1500 + (var * 5),
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

                pes_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, "ID_Personal": -1,
                    "Peso_Promedio_Baya_g": 3.5,
                    "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

                con_data.append({
                    "ID_Geografia": geo, "ID_Tiempo": id_tiempo, "ID_Variedad": var, "ID_Estado_Fenologico": 5,
                    "Cantidad_Organos": 40 + var, "Fecha_Evento": fecha, "Fecha_Sistema": ts_now, "Estado_DQ": "OK"
                })

    with engine.begin() as conn:
        pd.DataFrame(mad_data).to_sql("Fact_Maduracion", conn, schema="Silver", if_exists="append", index=False, chunksize=1000)
        pd.DataFrame(pel_data).to_sql("Fact_Peladas", conn, schema="Silver", if_exists="append", index=False)
        pd.DataFrame(cos_data).to_sql("Fact_Cosecha_SAP", conn, schema="Silver", if_exists="append", index=False)
        pd.DataFrame(pes_data).to_sql("Fact_Evaluacion_Pesos", conn, schema="Silver", if_exists="append", index=False)
        pd.DataFrame(con_data).to_sql("Fact_Conteo_Fenologico", conn, schema="Silver", if_exists="append", index=False)

    print("Carga fenológica para test de matriz completada.")

if __name__ == "__main__":
    poblar_datos_v6_fenologia()
