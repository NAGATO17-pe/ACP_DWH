import pyodbc

server   = "LCP-PAG-PRACTIC"
database = "ACP_DataWarehose_Proyecciones"
driver   = "ODBC Driver 18 for SQL Server"

conn = pyodbc.connect(
    f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes"
)
cursor = conn.cursor()

# Indices y PKs de marts existentes
print("=== INDICES Y PK DE GOLD MARTS EXISTENTES ===")
cursor.execute("""
    SELECT 
        s.name AS esquema,
        t.name AS tabla,
        i.name AS indice,
        i.type_desc,
        i.is_primary_key,
        i.is_unique,
        STUFF((
            SELECT ', ' + c.name + (CASE WHEN ic2.is_descending_key=1 THEN ' DESC' ELSE '' END)
            FROM sys.index_columns ic2
            JOIN sys.columns c ON c.object_id = ic2.object_id AND c.column_id = ic2.column_id
            WHERE ic2.object_id = i.object_id AND ic2.index_id = i.index_id AND ic2.is_included_column = 0
            ORDER BY ic2.key_ordinal
            FOR XML PATH('')
        ), 1, 2, '') AS columnas_clave
    FROM sys.indexes i
    JOIN sys.tables t ON t.object_id = i.object_id
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    WHERE s.name = 'Gold'
      AND i.index_id > 0
    ORDER BY t.name, i.index_id
""")
for r in cursor.fetchall():
    pk = " [PK]" if r[4] else ""
    uq = " [UNIQUE]" if r[5] and not r[4] else ""
    print(f"  [{r[0]}] {r[1]}.{r[2]}  {r[3]}{pk}{uq}  ({r[6]})")

# Ver si Mart_Cosecha y Mart_Proyecciones tienen ID_Mart_X autoincrement
print("\n=== IDENTITY (autoincrement) en marts ===")
cursor.execute("""
    SELECT s.name, t.name, c.name, c.is_identity, ic.seed_value, ic.increment_value
    FROM sys.tables t
    JOIN sys.schemas s ON s.schema_id = t.schema_id
    JOIN sys.columns c ON c.object_id = t.object_id
    LEFT JOIN sys.identity_columns ic ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    WHERE s.name = 'Gold' AND c.is_identity = 1
""")
for r in cursor.fetchall():
    print(f"  [{r[0]}] {r[1]}.{r[2]}  IDENTITY({r[4]},{r[5]})")

conn.close()
