# =========================================
# CONFIGURACIÓN
# =========================================
import pandas as pd
import pyodbc
from datetime import datetime, timedelta

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=LCP-PAG-PRACTIC;"
    "DATABASE=ACP_DataWarehose_Proyecciones;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

# =========================================
# EXTRACCIÓN DE DATOS
# =========================================

def extraer_datos(id_tiempo):
    """
    Extrae datos filtrados por la semana especificada.
    """
    conn = pyodbc.connect(CONN_STR)
    params = (id_tiempo,)

    # 1. Maduración: traemos el detalle para aplicar la matriz fenológica
    df_maduracion = pd.read_sql("""
        SELECT 
            ID_Geografia AS modulo, 
            ID_Variedad AS variedad,
            ID_Estado_Fenologico AS id_estado
        FROM Silver.Fact_Maduracion
        WHERE ID_Tiempo = ?
    """, conn, params=params)

    # 2. Conteo/Fenología
    df_fenologia = pd.read_sql("""
        SELECT 
            ID_Geografia AS modulo, 
            ID_Variedad AS variedad,
            CAST(SUM(Cantidad_Organos) AS FLOAT) AS total_organos,
            CAST(COUNT(DISTINCT Punto) * 10 AS FLOAT) AS total_plantas -- Asunción de 10 plantas por punto
        FROM Silver.Fact_Conteo_Fenologico
        WHERE ID_Tiempo = ?
        GROUP BY ID_Geografia, ID_Variedad
    """, conn, params=params)

    # 3. Pesos (Kg/Ha estimado)
    df_pesos = pd.read_sql("""
        SELECT 
            ID_Geografia AS modulo, 
            ID_Variedad AS variedad,
            CAST(AVG(Peso_Promedio_Baya_g * 100) AS FLOAT) AS kg_ha, -- Simulación de kg_ha
            CAST(1.0 AS FLOAT) AS hectareas
        FROM Silver.Fact_Evaluacion_Pesos
        WHERE ID_Tiempo = ?
        GROUP BY ID_Geografia, ID_Variedad
    """, conn, params=params)

    # 4. Productividad (Peladas)
    df_productividad = pd.read_sql("""
        SELECT 
            ID_Geografia AS modulo, 
            ID_Variedad AS variedad,
            CAST(SUM(Plantas_Productivas) AS FLOAT) AS plantas_productivas,
            CAST(SUM(Plantas_Productivas + Plantas_No_Productivas) AS FLOAT) AS total_plantas
        FROM Silver.Fact_Peladas
        WHERE ID_Tiempo = ?
        GROUP BY ID_Geografia, ID_Variedad
    """, conn, params=params)

    # 5. Cosecha
    df_cosecha = pd.read_sql("""
        SELECT 
            ID_Geografia AS modulo, 
            ID_Variedad AS variedad,
            CAST(SUM(Kg_Neto_MP) AS FLOAT) AS kg_real
        FROM Silver.Fact_Cosecha_SAP
        WHERE ID_Tiempo = ?
        GROUP BY ID_Geografia, ID_Variedad
    """, conn, params=params)
    
    # Marcamos df_conteo como igual a fenologia para que el script no rompa
    df_conteo = df_fenologia.copy()

    conn.close()

    return df_fenologia, df_conteo, df_maduracion, df_pesos, df_productividad, df_cosecha


# =========================================
# CÁLCULOS BASE
# =========================================

def calcular_pct_maduracion(df):
    if df.empty: return pd.DataFrame(columns=["modulo", "variedad", "pct_maduracion"])
    
    # Calculamos agregados para el % promedio
    df["es_maduro"] = df["id_estado"].isin([8, 9]).astype(int)
    res = df.groupby(["modulo", "variedad"]).agg(
        frutos_maduros=("es_maduro", "sum"),
        frutos_totales=("es_maduro", "count")
    ).reset_index()
    
    res["pct_maduracion"] = res["frutos_maduros"] / res["frutos_totales"]
    return res[["modulo", "variedad", "pct_maduracion"]]


def calcular_organos_por_planta(df):
    df["organos_planta"] = df["total_organos"] / df["total_plantas"]
    return df[["modulo", "variedad", "organos_planta"]]


def calcular_kg_base(df_pesos, df_productividad):
    df = df_pesos.merge(df_productividad, on=["modulo", "variedad"])
    df["kg_base"] = df["kg_ha"] * df["hectareas"]
    return df[["modulo", "variedad", "kg_base"]]


def calcular_pct_plantas_productivas(df):
    # Lógica de resiliencia: si no hay datos o es 0, asumimos 1.0 (100% productivas)
    # para no anular la proyección por falta de datos en la fuente.
    df["pct_productivas"] = df["plantas_productivas"] / df["total_plantas"]
    df["pct_productivas"] = df["pct_productivas"].fillna(1.0).replace(0, 1.0)
    return df[["modulo", "variedad", "pct_productivas"]]


# =========================================
# PROYECCIÓN SEMANAL
# =========================================

def calcular_proyeccion(df_base, df_mad, df_prod):
    df = df_base.merge(df_mad, on=["modulo", "variedad"])
    df = df.merge(df_prod, on=["modulo", "variedad"])

    df["proyeccion"] = (
        df["kg_base"]
        * df["pct_maduracion"]
        * df["pct_productivas"]
    )

    return df


# =========================================
# AJUSTES Y MÁRGENES
# =========================================

def aplicar_margenes(df):
    df["pesimista"] = df["proyeccion"] * 0.9906
    df["optimista"] = df["proyeccion"] * 1.0107
    return df


# =========================================
# CONSOLIDACIÓN FINAL
# =========================================

def consolidar(df):
    return df.groupby("variedad")["proyeccion"].sum().reset_index()

def calcular_distribucion_fenologica(df_maduracion):
    """
    Calcula el conteo de bayas por cada estado fenológico por módulo/variedad.
    """
    # Agrupamos por modulo, variedad y estado
    df_counts = df_maduracion.groupby(["modulo", "variedad", "id_estado"]).size().reset_index(name="conteo")
    # Calculamos el total por modulo/variedad para sacar el % de cada estado
    df_total = df_maduracion.groupby(["modulo", "variedad"]).size().reset_index(name="total_bayas")
    
    df = df_counts.merge(df_total, on=["modulo", "variedad"])
    df["pct_estado"] = df["conteo"] / df["total_bayas"]
    
    return df


def guardar_resultados(df_proy_total, df_mad_det, conn, id_tiempo_base):
    """
    Aplica la matriz de distribución del Excel para las próximas 6 semanas.
    """
    if df_proy_total.empty:
        print(f"No hay resultados para procesar.")
        return

    # MATRIZ DE DISTRIBUCIÓN (Extraída del Excel)
    # Formato: { ID_Estado: [W+1, W+2, W+3, W+4, W+5, W+6] }
    matriz = {
        9: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0], # Cosechable
        8: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0], # Madura
        7: [1.0, 0.0, 0.0, 0.0, 0.0, 0.0], # Crema
        6: [0.24, 0.44, 0.32, 0.0, 0.0, 0.0], # Fase 2
        5: [0.0, 0.0, 0.17, 0.40, 0.43, 0.0], # Fase 1
        4: [0.0, 0.0, 0.0, 0.0, 0.16, 0.17], # Verde (Sigue en W7/W8)
        3: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], # Pequeña (Futuras semanas)
    }
    
    cursor = conn.cursor()
    cursor.execute("""
        IF OBJECT_ID('tempdb..#Temp_SixWek_Matrix') IS NOT NULL DROP TABLE #Temp_SixWek_Matrix;
        CREATE TABLE #Temp_SixWek_Matrix (
            ID_Tiempo INT, ID_Geografia INT, ID_Variedad INT, ID_Escenario INT,
            Kg_Proyectados DECIMAL(18,4), Pct_Maduracion DECIMAL(10,6), 
            ID_Campana INT, Fecha_Cutoff DATE, Version_Modelo NVARCHAR(50)
        )
    """)

    fecha_base = datetime.strptime(str(id_tiempo_base), "%Y%m%d")

    # Para cada combinación Módulo/Variedad
    for _, proy in df_proy_total.iterrows():
        mod, var = proy["modulo"], proy["variedad"]
        kg_potencial = proy["proyeccion"] # Kilos si todo madurara hoy
        
        # Obtenemos los estados para este módulo/variedad
        estados_filtro = df_mad_det[(df_mad_det["modulo"] == mod) & (df_mad_det["variedad"] == var)]
        
        if estados_filtro.empty: continue

        # Calculamos los kilos para cada una de las 6 semanas
        semanas_kilos = [0.0] * 6
        
        for _, st in estados_filtro.iterrows():
            id_estado = int(st["id_estado"])
            pct_en_estado = st["pct_estado"]
            
            if id_estado in matriz:
                coefs = matriz[id_estado]
                for i in range(6):
                    # Kilos de esta semana = Potencial * % de bayas en este estado * Coeficiente de la semana
                    semanas_kilos[i] += kg_potencial * pct_en_estado * coefs[i]

        # Insertar las 6 semanas
        for i, kg_sem in enumerate(semanas_kilos):
            if kg_sem <= 0: continue
            
            semana_num = i + 1
            fecha_proy = fecha_base + timedelta(weeks=semana_num)
            id_tiempo_proy = int(fecha_proy.strftime("%Y%m%d"))

            cursor.execute("""
                INSERT INTO #Temp_SixWek_Matrix 
                (ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario, Kg_Proyectados, ID_Campana, Fecha_Cutoff, Version_Modelo)
                VALUES (?, ?, ?, 4, ?, 3, ?, ?)
            """, id_tiempo_proy, int(mod), int(var), kg_sem, fecha_base.date(), f"SixWek-Matrix-W{semana_num}")

    # MERGE final
    cursor.execute("""
        MERGE Silver.Fact_Proyecciones AS dest
        USING #Temp_SixWek_Matrix AS src
        ON (src.ID_Tiempo = dest.ID_Tiempo AND src.ID_Geografia = dest.ID_Geografia AND src.ID_Variedad = dest.ID_Variedad AND src.ID_Escenario = dest.ID_Escenario)
        WHEN MATCHED THEN UPDATE SET
            dest.Kg_Proyectados = src.Kg_Proyectados,
            dest.Fecha_Sistema = GETDATE()
        WHEN NOT MATCHED THEN INSERT 
            (ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario, Kg_Proyectados, ID_Campana, Fecha_Cutoff, Fecha_Evento, Fecha_Sistema, Version_Modelo, ID_Estado_Workflow, Estado_DQ)
            VALUES (src.ID_Tiempo, src.ID_Geografia, src.ID_Variedad, src.ID_Escenario, src.Kg_Proyectados, src.ID_Campana, src.Fecha_Cutoff, src.Fecha_Cutoff, GETDATE(), src.Version_Modelo, 1, 'OK');
    """)
    conn.commit()
    print(f"ÉXITO: Proyección distribuida mediante MATRIZ FENOLÓGICA guardada.")


def ejecutar_pipeline(id_tiempo=20260503):
    # 1. Extraer
    df_fenologia, df_conteo, df_maduracion, df_pesos, df_productividad, df_cosecha = extraer_datos(id_tiempo)

    # 2. Calcular variables
    df_mad_det = calcular_distribucion_fenologica(df_maduracion) # Detalle por estado
    df_mad_avg = calcular_pct_maduracion(df_maduracion) # Promedio para el total
    df_base = calcular_kg_base(df_pesos, df_productividad)
    df_prod = calcular_pct_plantas_productivas(df_productividad)

    # 3. Proyección Potencial (Total)
    df_proy = calcular_proyeccion(df_base, df_mad_avg, df_prod)
    df_proy = aplicar_margenes(df_proy)

    # 4. Distribuir usando Matriz Fenológica
    conn = pyodbc.connect(CONN_STR)
    guardar_resultados(df_proy, df_mad_det, conn, id_tiempo)
    conn.close()

    return consolidar(df_proy)


# =========================================
# EJECUCIÓN
# =========================================

if __name__ == "__main__":
    FECHA_CORTE = 20260125
    resultado = ejecutar_pipeline(id_tiempo=FECHA_CORTE)
    print(f"\n--- Proyección Finalizada (Basada en Matriz del Excel) ---")
    print(resultado)