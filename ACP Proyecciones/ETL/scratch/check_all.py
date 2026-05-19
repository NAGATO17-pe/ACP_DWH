import sys
sys.path.append(r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL")
from config.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()

with engine.connect() as conn:
    print("--- SCHEMAS AND TABLES ---")
    res = conn.execute(text("SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_SCHEMA, TABLE_NAME")).fetchall()
    for row in res:
        print(f"{row[0]}.{row[1]}")
        
    print("\n--- FOREIGN KEYS ---")
    fk_query = """
        SELECT 
            SCHEMA_NAME(fk.schema_id) AS TABLE_SCHEMA,
            OBJECT_NAME(fk.parent_object_id) AS TABLE_NAME,
            c1.name AS COLUMN_NAME,
            SCHEMA_NAME(t.schema_id) AS REF_SCHEMA,
            OBJECT_NAME(fk.referenced_object_id) AS REF_TABLE,
            c2.name AS REF_COLUMN
        FROM sys.foreign_keys fk
        INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        INNER JOIN sys.columns c1 ON fkc.parent_object_id = c1.object_id AND fkc.parent_column_id = c1.column_id
        INNER JOIN sys.columns c2 ON fkc.referenced_object_id = c2.object_id AND fkc.referenced_column_id = c2.column_id
        INNER JOIN sys.tables t ON fk.referenced_object_id = t.object_id
    """
    fks = conn.execute(text(fk_query)).fetchall()
    for fk in fks:
        print(f"FK: {fk[0]}.{fk[1]}.{fk[2]} -> {fk[3]}.{fk[4]}.{fk[5]}")
    if not fks:
        print("No foreign keys found in the entire database!")
