import pyodbc

server   = "LCP-PAG-PRACTIC"
database = "ACP_DataWarehose_Proyecciones"
driver   = "ODBC Driver 18 for SQL Server"

conn = pyodbc.connect(
    f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes"
)
cursor = conn.cursor()

cursor.execute("""
    SELECT
        s.name   AS esquema,
        t.name   AS tabla,
        SUM(p.rows) AS filas
    FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)
    GROUP BY s.name, t.name
    ORDER BY s.name, t.name
""")
rows = cursor.fetchall()
print("=== TABLAS ===")
for r in rows:
    print(f"[{r[0]}] {r[1]}  |  {r[2]} filas")

conn.close()
