import urllib
import os
import re
from sqlalchemy import create_engine, text
import pandas as pd

def audit_database():
    s='LCP-PAG-PRACTIC'
    b='ACP_DataWarehose_Proyecciones'
    d='ODBC Driver 17 for SQL Server'
    c=f'DRIVER={{{d}}};SERVER={s};DATABASE={b};Trusted_Connection=yes;TrustServerCertificate=yes;'
    u='mssql+pyodbc:///?odbc_connect='+urllib.parse.quote_plus(c)
    
    engine = create_engine(u)
    with engine.connect() as conn:
        # 1. Obtener todas las tablas
        print("Obteniendo tablas de la base de datos...")
        query_tablas = """
            SELECT TABLE_SCHEMA + '.' + TABLE_NAME as FullTableName
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """
        db_tables = [r[0] for r in conn.execute(text(query_tablas)).fetchall()]
        print(f"Total tablas en DB: {len(db_tables)}")
        
        # 2. Analizar índices sin uso (nunca leídos)
        print("\nBuscando índices que nunca han sido utilizados para lectura...")
        query_indexes = """
            SELECT 
                OBJECT_SCHEMA_NAME(i.object_id) + '.' + OBJECT_NAME(i.object_id) AS TableName,
                i.name AS IndexName,
                user_seeks, user_scans, user_lookups, user_updates
            FROM sys.indexes i
            LEFT JOIN sys.dm_db_index_usage_stats s 
                ON i.object_id = s.object_id AND i.index_id = s.index_id AND s.database_id = DB_ID()
            WHERE OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
              AND i.type > 0 -- Ignorar Heaps
              AND i.is_primary_key = 0 -- Ignorar PKs
              AND i.is_unique_constraint = 0 -- Ignorar UQs
              AND (s.user_seeks = 0 AND s.user_scans = 0 AND s.user_lookups = 0 OR s.object_id IS NULL)
              -- Solo índices que sí se actualizan pero nunca se leen
              AND s.user_updates > 0
            ORDER BY s.user_updates DESC
        """
        df_unused_idx = pd.read_sql(text(query_indexes), conn)
        df_unused_idx.to_csv("unused_indexes.csv", index=False)
        print(f"Índices potencialmente sin uso (con actualizaciones): {len(df_unused_idx)}")
        
        return db_tables

def find_tables_in_code(db_tables):
    print("\nBuscando referencias a tablas en el código ETL...")
    etl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ACP Proyecciones', 'ETL')
    
    # Expresión regular para encontrar nombres de tablas (muy básica, asume Esquema.Nombre)
    table_pattern = re.compile(r'(Bronce\.[a-zA-Z0-9_]+|Silver\.[a-zA-Z0-9_]+|Gold\.[a-zA-Z0-9_]+|MDM\.[a-zA-Z0-9_]+|Auditoria\.[a-zA-Z0-9_]+)')
    
    referenced_tables = set()
    
    for root, _, files in os.walk(etl_dir):
        for file in files:
            if file.endswith('.py') or file.endswith('.sql'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = table_pattern.findall(content)
                        referenced_tables.update(matches)
                except Exception as e:
                    pass
    
    # Comparar
    db_tables_set = set(db_tables)
    
    orphan_tables = db_tables_set - referenced_tables
    print(f"\nTablas encontradas en DB pero NO mencionadas en el código ({len(orphan_tables)}):")
    for t in sorted(orphan_tables):
        print(f"- {t}")

    # Escribir reporte
    with open("orphan_tables.txt", "w") as f:
        f.write("\n".join(sorted(orphan_tables)))

if __name__ == "__main__":
    tables = audit_database()
    find_tables_in_code(tables)
