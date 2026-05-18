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

print("--- OBJECT TYPE CHECK ---")
cursor.execute("SELECT TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'Silver' AND TABLE_NAME = 'Dim_Geografia'")
res = cursor.fetchone()
print(f"Silver.Dim_Geografia es: {res[0] if res else 'NO ENCONTRADO'}")

# Si es una tabla, busquemos si hay una vista con nombre similar o si el repo_catalogos.py tiene joins
print("\n--- REPO_CATALOGOS SQL CHECK ---")
with open("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/backend/repositorios/repo_catalogos.py", "r", encoding="utf-8") as f:
    content = f.read()
    if "JOIN" in content:
        print("El archivo TIENE joins.")
    else:
        print("El archivo NO tiene joins en el bloque de geografia.")
