import pyodbc
import os
from dotenv import load_dotenv

load_dotenv(r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend\.env")

server = os.getenv('DB_SERVIDOR', 'LCP-PAG-PRACTIC')
database = os.getenv('DB_NOMBRE', 'ACP_DataWarehose_Proyecciones')
driver = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')

print(f"Probando conexión a {server} / {database}")

options = [
    f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;",
    f"DRIVER={driver};SERVER=localhost;DATABASE={database};Trusted_Connection=yes;",
    f"DRIVER={driver};SERVER=(local);DATABASE={database};Trusted_Connection=yes;",
    f"DRIVER={driver};SERVER=tcp:{server};DATABASE={database};Trusted_Connection=yes;",
    f"DRIVER={driver};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
]

for i, conn_str in enumerate(options):
    print(f"\n--- Intento {i+1} ---")
    print(f"ConnectionString: {conn_str}")
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        print("¡CONEXIÓN EXITOSA!")
        conn.close()
        # No break, let's see which ones work
    except Exception as e:
        print(f"FALLÓ: {type(e).__name__}: {e}")
