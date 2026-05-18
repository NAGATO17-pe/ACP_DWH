import os
from sqlalchemy import text
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.abspath("."))

try:
    from utils.db import obtener_engine
    engine = obtener_engine()
    with engine.connect() as conn:
        query = """
        SELECT 
            t.name AS TableName,
            i.name AS IndexName,
            i.type_desc AS IndexType,
            STUFF((SELECT ', ' + c.name 
                   FROM sys.index_columns ic 
                   JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                   WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                   ORDER BY ic.key_ordinal
                   FOR XML PATH('')), 1, 2, '') AS Columns
        FROM sys.indexes i
        INNER JOIN sys.tables t ON i.object_id = t.object_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.name IN ('Fact_Conteo_Fenologico', 'Fact_Peladas', 'Fact_Evaluacion_Pesos', 'Dim_Geografia')
        ORDER BY t.name, i.index_id
        """
        res = conn.execute(text(query)).fetchall()
        df = pd.DataFrame(res)
        print(df.to_string())
except Exception as e:
    print(f"Error: {e}")
