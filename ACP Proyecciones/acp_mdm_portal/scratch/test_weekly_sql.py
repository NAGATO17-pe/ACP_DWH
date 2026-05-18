import sys
import os
sys.path.append(os.getcwd())
from utils.db import ejecutar_query

def test_sql():
    sql = """
        SELECT 
            MAX(dt.ID_Tiempo) as ID_Tiempo,
            dt.Anio,
            dt.Semana_ISO
        FROM (
            SELECT ID_Tiempo FROM Silver.Fact_Conteo_Fenologico WITH (NOLOCK)
            UNION
            SELECT ID_Tiempo FROM Silver.Fact_Peladas WITH (NOLOCK)
            UNION
            SELECT ID_Tiempo FROM Silver.Fact_Evaluacion_Pesos WITH (NOLOCK)
        ) f
        JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
        GROUP BY dt.Anio, dt.Semana_ISO
        ORDER BY ID_Tiempo DESC
    """
    df = ejecutar_query(sql)
    print(df.head(10))

if __name__ == "__main__":
    test_sql()
