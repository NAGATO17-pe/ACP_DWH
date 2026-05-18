import os
from sqlalchemy import text
import pandas as pd
from dotenv import load_dotenv

# Path to the .env file might be in a different directory
load_dotenv()

# We need to add the parent directory to sys.path to import utils
import sys
sys.path.append(os.path.abspath("."))

try:
    from utils.db import obtener_engine
    engine = obtener_engine()
    with engine.connect() as conn:
        query = """
        SELECT 
            s.name AS SchemaName, 
            t.name AS TableName, 
            p.rows AS RowCounts
        FROM sys.tables t
        INNER JOIN sys.indexes i ON t.object_id = i.object_id
        INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.is_ms_shipped = 0 AND i.index_id < 2
        ORDER BY p.rows DESC
        """
        res = conn.execute(text(query)).fetchall()
        df = pd.DataFrame(res)
        print(df.to_string())
except Exception as e:
    print(f"Error: {e}")
