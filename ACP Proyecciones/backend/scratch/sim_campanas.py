import sys
sys.path.insert(0, r"d:\Proyecto2026\ACP_DWH\ACP Proyecciones\backend")
from nucleo.conexion import obtener_engine
import pandas as pd
from sqlalchemy import text

engine = obtener_engine()
with engine.connect() as conn:
    # 1. Obtener Podas con su Geografia (Modulo + Variedad)
    sql = """
    SELECT 
        g.ID_Modulo_Catalogo,
        p.ID_Variedad,
        p.Fecha_Evento as Fecha_Inicio,
        DATEPART(isowk, p.Fecha_Evento) as Semana_ISO,
        CASE 
            WHEN DATEPART(isowk, p.Fecha_Evento) <= 20 THEN YEAR(p.Fecha_Evento)
            ELSE YEAR(p.Fecha_Evento) + 1
        END as Anio_Campana
    FROM Silver.Fact_Ciclo_Poda p
    INNER JOIN Silver.Dim_Geografia g ON p.ID_Geografia = g.ID_Geografia
    WHERE p.Estado_DQ = 'OK'
    ORDER BY g.ID_Modulo_Catalogo, p.ID_Variedad, p.Fecha_Evento ASC
    """
    df_podas = pd.read_sql(text(sql), conn)
    
    if df_podas.empty:
        print('No hay podas para simular.')
        sys.exit()

    # 2. Refinar logic: Agrupar por Modulo + Variedad + Año Campaña
    # Tomamos la primera poda de esa campaña como el inicio.
    df_bridge = df_podas.groupby(['ID_Modulo_Catalogo', 'ID_Variedad', 'Anio_Campana']).agg(
        Fecha_Inicio=('Fecha_Inicio', 'min')
    ).reset_index()
    
    # Ordenar para calcular el fin
    df_bridge = df_bridge.sort_values(['ID_Modulo_Catalogo', 'ID_Variedad', 'Fecha_Inicio'])
    
    # La fecha fin es el dia anterior a la primera poda de la SIGUIENTE campaña
    df_bridge['Fecha_Fin'] = df_bridge.groupby(['ID_Modulo_Catalogo', 'ID_Variedad'])['Fecha_Inicio'].shift(-1)
    df_bridge['Fecha_Fin'] = pd.to_datetime(df_bridge['Fecha_Fin']) - pd.Timedelta(days=1)
    df_bridge['Fecha_Fin'] = df_bridge['Fecha_Fin'].fillna(pd.Timestamp('2099-12-31'))
    
    print('\n=== SIMULACION DE BRIDGE REFINADA (AGRUPADA POR TEMPORADA) ===')
    print(df_bridge.to_string())
    
    # 3. Verificar impacto
    print('\n=== ANALISIS DE COBERTURA ===')
    print(f"Total periodos de campaña únicos: {len(df_bridge)}")
    print(f"Modulos únicos: {df_bridge['ID_Modulo_Catalogo'].nunique()}")
