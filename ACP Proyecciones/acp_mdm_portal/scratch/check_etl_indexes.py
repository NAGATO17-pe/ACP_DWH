import os
import pyodbc
from dotenv import load_dotenv

load_dotenv("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/.env")

server = os.getenv("ACP_DB_SERVER")
database = os.getenv("ACP_DB_DATABASE")
driver = os.getenv("ACP_DB_DRIVER")

conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

tables = [
    'Silver.Fact_Conteo_Fenologico',
    'Silver.Fact_Peladas',
    'Silver.Fact_Evaluacion_Pesos',
    'Silver.Fact_Fisiologia',
    'Silver.Fact_Maduracion',
    'Silver.Fact_Cosecha_SAP'
]

print("--- INDEX CHECK FOR ETL/GOLD ---")
for table in tables:
    schema, name = table.split('.')
    print(f"\nTable: {table}")
    cursor.execute(f"""
        SELECT i.name, 
               STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal) as keys,
               STRING_AGG(CASE WHEN ic.is_included_column = 1 THEN c.name END, ', ') as included
        FROM sys.indexes i
        JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN sys.objects o ON i.object_id = o.object_id
        JOIN sys.schemas s ON o.schema_id = s.schema_id
        WHERE s.name = '{schema}' AND o.name = '{name}'
        GROUP BY i.name
    """)
    rows = cursor.fetchall()
    if not rows:
        print("  [WARNING] No indexes found (other than PK maybe).")
    for row in rows:
        print(f"  - {row[0]}: Keys({row[1]}) | Included({row[2]})")
