import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import ejecutar_query
import pandas as pd

sql = """
SELECT 
    dt.Anio, dt.Semana_ISO, 
    SUM(f.Cantidad_Organos) as Total_Org, 
    COUNT(DISTINCT f.ID_Geografia) as Unidades,
    CAST(SUM(f.Cantidad_Organos) AS FLOAT) / (NULLIF(COUNT(DISTINCT f.ID_Geografia), 0) * 10) as Org_Planta
FROM Silver.Fact_Conteo_Fenologico f
JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
GROUP BY dt.Anio, dt.Semana_ISO
ORDER BY Org_Planta DESC
"""

df = ejecutar_query(sql)
print(df.head(20))
