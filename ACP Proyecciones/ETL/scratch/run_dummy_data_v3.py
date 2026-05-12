import sys
import os
from datetime import datetime
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")

from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()
id_campana = 3
id_personal = -1
fecha_sistema = datetime.now()

sql_template = """
-- 1. Silver.Fact_Cosecha_SAP (para kg_base)
INSERT INTO Silver.Fact_Cosecha_SAP (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Condicion_Cultivo, Kg_Brutos, Kg_Neto_MP, Cantidad_Jabas, Fecha_Evento, Fecha_Sistema, Estado_DQ, ID_Campana)
VALUES 
(1, 20260410, 89, 1, 1500, 1400, 50, '2026-04-10', :fecha_sistema, 'OK', :id_campana),
(1, 20260417, 89, 1, 1600, 1500, 55, '2026-04-17', :fecha_sistema, 'OK', :id_campana),
(2, 20260410, 7, 1, 2000, 1900, 70, '2026-04-10', :fecha_sistema, 'OK', :id_campana),
(2, 20260417, 7, 1, 2100, 2000, 75, '2026-04-17', :fecha_sistema, 'OK', :id_campana),
(3, 20260410, 32, 1, 1200, 1100, 40, '2026-04-10', :fecha_sistema, 'OK', :id_campana);

-- 2. Silver.Fact_Maduracion (para pct_maduracion)
INSERT INTO Silver.Fact_Maduracion (ID_Personal, ID_Geografia, ID_Tiempo, ID_Variedad, ID_Estado_Fenologico, ID_Cinta, ID_Organo, Fecha_Evento, Fecha_Sistema, Estado_DQ, ID_Campana)
SELECT :id_personal, G, T, V, E, 1, O, CAST(CAST(T AS NVARCHAR) AS DATE), :fecha_sistema, 'OK', :id_campana
FROM (VALUES (1, 20260420, 89), (2, 20260420, 7), (3, 20260420, 32)) AS Base(G, T, V)
CROSS JOIN (VALUES (8), (8), (9), (4)) AS Est(E) 
CROSS JOIN (VALUES (1), (2), (3), (4), (5)) AS Org(O);

-- 3. Silver.Fact_Peladas (para pct_productivas)
INSERT INTO Silver.Fact_Peladas (ID_Geografia, ID_Tiempo, ID_Variedad, ID_Personal, Punto, Plantas_Productivas, Plantas_No_Productivas, Muestras, Fecha_Evento, Fecha_Sistema, Estado_DQ, ID_Campana)
VALUES 
(1, 20260420, 89, :id_personal, 1, 45, 5, 50, '2026-04-20', :fecha_sistema, 'OK', :id_campana),
(2, 20260420, 7, :id_personal, 1, 48, 2, 50, '2026-04-20', :fecha_sistema, 'OK', :id_campana),
(3, 20260420, 32, :id_personal, 1, 40, 10, 50, '2026-04-20', :fecha_sistema, 'OK', :id_campana);
"""

with engine.begin() as conn:
    statements = sql_template.split(';')
    for stmt in statements:
        if stmt.strip():
            conn.execute(text(stmt), {"fecha_sistema": fecha_sistema, "id_campana": id_campana, "id_personal": id_personal})
    print("Dummy data inserted successfully.")
