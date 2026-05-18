"""
marts.py
========
Refresca todos los Marts Gold desde Silver.
Operacion: TRUNCATE + INSERT, siempre desde cero.
Power BI solo conecta a estos Marts.

FIX: Gold no se publica si alguna fact critica fallo en el pipeline.
     refrescar_todos_los_marts() recibe el resumen del ETL y aborta
     si hay errores en las facts bloqueantes.
"""

import logging

from sqlalchemy.engine import Engine
from sqlalchemy import text

_log = logging.getLogger("ETL_Pipeline")

from config.parametros import obtener_int as obtener_param_int

# Escenario "Base" de proyecciones: es el escenario oficial de producción.
def _obtener_escenario_base() -> int:
    return obtener_param_int('ESCENARIO_PROYECCION_OFICIAL', 4)

MARTS = [
    'Gold.Mart_Cosecha',
    'Gold.Mart_Proyecciones',
    'Gold.Mart_Fenologia',
    'Gold.Mart_Clima',
    'Gold.Mart_Pesos_Calibres',
    'Gold.Mart_Administrativo',
    'Gold.Mart_Fisiologia',
    'Gold.Mart_Evaluacion_Vegetativa',
    'Gold.Mart_Maduracion',
    'Gold.Mart_Tasa_Crecimiento',
    'Gold.Mart_Induccion_Floral',
    'Gold.Mart_Ciclo_Poda',
    'Gold.Mart_Peladas',
]

# Fallback local — se usa solo si el pipeline no pasa facts_bloqueantes desde DB.
# Fuente de verdad: Config.Parametros_Pipeline / FACTS_BLOQUEANTES_GOLD (pipeline.py).
_FACTS_BLOQUEANTES_FALLBACK: frozenset[str] = frozenset({
    'Fact_Cosecha_SAP',
    'Fact_Conteo_Fenologico',
    'Fact_Evaluacion_Pesos',
    'Fact_Telemetria_Clima',
    'Fact_Fisiologia',
    'Fact_Maduracion',
    'Fact_Peladas',
    'Fact_Induccion_Floral',
    'Fact_Tasa_Crecimiento_Brotes',
    'Fact_Ciclo_Poda',
})


def _hay_fallas_criticas(
    resumen_etl: dict,
    facts_bloqueantes: frozenset[str] | set[str] | None = None,
) -> list[str]:
    """
    Detecta facts bloqueantes que terminaron en ERROR.
    Retorna lista de nombres con error (vacia = todo OK).
    Usa facts_bloqueantes del pipeline si se provee; si no, el fallback local.
    """
    conjunto = facts_bloqueantes if facts_bloqueantes is not None else _FACTS_BLOQUEANTES_FALLBACK
    return [nombre for nombre in conjunto if f'{nombre} ERROR' in resumen_etl]


def _truncar(conexion, mart: str) -> None:
    conexion.execute(text(f'TRUNCATE TABLE {mart}'))


def refrescar_mart_cosecha(conexion) -> int:
    conexion.execute(text(f"""
        INSERT INTO Gold.Mart_Cosecha (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Turno, Variedad, Fecha_Cosecha,
            Kg_Brutos, Kg_Neto_Real, Kg_Neto_MP,
            Kg_Proyectados, Kg_Proyectado,
            Cantidad_Jabas,
            Condicion, Fecha_Evento, Fecha_Actualizacion, Semana_ISO
        )
        SELECT
            cs.ID_Tiempo,
            cs.ID_Geografia,
            cs.ID_Variedad,
            ISNULL(cs.ID_Campana, 0),
            fc.Fundo,
            mc.Modulo,
            tc.Turno,
            v.Nombre_Variedad,
            CAST(cs.Fecha_Evento AS DATE),
            cs.Kg_Brutos,
            cs.Kg_Neto_MP, -- Kg_Neto_Real
            cs.Kg_Neto_MP, -- Kg_Neto_MP
            p.Kg_Proyectados,
            cs.Cantidad_Jabas,
            c.Sustrato,
            CAST(cs.Fecha_Evento AS NVARCHAR),
            SYSDATETIME(),
            t.Semana_ISO
        FROM Silver.Fact_Cosecha_SAP cs
        JOIN Silver.Dim_Tiempo             t  ON t.ID_Tiempo = cs.ID_Tiempo
        JOIN Silver.Dim_Geografia          g  ON g.ID_Geografia = cs.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo tc ON tc.ID_Turno_Catalogo = g.ID_Turno_Catalogo
        JOIN Silver.Dim_Variedad           v  ON v.ID_Variedad = cs.ID_Variedad
        JOIN Silver.Dim_Condicion_Cultivo  c  ON c.ID_Condicion = cs.ID_Condicion_Cultivo
        LEFT JOIN Silver.Fact_Proyecciones p
            ON  p.ID_Tiempo = cs.ID_Tiempo
            AND p.ID_Variedad = cs.ID_Variedad
            AND p.ID_Geografia = cs.ID_Geografia
            AND p.ID_Escenario = :id_escenario
    """), {"id_escenario": _obtener_escenario_base()})
    return _contar(conexion, 'Gold.Mart_Cosecha')


def refrescar_mart_proyecciones(conexion) -> int:
    conexion.execute(text(f"""
        INSERT INTO Gold.Mart_Proyecciones (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario, ID_Campana,
            Fundo, Modulo, Turno, Variedad, Fecha_Cutoff,
            Kg_Proyectados, MAPE, Error_MAPE, Version_Modelo,
            Flag_Override, Motivo_Override, Estado_Workflow,
            Semana_Objetivo, Version_Escenario, Fecha_Generacion,
            Kg_Real, Fecha_Actualizacion
        )
        SELECT
            p.ID_Tiempo,
            p.ID_Geografia,
            p.ID_Variedad,
            p.ID_Escenario,
            ISNULL(p.ID_Campana, 0),
            fc.Fundo,
            mc.Modulo,
            tc.Turno,
            v.Nombre_Variedad,
            p.Fecha_Cutoff,
            p.Kg_Proyectados,
            p.MAPE,
            p.Version_Modelo,
            p.Flag_Override,
            p.Motivo_Override,
            w.Estado,
            t.Semana_ISO,
            e.Tipo_Escenario,
            CAST(p.Fecha_Sistema AS DATE),
            real.Kg_Real,
            SYSDATETIME()
        FROM Silver.Fact_Proyecciones p
        JOIN Silver.Dim_Tiempo                t  ON t.ID_Tiempo = p.ID_Tiempo
        JOIN Silver.Dim_Geografia             g  ON g.ID_Geografia = p.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo   fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo  mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        LEFT JOIN Silver.Dim_Turno_Catalogo   tc ON tc.ID_Turno_Catalogo = g.ID_Turno_Catalogo
        JOIN Silver.Dim_Variedad              v  ON v.ID_Variedad = p.ID_Variedad
        JOIN Silver.Dim_Escenario_Proyeccion  e  ON e.ID_Escenario = p.ID_Escenario
        JOIN Silver.Dim_Estado_Workflow       w  ON w.ID_Workflow = p.ID_Estado_Workflow
        LEFT JOIN (
            SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Kg_Neto_MP) AS Kg_Real
            FROM Silver.Fact_Cosecha_SAP
            GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
        ) real ON real.ID_Tiempo = p.ID_Tiempo
               AND real.ID_Geografia = p.ID_Geografia
               AND real.ID_Variedad = p.ID_Variedad
    """))
    return _contar(conexion, 'Gold.Mart_Proyecciones')


def refrescar_mart_fenologia(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Fenologia (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Estado_Fenologico, Orden_Estado,
            Cantidad_Organos, Color_Cinta,
            Brotes_Productivos, Brotes_Vegetativos,
            Cantidad_Bayas,
            Fecha_Actualizacion
        )
        SELECT
            cf.ID_Tiempo,
            cf.ID_Geografia,
            cf.ID_Variedad,
            ISNULL(cf.ID_Campana, 0),
            fc.Fundo,
            mc.Modulo,
            v.Nombre_Variedad,
            t.Semana_ISO,
            ef.Nombre_Estado,
            ef.Orden_Estado,
            SUM(cf.Cantidad_Organos),
            MAX(mad.Color_Cinta),
            MAX(fis.Brotes_Productivos),
            MAX(fis.Brotes_Vegetativos),
            MAX(pes.Cantidad_Bayas),
            SYSDATETIME()
        FROM Silver.Fact_Conteo_Fenologico cf
        JOIN Silver.Dim_Tiempo            t  ON t.ID_Tiempo = cf.ID_Tiempo
        JOIN Silver.Dim_Geografia         g  ON g.ID_Geografia = cf.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad          v  ON v.ID_Variedad = cf.ID_Variedad
        JOIN Silver.Dim_Estado_Fenologico ef ON ef.ID_Estado_Fenologico = cf.ID_Estado_Fenologico
        LEFT JOIN (
            SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Brotes_Productivos) as Brotes_Productivos, SUM(Brotes_Vegetativos) as Brotes_Vegetativos
            FROM Silver.Fact_Fisiologia
            GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
        ) fis ON fis.ID_Tiempo = cf.ID_Tiempo AND fis.ID_Geografia = cf.ID_Geografia AND fis.ID_Variedad = cf.ID_Variedad
        LEFT JOIN (
            SELECT ID_Tiempo, ID_Geografia, ID_Variedad, SUM(Cantidad_Bayas_Muestra) as Cantidad_Bayas
            FROM Silver.Fact_Evaluacion_Pesos
            GROUP BY ID_Tiempo, ID_Geografia, ID_Variedad
        ) pes ON pes.ID_Tiempo = cf.ID_Tiempo AND pes.ID_Geografia = cf.ID_Geografia AND pes.ID_Variedad = cf.ID_Variedad
        LEFT JOIN (
             SELECT m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad, MAX(c.Color_Cinta) as Color_Cinta
             FROM Silver.Fact_Maduracion m
             JOIN Silver.Dim_Cinta c ON c.ID_Cinta = m.ID_Cinta
             GROUP BY m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad
        ) mad ON mad.ID_Tiempo = cf.ID_Tiempo AND mad.ID_Geografia = cf.ID_Geografia AND mad.ID_Variedad = cf.ID_Variedad
        GROUP BY
            cf.ID_Tiempo, cf.ID_Geografia, cf.ID_Variedad, ISNULL(cf.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            ef.Nombre_Estado, ef.Orden_Estado
    """))
    return _contar(conexion, 'Gold.Mart_Fenologia')


def refrescar_mart_clima(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Clima (
            ID_Tiempo, Sector_Climatico, ID_Campana,
            Semana_ISO,
            Temp_Max_Promedio, Temp_Min_Promedio,
            VPD_Promedio, Humedad_Promedio,
            Precipitacion_Total
        )
        SELECT
            cl.ID_Tiempo,
            cl.Sector_Climatico,
            ISNULL(cl.ID_Campana, 0),
            t.Semana_ISO,
            AVG(cl.Temperatura_Max_C),
            AVG(cl.Temperatura_Min_C),
            AVG(cl.VPD),
            AVG(cl.Humedad_Relativa_Pct),
            SUM(cl.Precipitacion_mm)
        FROM Silver.Fact_Telemetria_Clima cl
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = cl.ID_Tiempo
        GROUP BY cl.ID_Tiempo, cl.Sector_Climatico, ISNULL(cl.ID_Campana, 0), t.Semana_ISO
    """))
    return _contar(conexion, 'Gold.Mart_Clima')


def refrescar_mart_pesos_calibres(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Pesos_Calibres (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Peso_Promedio_Baya_g, Cant_Bayas_Muestra,
            Evaluador, Peso_Proyectado_Baya_g, Tendencia_Peso,
            Estado_DQ, Fecha_Actualizacion
        )
        SELECT
            ep.ID_Tiempo,
            ep.ID_Geografia,
            ep.ID_Variedad,
            ISNULL(ep.ID_Campana, 0),
            fc.Fundo,
            mc.Modulo,
            v.Nombre_Variedad,
            t.Semana_ISO,
            AVG(ep.Peso_Promedio_Baya_g),
            SUM(ep.Cantidad_Bayas_Muestra),
            MAX(dp.Nombre_Completo),
            AVG(ep.Peso_Proyectado_Baya_g),
            AVG(ep.Peso_Promedio_Baya_g) - LAG(AVG(ep.Peso_Promedio_Baya_g)) OVER (PARTITION BY ep.ID_Geografia, ep.ID_Variedad ORDER BY ep.ID_Tiempo),
            MAX(ep.Estado_DQ),
            SYSDATETIME()
        FROM Silver.Fact_Evaluacion_Pesos ep
        JOIN Silver.Dim_Tiempo    t  ON t.ID_Tiempo = ep.ID_Tiempo
        JOIN Silver.Dim_Geografia g  ON g.ID_Geografia = ep.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad  v  ON v.ID_Variedad = ep.ID_Variedad
        LEFT JOIN Silver.Dim_Personal dp ON dp.ID_Personal = ep.ID_Personal
        GROUP BY
            ep.ID_Tiempo, ep.ID_Geografia, ep.ID_Variedad, ISNULL(ep.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO
    """))
    return _contar(conexion, 'Gold.Mart_Pesos_Calibres')


def refrescar_mart_administrativo(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Administrativo (
            ID_Tiempo, ID_Personal, ID_Actividad, ID_Campana,
            Supervisor, Semana_ISO,
            Horas_Trabajadas_Total, Horas_Trabajadas, Registros_Observados_SAP,
            DNI_Personal, Nombre_Personal, Sexo, Rol,
            Actividad, Labor, Dias_Trabajados, Pct_Asertividad,
            Fecha_Actualizacion
        )
        SELECT
            ta.ID_Tiempo,
            ta.ID_Personal,
            ta.ID_Actividad_Operativa,
            ISNULL(ta.ID_Campana, 0),
            COALESCE(sp.Nombre_Completo, 'Sin Supervisor'),
            t.Semana_ISO,
            SUM(ta.Horas_Trabajadas), -- Horas_Trabajadas_Total
            SUM(ta.Horas_Trabajadas), -- Horas_Trabajadas
            SUM(CAST(ta.Es_Observado_SAP AS INT)),
            dp.DNI,
            dp.Nombre_Completo,
            dp.Sexo,
            dp.Rol,
            da.Nombre_Actividad,
            da.Nombre_Labor,
            COUNT(DISTINCT t.Fecha),
            dp.Pct_Asertividad,
            SYSDATETIME()
        FROM Silver.Fact_Tareo ta
        JOIN Silver.Dim_Tiempo      t  ON t.ID_Tiempo = ta.ID_Tiempo
        JOIN Silver.Dim_Personal    dp ON dp.ID_Personal = ta.ID_Personal
        LEFT JOIN Silver.Dim_Personal sp ON sp.ID_Personal = ta.ID_Personal_Supervisor
        JOIN Silver.Dim_Actividad_Operativa da ON da.ID_Actividad = ta.ID_Actividad_Operativa
        GROUP BY
            ta.ID_Tiempo, ta.ID_Personal, ta.ID_Actividad_Operativa, ISNULL(ta.ID_Campana, 0),
            sp.Nombre_Completo, t.Semana_ISO, dp.DNI, dp.Nombre_Completo, dp.Sexo, dp.Rol,
            da.Nombre_Actividad, da.Nombre_Labor, dp.Pct_Asertividad
    """))
    return _contar(conexion, 'Gold.Mart_Administrativo')


def refrescar_mart_fisiologia(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Fisiologia (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Tercio, Brotes_Productivos_Promedio, Brotes_Vegetativos_Promedio,
            Hinchadas_Promedio, Productivas_Promedio, Total_Organos_Promedio,
            Fecha_Actualizacion
        )
        SELECT
            f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, ISNULL(f.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            f.Tercio,
            AVG(f.Brotes_Productivos), AVG(f.Brotes_Vegetativos),
            AVG(f.Hinchadas), AVG(f.Productivas), AVG(f.Total_Organos),
            SYSDATETIME()
        FROM Silver.Fact_Fisiologia f
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = f.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = f.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = f.ID_Variedad
        GROUP BY
            f.ID_Tiempo, f.ID_Geografia, f.ID_Variedad, ISNULL(f.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, f.Tercio
    """))
    return _contar(conexion, 'Gold.Mart_Fisiologia')


def refrescar_mart_evaluacion_vegetativa(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Evaluacion_Vegetativa (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Tipo_Evaluacion, Plantas_Evaluadas_Total,
            Plantas_En_Floracion_Total, Pct_Floracion_Promedio,
            Fecha_Actualizacion
        )
        SELECT
            ev.ID_Tiempo, ev.ID_Geografia, ev.ID_Variedad, ISNULL(ev.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            ev.Tipo_Evaluacion,
            SUM(ev.Cantidad_Plantas_Evaluadas),
            SUM(ev.Cantidad_Plantas_en_Floracion),
            AVG(CAST(ev.Cantidad_Plantas_en_Floracion AS DECIMAL(10,2)) / NULLIF(ev.Cantidad_Plantas_Evaluadas, 0) * 100),
            SYSDATETIME()
        FROM Silver.Fact_Evaluacion_Vegetativa ev
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = ev.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = ev.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = ev.ID_Variedad
        GROUP BY
            ev.ID_Tiempo, ev.ID_Geografia, ev.ID_Variedad, ISNULL(ev.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, ev.Tipo_Evaluacion
    """))
    return _contar(conexion, 'Gold.Mart_Evaluacion_Vegetativa')


def refrescar_mart_maduracion(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Maduracion (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            ID_Estado_Fenologico, Estado_Fenologico,
            ID_Cinta, Color_Cinta,
            Organos_Observados, Dias_Pasados_Promedio,
            Fecha_Actualizacion
        )
        SELECT
            m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad, ISNULL(m.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            m.ID_Estado_Fenologico, ef.Nombre_Estado,
            m.ID_Cinta, c.Color_Cinta,
            COUNT(*), AVG(CAST(m.Dias_Pasados_Del_Marcado AS DECIMAL(10,2))),
            SYSDATETIME()
        FROM Silver.Fact_Maduracion m
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = m.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = m.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = m.ID_Variedad
        JOIN Silver.Dim_Estado_Fenologico ef ON ef.ID_Estado_Fenologico = m.ID_Estado_Fenologico
        JOIN Silver.Dim_Cinta c ON c.ID_Cinta = m.ID_Cinta
        GROUP BY
            m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad, ISNULL(m.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            m.ID_Estado_Fenologico, ef.Nombre_Estado, m.ID_Cinta, c.Color_Cinta
    """))
    return _contar(conexion, 'Gold.Mart_Maduracion')


def refrescar_mart_tasa_crecimiento(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Tasa_Crecimiento (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Tipo_Evaluacion, Estado_Vegetativo, Tipo_Tallo,
            Medida_Crecimiento_Promedio, Medida_Crecimiento_Max,
            Dias_Desde_Poda_Promedio, Cantidad_Mediciones,
            Fecha_Actualizacion
        )
        SELECT
            tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, ISNULL(tc.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo,
            AVG(tc.Medida_Crecimiento), MAX(tc.Medida_Crecimiento),
            AVG(CAST(tc.Dias_Desde_Poda AS DECIMAL(10,2))), COUNT(*),
            SYSDATETIME()
        FROM Silver.Fact_Tasa_Crecimiento_Brotes tc
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = tc.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = tc.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = tc.ID_Variedad
        GROUP BY
            tc.ID_Tiempo, tc.ID_Geografia, tc.ID_Variedad, ISNULL(tc.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            tc.Tipo_Evaluacion, tc.Estado_Vegetativo, tc.Tipo_Tallo
    """))
    return _contar(conexion, 'Gold.Mart_Tasa_Crecimiento')


def refrescar_mart_induccion_floral(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Induccion_Floral (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Tipo_Evaluacion, Pct_Plantas_Con_Induccion_Prom,
            Pct_Brotes_Con_Induccion_Prom, Pct_Brotes_Con_Flor_Prom,
            Brotes_Totales, Brotes_Con_Flor,
            Fecha_Actualizacion
        )
        SELECT
            i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, ISNULL(i.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            i.Tipo_Evaluacion,
            AVG(i.Pct_Plantas_Con_Induccion),
            AVG(i.Pct_Brotes_Con_Induccion),
            AVG(i.Pct_Brotes_Con_Flor),
            SUM(i.Cantidad_Brotes_Totales),
            SUM(i.Cantidad_Brotes_Con_Flor),
            SYSDATETIME()
        FROM Silver.Fact_Induccion_Floral i
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = i.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = i.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = i.ID_Variedad
        GROUP BY
            i.ID_Tiempo, i.ID_Geografia, i.ID_Variedad, ISNULL(i.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, i.Tipo_Evaluacion
    """))
    return _contar(conexion, 'Gold.Mart_Induccion_Floral')


def refrescar_mart_ciclo_poda(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Ciclo_Poda (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Tipo_Evaluacion,
            Tallos_Planta_Total, Longitud_Tallo_Total,
            Diametro_Tallo_Total, Ramilla_Planta_Total,
            Tocones_Planta_Total, Cortes_Defectuosos_Total,
            Altura_Poda_Total, N_Muestras,
            Fecha_Actualizacion
        )
        SELECT
            p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, ISNULL(p.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            p.Tipo_Evaluacion,
            SUM(p.Tallos_Planta), SUM(p.Longitud_Tallo),
            SUM(p.Diametro_Tallo), SUM(p.Ramilla_Planta),
            SUM(p.Tocones_Planta), SUM(p.Cortes_Defectuosos),
            SUM(p.Altura_Poda), COUNT(*),
            SYSDATETIME()
        FROM Silver.Fact_Ciclo_Poda p
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = p.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = p.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = p.ID_Variedad
        GROUP BY
            p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad, ISNULL(p.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO, p.Tipo_Evaluacion
    """))
    return _contar(conexion, 'Gold.Mart_Ciclo_Poda')


def refrescar_mart_peladas(conexion) -> int:
    conexion.execute(text("""
        INSERT INTO Gold.Mart_Peladas (
            ID_Tiempo, ID_Geografia, ID_Variedad, ID_Campana,
            Fundo, Modulo, Variedad, Semana_ISO,
            Botones_Florales_Total, Flores_Total, Bayas_Pequenas_Total,
            Bayas_Grandes_Total, Fase_1_Total, Fase_2_Total,
            Bayas_Cremas_Total, Bayas_Maduras_Total,
            Bayas_Cosechables_Total,
            Plantas_Productivas_Total, Plantas_No_Productivas_Total,
            Muestras_Total, Fecha_Actualizacion
        )
        SELECT
            pel.ID_Tiempo, pel.ID_Geografia, pel.ID_Variedad, ISNULL(pel.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO,
            SUM(pel.Botones_Florales), SUM(pel.Flores), SUM(pel.Bayas_Pequenas),
            SUM(pel.Bayas_Grandes), SUM(pel.Fase_1), SUM(pel.Fase_2),
            SUM(pel.Bayas_Cremas), SUM(pel.Bayas_Maduras),
            SUM(pel.Bayas_Cosechables),
            SUM(pel.Plantas_Productivas), SUM(pel.Plantas_No_Productivas),
            SUM(pel.Muestras), SYSDATETIME()
        FROM Silver.Fact_Peladas pel
        JOIN Silver.Dim_Tiempo t ON t.ID_Tiempo = pel.ID_Tiempo
        JOIN Silver.Dim_Geografia g ON g.ID_Geografia = pel.ID_Geografia
        LEFT JOIN Silver.Dim_Fundo_Catalogo fc ON fc.ID_Fundo_Catalogo = g.ID_Fundo_Catalogo
        LEFT JOIN Silver.Dim_Modulo_Catalogo mc ON mc.ID_Modulo_Catalogo = g.ID_Modulo_Catalogo
        JOIN Silver.Dim_Variedad v ON v.ID_Variedad = pel.ID_Variedad
        GROUP BY
            pel.ID_Tiempo, pel.ID_Geografia, pel.ID_Variedad, ISNULL(pel.ID_Campana, 0),
            fc.Fundo, mc.Modulo, v.Nombre_Variedad, t.Semana_ISO
    """))
    return _contar(conexion, 'Gold.Mart_Peladas')


def _contar(conexion, mart: str) -> int:
    resultado = conexion.execute(text(f'SELECT COUNT(*) FROM {mart}'))
    return resultado.scalar()


FUNCIONES_MARTS = {
    'Gold.Mart_Cosecha': refrescar_mart_cosecha,
    'Gold.Mart_Proyecciones': refrescar_mart_proyecciones,
    'Gold.Mart_Fenologia': refrescar_mart_fenologia,
    'Gold.Mart_Clima': refrescar_mart_clima,
    'Gold.Mart_Pesos_Calibres': refrescar_mart_pesos_calibres,
    'Gold.Mart_Administrativo': refrescar_mart_administrativo,
    'Gold.Mart_Fisiologia': refrescar_mart_fisiologia,
    'Gold.Mart_Evaluacion_Vegetativa': refrescar_mart_evaluacion_vegetativa,
    'Gold.Mart_Maduracion': refrescar_mart_maduracion,
    'Gold.Mart_Tasa_Crecimiento': refrescar_mart_tasa_crecimiento,
    'Gold.Mart_Induccion_Floral': refrescar_mart_induccion_floral,
    'Gold.Mart_Ciclo_Poda': refrescar_mart_ciclo_poda,
    'Gold.Mart_Peladas': refrescar_mart_peladas,
}


def refrescar_marts_seleccionados(
    engine: Engine,
    marts: list[str] | tuple[str, ...],
    resumen_etl: dict | None = None,
    facts_bloqueantes: frozenset[str] | set[str] | None = None,
) -> dict:
    """
    Refresca solo los marts solicitados.
    facts_bloqueantes: conjunto activo del pipeline (desde DB); si None usa fallback local.
    """
    marts_set = set(marts)
    marts_solicitados = [mart for mart in MARTS if mart in marts_set]
    if not marts_solicitados:
        return {}

    if resumen_etl is not None:
        fallas = _hay_fallas_criticas(resumen_etl, facts_bloqueantes)
        if fallas:
            msg = f'Gold bloqueado - facts con error: {fallas}'
            _log.warning('[BLOCK] %s', msg)
            return {'BLOQUEADO': msg}

    resumen = {}
    with engine.begin() as conexion:
        for mart in marts_solicitados:
            _truncar(conexion, mart)

        for mart in marts_solicitados:
            filas = FUNCIONES_MARTS[mart](conexion)
            resumen[mart] = filas
            _log.info('[OK] %s: %s filas', mart, filas)

    return resumen


def refrescar_todos_los_marts(
    engine: Engine,
    resumen_etl: dict | None = None,
    facts_bloqueantes: frozenset[str] | set[str] | None = None,
) -> dict:
    """
    Refresca todos los Marts Gold en orden. TRUNCATE + INSERT, siempre desde cero.
    facts_bloqueantes: conjunto activo del pipeline (desde DB); si None usa fallback local.
    """
    if resumen_etl is not None:
        fallas = _hay_fallas_criticas(resumen_etl, facts_bloqueantes)
        if fallas:
            msg = f'Gold bloqueado - facts con error: {fallas}'
            _log.warning('[BLOCK] %s', msg)
            return {'BLOQUEADO': msg}

    resumen = {}

    with engine.begin() as conexion:
        for mart in MARTS:
            _truncar(conexion, mart)

        for mart, funcion in FUNCIONES_MARTS.items():
            filas = funcion(conexion)
            resumen[mart] = filas
            _log.info('[OK] %s: %s filas', mart, filas)

    return resumen
