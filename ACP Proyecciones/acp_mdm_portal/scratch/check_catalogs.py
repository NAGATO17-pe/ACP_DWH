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

print("--- CATALOG TABLES CHECK ---")
cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME LIKE 'Dim_%_Catalogo'")
for row in cursor.fetchall():
    print(row[0])
