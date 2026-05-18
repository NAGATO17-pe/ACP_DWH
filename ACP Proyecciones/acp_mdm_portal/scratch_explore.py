import sys
import os
import json

from utils.db import ejecutar_query

def explore():
    query = """
    SELECT TABLE_SCHEMA, TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_TYPE = 'BASE TABLE'
    ORDER BY TABLE_SCHEMA, TABLE_NAME
    """
    df_tables = ejecutar_query(query)
    
    tables = df_tables['TABLE_NAME'].tolist()
    
    # Check for anything containing 'cosecha', 'recepcion', 'actual', 'real'
    target_tables = [t for t in tables if any(x in t.lower() for x in ['cosecha', 'recepcion', 'actual', 'real', 'fact'])]
    
    res = {
        'all_tables': tables,
        'target_tables': target_tables
    }
    
    with open('C:/Users/chernandez/.gemini/antigravity/brain/e4cc7ae7-763e-4965-a9b7-e3d8891de95e/scratch/db_tables.json', 'w') as f:
        json.dump(res, f, indent=2)

if __name__ == '__main__':
    explore()
