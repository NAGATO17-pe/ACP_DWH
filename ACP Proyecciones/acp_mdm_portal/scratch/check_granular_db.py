import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import ejecutar_query
import pandas as pd

sql = """
SELECT 
    m.Modulo, t.Turno, v.Valvula, var.Nombre_Variedad,
    e.Nombre_Estado, 
    SUM(f.Cantidad_Organos) as Total_Organos,
    COUNT(DISTINCT f.Punto) as Puntos
FROM Silver.Fact_Conteo_Fenologico f
JOIN Silver.Dim_Estado_Fenologico e ON f.ID_Estado_Fenologico = e.ID_Estado_Fenologico
JOIN Silver.Dim_Geografia g ON f.ID_Geografia = g.ID_Geografia
JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
JOIN Silver.Dim_Variedad var ON f.ID_Variedad = var.ID_Variedad
JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
WHERE dt.Anio = 2025 AND dt.Semana_ISO = 24
  AND m.Modulo = '2' AND t.Turno = '1' AND v.Valvula = '1'
GROUP BY m.Modulo, t.Turno, v.Valvula, var.Nombre_Variedad, e.Nombre_Estado
"""

df = ejecutar_query(sql)
# Calcular organos por planta (asumiendo 10 plantas por punto)
df['Organos_Planta'] = df['Total_Organos'] / (df['Puntos'] * 10)
print(df[['Nombre_Estado', 'Organos_Planta']])
