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

print("--- SCHEMA CHECK: Silver.Dim_Geografia ---")
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Dim_Geografia'")
cols = [row[0] for row in cursor.fetchall()]
print(f"Columnas: {', '.join(cols)}")

cursor.execute("SELECT TOP 5 * FROM Silver.Dim_Geografia")
print("\nFirst 5 rows (sample):")
for row in cursor.fetchall():
    print(row)
