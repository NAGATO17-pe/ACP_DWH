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

print("--- DETAILED SCHEMA CHECK: Silver.Dim_Geografia ---")
cursor.execute("""
    SELECT c.name
    FROM sys.columns c
    JOIN sys.objects o ON c.object_id = o.object_id
    JOIN sys.schemas s ON o.schema_id = s.schema_id
    WHERE s.name = 'Silver' AND o.name = 'Dim_Geografia'
""")
cols = [row[0] for row in cursor.fetchall()]
print(f"Columnas: {', '.join(cols)}")
