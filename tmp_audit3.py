import pyodbc

server   = "LCP-PAG-PRACTIC"
database = "ACP_DataWarehose_Proyecciones"
driver   = "ODBC Driver 18 for SQL Server"

conn = pyodbc.connect(
    f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes"
)
cursor = conn.cursor()

# Marts con datos vs vacios
print("=== ESTADO GOLD MARTS (datos reales) ===")
marts = [
    "Gold.Mart_Administrativo",
    "Gold.Mart_Clima",
    "Gold.Mart_Cosecha",
    "Gold.Mart_Fenologia",
    "Gold.Mart_Pesos_Calibres",
    "Gold.Mart_Proyecciones",
]
for m in marts:
    cursor.execute(f"SELECT COUNT(*) FROM {m}")
    n = cursor.fetchone()[0]
    estado = "CON DATOS" if n > 0 else "VACIO"
    print(f"  {m}: {n} filas [{estado}]")

# Silver facts con datos
print("\n=== ESTADO SILVER FACTS (datos reales) ===")
facts = [
    "Silver.Fact_Ciclo_Poda",
    "Silver.Fact_Conteo_Fenologico",
    "Silver.Fact_Cosecha_SAP",
    "Silver.Fact_Evaluacion_Pesos",
    "Silver.Fact_Evaluacion_Vegetativa",
    "Silver.Fact_Fisiologia",
    "Silver.Fact_Induccion_Floral",
    "Silver.Fact_Maduracion",
    "Silver.Fact_Peladas",
    "Silver.Fact_Proyecciones",
    "Silver.Fact_Sanidad_Activo",
    "Silver.Fact_Tareo",
    "Silver.Fact_Tasa_Crecimiento_Brotes",
    "Silver.Fact_Telemetria_Clima",
]
for f in facts:
    cursor.execute(f"SELECT COUNT(*) FROM {f}")
    n = cursor.fetchone()[0]
    estado = "CON DATOS" if n > 0 else "VACIO"
    print(f"  {f}: {n} filas [{estado}]")

# Columnas que el codigo intenta insertar en mart_administrativo pero que NO existen (detectar desfase)
print("\n=== DESFASE: columnas codigo vs BD real ===")
# Mart_Administrativo - el codigo inserta: ID_Tiempo, ID_Personal, ID_Actividad, ID_Campana, Supervisor, Semana_ISO, Horas_Trabajadas_Total, Registros_Observados_SAP
code_cols = {
    "Gold.Mart_Administrativo": ["ID_Tiempo","ID_Personal","ID_Actividad","ID_Campana","Supervisor","Semana_ISO","Horas_Trabajadas_Total","Registros_Observados_SAP"],
    "Gold.Mart_Cosecha": ["ID_Tiempo","ID_Geografia","ID_Variedad","ID_Campana","Fundo","Modulo","Turno","Variedad","Fecha_Cosecha","Kg_Brutos","Kg_Neto_Real","Kg_Proyectados","Condicion"],
    "Gold.Mart_Proyecciones": ["ID_Tiempo","ID_Geografia","ID_Variedad","ID_Escenario","ID_Campana","Fundo","Modulo","Turno","Variedad","Fecha_Cutoff","Kg_Proyectados","MAPE","Version_Modelo","Flag_Override","Estado_Workflow"],
    "Gold.Mart_Fenologia": ["ID_Tiempo","ID_Geografia","ID_Variedad","ID_Campana","Fundo","Modulo","Variedad","Semana_ISO","Estado_Fenologico","Orden_Estado","Cantidad_Organos"],
    "Gold.Mart_Clima": ["ID_Tiempo","Sector_Climatico","ID_Campana","Semana_ISO","Temp_Max_Promedio","Temp_Min_Promedio","VPD_Promedio","Humedad_Promedio","Precipitacion_Total"],
    "Gold.Mart_Pesos_Calibres": ["ID_Tiempo","ID_Geografia","ID_Variedad","ID_Campana","Fundo","Modulo","Variedad","Semana_ISO","Peso_Promedio_Baya_g","Cant_Bayas_Muestra"],
}

for mart, cols_codigo in code_cols.items():
    schema, table = mart.split(".")
    cursor.execute(f"""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA=? AND TABLE_NAME=?
    """, schema, table)
    cols_bd = {r[0] for r in cursor.fetchall()}
    
    faltantes = [c for c in cols_codigo if c not in cols_bd]
    extras_bd = [c for c in cols_bd if c not in cols_codigo and not c.startswith("ID_Mart") and c not in ("Fecha_Actualizacion",)]
    
    if faltantes or extras_bd:
        print(f"\n  {mart}:")
        if faltantes:
            print(f"    CODIGO inserta pero NO existe en BD: {faltantes}")
        if extras_bd:
            print(f"    EXISTE en BD pero codigo NO rellena: {extras_bd}")
    else:
        print(f"\n  {mart}: OK (sin desfases detectados)")

conn.close()
