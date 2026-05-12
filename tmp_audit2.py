import pyodbc

server   = "LCP-PAG-PRACTIC"
database = "ACP_DataWarehose_Proyecciones"
driver   = "ODBC Driver 18 for SQL Server"

conn = pyodbc.connect(
    f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes"
)
cursor = conn.cursor()

# Columnas de todas las Silver.Fact_* y Gold.Mart_*
cursor.execute("""
    SELECT
        c.TABLE_SCHEMA,
        c.TABLE_NAME,
        c.COLUMN_NAME,
        c.DATA_TYPE,
        c.IS_NULLABLE,
        c.CHARACTER_MAXIMUM_LENGTH,
        c.NUMERIC_PRECISION,
        c.NUMERIC_SCALE
    FROM INFORMATION_SCHEMA.COLUMNS c
    WHERE (c.TABLE_SCHEMA = 'Silver' AND c.TABLE_NAME LIKE 'Fact_%')
       OR (c.TABLE_SCHEMA = 'Gold'   AND c.TABLE_NAME LIKE 'Mart_%')
    ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
""")
rows = cursor.fetchall()

current = None
for r in rows:
    key = f"[{r[0]}] {r[1]}"
    if key != current:
        print(f"\n=== {key} ===")
        current = key
    nullable = "NULL" if r[4] == "YES" else "NOT NULL"
    size = ""
    if r[5]: size = f"({r[5]})"
    elif r[6] and r[7] is not None: size = f"({r[6]},{r[7]})"
    elif r[6]: size = f"({r[6]})"
    print(f"  {r[2]}  {r[3]}{size}  {nullable}")

conn.close()
