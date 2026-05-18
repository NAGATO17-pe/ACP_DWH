import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import ejecutar_query
import pandas as pd

sql = """
SELECT 
    f.ID_Tiempo, dt.Anio, dt.Semana_ISO,
    SUM(CASE WHEN e.Nombre_Estado = 'Madura' THEN f.Cantidad_Organos ELSE 0 END) as Maduras,
    SUM(CASE WHEN e.Nombre_Estado = 'Crema' THEN f.Cantidad_Organos ELSE 0 END) as Cremas,
    SUM(CASE WHEN e.Nombre_Estado = 'Verde' THEN f.Cantidad_Organos ELSE 0 END) as Verdes,
    SUM(f.Cantidad_Organos) as Total_General
FROM Silver.Fact_Conteo_Fenologico f
JOIN Silver.Dim_Estado_Fenologico e ON f.ID_Estado_Fenologico = e.ID_Estado_Fenologico
JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
WHERE dt.Anio IN (2024, 2025)
GROUP BY f.ID_Tiempo, dt.Anio, dt.Semana_ISO
ORDER BY f.ID_Tiempo DESC
"""

df = ejecutar_query(sql)

# Datos del Excel (para comparación)
excel_maduras = 2729
excel_cremas = 2284
excel_verdes = 58495

# Calcular "distancia" o parecido
df['diff_maduras'] = abs(df['Maduras'] - excel_maduras)
df['diff_cremas'] = abs(df['Cremas'] - excel_cremas)
df['diff_verdes'] = abs(df['Verdes'] - excel_verdes)
df['score'] = df['diff_maduras'] + df['diff_cremas'] + (df['diff_verdes'] / 10) # Menos peso a verdes por volumen

print("Top 10 semanas con conteo de Maduras más parecido al Excel:")
print(df.sort_values('diff_maduras').head(10)[['Anio', 'Semana_ISO', 'ID_Tiempo', 'Maduras', 'Cremas', 'Verdes', 'Total_General']])
