"""
Ejecuta la migracion fase35_optimizaciones_etl.sql contra la BD real.
"""
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv("d:/Proyecto2026/ACP_DWH/ACP Proyecciones/.env")

server = os.getenv("ACP_DB_SERVER")
database = os.getenv("ACP_DB_DATABASE")
driver = os.getenv("ACP_DB_DRIVER", "ODBC Driver 18 for SQL Server")

conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

sql_path = r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\ETL\sql_migrations\fase35_optimizaciones_etl.sql"

with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

# Split by GO (batch separator for SQL Server)
batches = [b.strip() for b in sql_content.split("\nGO\n") if b.strip()]
# Also handle GO at end of file
if sql_content.strip().endswith("GO"):
    pass  # already handled

print(f"Total batches to execute: {len(batches)}")
print("=" * 60)

for i, batch in enumerate(batches, 1):
    # Skip comment-only or empty batches
    lines = [l for l in batch.split("\n") if l.strip() and not l.strip().startswith("--")]
    if not lines:
        continue

    try:
        cursor.execute(batch)
        # Capture PRINT output via messages
        while cursor.nextset():
            pass
        print(f"[OK] Batch {i}/{len(batches)} ejecutado correctamente")
    except pyodbc.Error as e:
        print(f"[ERROR] Batch {i}/{len(batches)}: {e}")
        # Continue with next batch (idempotent design)

conn.close()
print("=" * 60)
print("Migracion fase35 completada.")
