import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine
from sqlalchemy import text

engine = obtener_engine()

sql_sp = """
CREATE OR ALTER PROCEDURE Silver.sp_Sincronizar_Periodos_Campana
AS
BEGIN
    SET NOCOUNT ON;
    SET DATEFIRST 1; -- Asegurar Lunes como primer dia de la semana (ISO)

    -- 1. Crear Campañas faltantes en Dim_Campana
    INSERT INTO Silver.Dim_Campana (Anio_Cosecha, Nombre_Campana, Estado, Es_Activa, Fecha_Creacion)
    SELECT DISTINCT 
        Calculo.Anio_Cosecha,
        'Campaña ' + CAST(Calculo.Anio_Cosecha AS VARCHAR),
        'ACTIVO', 
        1, 
        GETDATE()
    FROM (
        SELECT 
            CASE 
                WHEN DATEPART(isowk, Fecha_Evento) <= 20 THEN YEAR(Fecha_Evento)
                ELSE YEAR(Fecha_Evento) + 1
            END as Anio_Cosecha
        FROM Silver.Fact_Ciclo_Poda
        WHERE Estado_DQ = 'OK'
    ) Calculo
    WHERE NOT EXISTS (
        SELECT 1 FROM Silver.Dim_Campana c WHERE c.Anio_Cosecha = Calculo.Anio_Cosecha
    );

    -- 2. Procesar Podas para generar el Bridge
    -- Usamos una tabla temporal para agrupar y calcular intervalos
    IF OBJECT_ID('tempdb..#TmpPodas') IS NOT NULL DROP TABLE #TmpPodas;
    
    SELECT 
        g.ID_Modulo_Catalogo,
        p.ID_Variedad,
        CASE 
            WHEN DATEPART(isowk, p.Fecha_Evento) <= 20 THEN YEAR(p.Fecha_Evento)
            ELSE YEAR(p.Fecha_Evento) + 1
        END as Anio_Cosecha,
        MIN(p.Fecha_Evento) as Fecha_Inicio,
        MIN(DATEPART(isowk, p.Fecha_Evento)) as Semana_Poda_ISO,
        MIN(YEAR(p.Fecha_Evento)) as Anio_Poda_ISO -- Simplificado, podria ser ISODATE si fuera critico
    INTO #TmpPodas
    FROM Silver.Fact_Ciclo_Poda p
    INNER JOIN Silver.Dim_Geografia g ON p.ID_Geografia = g.ID_Geografia
    WHERE p.Estado_DQ = 'OK'
    GROUP BY g.ID_Modulo_Catalogo, p.ID_Variedad, 
             CASE WHEN DATEPART(isowk, p.Fecha_Evento) <= 20 THEN YEAR(p.Fecha_Evento) ELSE YEAR(p.Fecha_Evento) + 1 END;

    -- 3. Calcular Fecha_Fin (Dia antes de la siguiente poda del mismo Modulo+Variedad)
    IF OBJECT_ID('tempdb..#TmpBridge') IS NOT NULL DROP TABLE #TmpBridge;
    
    SELECT 
        t.ID_Modulo_Catalogo,
        t.ID_Variedad,
        c.ID_Campana,
        t.Fecha_Inicio,
        ISNULL(
            DATEADD(DAY, -1, LEAD(t.Fecha_Inicio) OVER (PARTITION BY t.ID_Modulo_Catalogo, t.ID_Variedad ORDER BY t.Fecha_Inicio)),
            '2099-12-31'
        ) as Fecha_Fin,
        t.Semana_Poda_ISO,
        t.Anio_Poda_ISO
    INTO #TmpBridge
    FROM #TmpPodas t
    INNER JOIN Silver.Dim_Campana c ON t.Anio_Cosecha = c.Anio_Cosecha;

    -- 4. Actualizar Bridge_Modulo_Campana (Truncate & Reload es seguro aqui porque se deriva de Fact_Ciclo_Poda)
    TRUNCATE TABLE Silver.Bridge_Modulo_Campana;
    
    INSERT INTO Silver.Bridge_Modulo_Campana 
    (ID_Modulo_Catalogo, ID_Variedad, ID_Campana, Tipo_Campana, Fecha_Inicio, Fecha_Fin, Es_Activa, Fecha_Creacion, Semana_Poda_ISO, Anio_Poda_ISO)
    SELECT 
        ID_Modulo_Catalogo, ID_Variedad, ID_Campana, 'COMERCIAL', Fecha_Inicio, Fecha_Fin, 1, GETDATE(), Semana_Poda_ISO, Anio_Poda_ISO
    FROM #TmpBridge;

    PRINT 'Bridge de Campañas sincronizado exitosamente.';
END;
"""

with engine.begin() as conn:
    print("Creando Stored Procedure Silver.sp_Sincronizar_Periodos_Campana...")
    conn.execute(text(sql_sp))
    print("SP creado con éxito.")
