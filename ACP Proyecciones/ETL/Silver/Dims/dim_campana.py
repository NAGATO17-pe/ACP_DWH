"""
ETL/silver/dims/dim_campana.py
=============================
Dimension de Campañas y Bridge de Modulo-Campaña.
Implementa las reglas de negocio para definicion de periodos agricolas.

Reglas:
1. Semana de Poda < 20 -> Año Campaña = Año de la Poda.
2. Semana de Poda >= 20 -> Año Campaña = Año de la Poda + 1.
3. Una campaña para un modulo inicia el dia de su poda y termina el dia anterior a la siguiente poda.
"""

import pandas as pd
from sqlalchemy import text, Engine
import logging

log = logging.getLogger("ETL_Pipeline")

TABLA_DIM_CAMPANA = "Silver.Dim_Campana"
TABLA_BRIDGE = "Silver.Bridge_Modulo_Campana"
TABLA_PODAS = "Silver.Fact_Ciclo_Poda"
TABLA_GEO = "Silver.Dim_Geografia"

def cargar_dim_campana(engine: Engine):
    """
    Sincroniza Dim_Campana y Bridge_Modulo_Campana basandose en las podas registradas.
    """
    with engine.connect() as conn:
        # 1. Leer todas las podas únicas por módulo y fecha
        # Usamos ID_Modulo_Catalogo de Dim_Geografia para agrupar por Modulo real
        df_podas = pd.read_sql(f"""
            SELECT 
                g.ID_Modulo_Catalogo,
                p.Fecha_Evento as Fecha_Poda,
                DATEPART(isowk, p.Fecha_Evento) as Semana_ISO
            FROM {TABLA_PODAS} p
            INNER JOIN {TABLA_GEO} g ON p.ID_Geografia = g.ID_Geografia
            WHERE p.Estado_DQ = 'OK'
            GROUP BY g.ID_Modulo_Catalogo, p.Fecha_Evento
            ORDER BY g.ID_Modulo_Catalogo, p.Fecha_Evento ASC
        """, conn)

        if df_podas.empty:
            log.warning("No hay podas para procesar campañas.")
            return {"status": "SKIP", "mensaje": "No hay podas"}

        # 2. Calcular Año de Campaña (Cosecha)
        # Regla: < 20 -> Actual, >= 20 -> Siguiente
        df_podas['Anio_Cosecha'] = df_podas.apply(
            lambda x: x['Fecha_Poda'].year if x['Semana_ISO'] < 20 else x['Fecha_Poda'].year + 1,
            axis=1
        )

        # 3. Asegurar que los registros de Dim_Campana existan
        anios_necesarios = df_podas['Anio_Cosecha'].unique()
        for anio in anios_necesarios:
            conn.execute(text(f"""
                IF NOT EXISTS (SELECT 1 FROM {TABLA_DIM_CAMPANA} WHERE Anio_Cosecha = :anio)
                BEGIN
                    INSERT INTO {TABLA_DIM_CAMPANA} (Anio_Cosecha, Nombre_Campana, Estado, Es_Activa, Fecha_Creacion)
                    VALUES (:anio, :nombre, 'ACTIVO', 1, GETDATE())
                END
            """), {"anio": int(anio), "nombre": f"Campaña {anio}"})
        
        # 4. Construir los intervalos (Bridge)
        # Para cada modulo, la campaña termina donde empieza la siguiente
        df_intervals = []
        for modulo_id, group in df_podas.groupby('ID_Modulo_Catalogo'):
            group = group.sort_values('Fecha_Poda')
            for i in range(len(group)):
                row = group.iloc[i]
                fecha_inicio = row['Fecha_Poda']
                anio_cosecha = row['Anio_Cosecha']
                
                # Fecha fin es el dia anterior a la siguiente poda
                fecha_fin = None
                if i + 1 < len(group):
                    fecha_fin = group.iloc[i+1]['Fecha_Poda'] - pd.Timedelta(days=1)
                else:
                    # Si es la ultima poda, termina en el futuro lejano o queda abierto
                    fecha_fin = pd.Timestamp('2099-12-31')
                
                df_intervals.append({
                    'ID_Modulo_Catalogo': modulo_id,
                    'Anio_Cosecha': anio_cosecha,
                    'Fecha_Inicio': fecha_inicio,
                    'Fecha_Fin': fecha_fin
                })

        df_bridge = pd.DataFrame(df_intervals)

        # 5. Mapear ID_Campana
        dim_campana = pd.read_sql(f"SELECT ID_Campana, Anio_Cosecha FROM {TABLA_DIM_CAMPANA}", conn)
        df_bridge = df_bridge.merge(dim_campana, on='Anio_Cosecha')

        # 6. Upsert en Bridge_Modulo_Campana
        # Limpiamos y recargamos (o hacemos merge mas sofisticado)
        # Dado que las podas definen la estructura, una recarga total del bridge es segura si se basa en Fact_Ciclo_Poda
        with engine.begin() as trans:
            trans.execute(text(f"DELETE FROM {TABLA_BRIDGE}"))
            for _, row in df_bridge.iterrows():
                trans.execute(text(f"""
                    INSERT INTO {TABLA_BRIDGE} 
                    (ID_Modulo_Catalogo, ID_Campana, Fecha_Inicio, Fecha_Fin, Es_Activa, Fecha_Creacion)
                    VALUES (:mod, :camp, :ini, :fin, 1, GETDATE())
                """), {
                    "mod": int(row['ID_Modulo_Catalogo']),
                    "camp": int(row['ID_Campana']),
                    "ini": row['Fecha_Inicio'],
                    "fin": row['Fecha_Fin']
                })

        return {
            "status": "OK", 
            "campañas_creadas": len(anios_necesarios),
            "intervalos_bridge": len(df_bridge)
        }

if __name__ == "__main__":
    from nucleo.conexion import obtener_engine
    engine = obtener_engine()
    res = cargar_dim_campana(engine)
    print(res)
