"""
fact_sixweek.py
===============
Genera Silver.Fact_Proyecciones con el modelo Six-Week.

Grain: ID_Tiempo + ID_Geografia + ID_Variedad + ID_Escenario
       (una proyección por combinación y escenario "Base")

Fuentes (solo lectura, ya procesadas):
  - Silver.Fact_Maduracion       → pct_maduracion
  - Silver.Fact_Conteo_Fenologico → total_organos / total_plantas
  - Silver.Fact_Peladas          → plantas_productivas / plantas_totales
  - Silver.Fact_Cosecha_SAP      → kg base histórico (promedio semana anterior)

Parámetros de Config.Parametros_Pipeline:
  - PROY_SIXWEEK_MARGEN_PESIMISTA   (default 0.9906)
  - PROY_SIXWEEK_MARGEN_OPTIMISTA   (default 1.0107)
  - PROY_SIXWEEK_ID_ESCENARIO_BASE  (default 4)
  - PROY_SIXWEEK_SEMANAS_HISTORICO  (default 4) — nro. de semanas hacia atrás para promedio de kg

Lógica de proyección:
  kg_proyectados = kg_base * pct_maduracion * pct_productivas
  pesimista      = kg_proyectados * margen_pesimista
  optimista      = kg_proyectados * margen_optimista
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.parametros import obtener_float as _obtener_float, obtener_int as _obtener_int
from utils.contexto_transaccional import ContextoTransaccionalETL
from utils.fechas import obtener_id_tiempo
from mdm.lookup import obtener_id_campana
from silver.facts._helpers_fact_comunes import finalizar_resumen_fact as _finalizar_resumen_fact

_log = logging.getLogger("ETL_Pipeline")

TABLA_DESTINO = "Silver.Fact_Proyecciones"

# ID del escenario "Base" en Silver.Dim_Escenario_Proyeccion
_DEFAULT_ID_ESCENARIO = 4
# ID del estado workflow "Borrador" — se asigna al crear la proyección
_ID_WORKFLOW_BORRADOR = 1


# ──────────────────────────────────────────────
# Helpers de parámetros
# ──────────────────────────────────────────────

def _margen_pesimista() -> float:
    try:
        return float(_obtener_float("PROY_SIXWEEK_MARGEN_PESIMISTA", 0.9906))
    except Exception:
        return 0.9906


def _margen_optimista() -> float:
    try:
        return float(_obtener_float("PROY_SIXWEEK_MARGEN_OPTIMISTA", 1.0107))
    except Exception:
        return 1.0107


def _id_escenario_base() -> int:
    try:
        return int(_obtener_int("PROY_SIXWEEK_ID_ESCENARIO_BASE", _DEFAULT_ID_ESCENARIO))
    except Exception:
        return _DEFAULT_ID_ESCENARIO


def _semanas_historico() -> int:
    try:
        return int(_obtener_int("PROY_SIXWEEK_SEMANAS_HISTORICO", 4))
    except Exception:
        return 4


# ──────────────────────────────────────────────
# Extracción de datos desde Silver
# ──────────────────────────────────────────────

def _extraer_maduracion(engine: Engine, id_tiempo_min: int) -> pd.DataFrame:
    """
    Calcula pct_maduracion (fracción de órganos maduros/cosechables) por
    ID_Tiempo, ID_Geografia, ID_Variedad usando Silver.Fact_Maduracion.
    """
    query = text("""
        SELECT
            m.ID_Tiempo,
            m.ID_Geografia,
            m.ID_Variedad,
            -- Órganos en estado Madura o Cosechable sobre el total observado
            CAST(
                SUM(CASE WHEN ef.Nombre_Estado IN ('Madura', 'Cosechable') THEN 1.0 ELSE 0.0 END)
                / NULLIF(COUNT(*), 0)
            AS DECIMAL(10,6)) AS pct_maduracion
        FROM Silver.Fact_Maduracion m
        JOIN Silver.Dim_Estado_Fenologico ef
            ON ef.ID_Estado_Fenologico = m.ID_Estado_Fenologico
        WHERE m.ID_Tiempo >= :id_tiempo_min
        GROUP BY m.ID_Tiempo, m.ID_Geografia, m.ID_Variedad
    """)
    with engine.connect() as conn:
        return pd.DataFrame(
            conn.execute(query, {"id_tiempo_min": id_tiempo_min}).fetchall(),
            columns=["ID_Tiempo", "ID_Geografia", "ID_Variedad", "pct_maduracion"],
        )


def _extraer_conteo(engine: Engine, id_tiempo_min: int) -> pd.DataFrame:
    """
    Calcula órganos por planta (densidad) por ID_Tiempo, ID_Geografia, ID_Variedad
    usando Silver.Fact_Conteo_Fenologico.
    """
    query = text("""
        SELECT
            cf.ID_Tiempo,
            cf.ID_Geografia,
            cf.ID_Variedad,
            CAST(
                SUM(cf.Cantidad_Organos)
                / NULLIF(COUNT(DISTINCT cf.ID_Personal), 0)
            AS DECIMAL(10,4)) AS organos_por_planta
        FROM Silver.Fact_Conteo_Fenologico cf
        WHERE cf.ID_Tiempo >= :id_tiempo_min
        GROUP BY cf.ID_Tiempo, cf.ID_Geografia, cf.ID_Variedad
    """)
    with engine.connect() as conn:
        return pd.DataFrame(
            conn.execute(query, {"id_tiempo_min": id_tiempo_min}).fetchall(),
            columns=["ID_Tiempo", "ID_Geografia", "ID_Variedad", "organos_por_planta"],
        )


def _extraer_peladas(engine: Engine, id_tiempo_min: int) -> pd.DataFrame:
    """
    Calcula % de plantas productivas por ID_Tiempo, ID_Geografia, ID_Variedad
    usando Silver.Fact_Peladas.
    Retorna 1.0 si los campos de planta estan todos en NULL (campana sin datos de peladas).
    """
    query = text("""
        SELECT
            p.ID_Tiempo,
            p.ID_Geografia,
            p.ID_Variedad,
            -- Fallback 1.0: si no hay planta registrada se asume 100% productivas
            ISNULL(
                CAST(
                    SUM(CAST(p.Plantas_Productivas AS FLOAT))
                    / NULLIF(SUM(CAST(p.Plantas_Productivas + p.Plantas_No_Productivas AS FLOAT)), 0)
                AS DECIMAL(10,6)),
            1.0) AS pct_productivas
        FROM Silver.Fact_Peladas p
        WHERE p.ID_Tiempo >= :id_tiempo_min
        GROUP BY p.ID_Tiempo, p.ID_Geografia, p.ID_Variedad
    """)
    with engine.connect() as conn:
        return pd.DataFrame(
            conn.execute(query, {"id_tiempo_min": id_tiempo_min}).fetchall(),
            columns=["ID_Tiempo", "ID_Geografia", "ID_Variedad", "pct_productivas"],
        )


def _extraer_kg_base(engine: Engine, id_tiempo_min: int) -> pd.DataFrame:
    """
    Promedia los kg netos de las N semanas históricas anteriores por
    ID_Geografia, ID_Variedad, usando Silver.Fact_Cosecha_SAP.
    El resultado se usa como 'kg_base' para la proyección.
    """
    query = text("""
        SELECT
            cs.ID_Geografia,
            cs.ID_Variedad,
            AVG(CAST(cs.Kg_Neto_MP AS DECIMAL(18,4))) AS kg_base
        FROM Silver.Fact_Cosecha_SAP cs
        WHERE cs.ID_Tiempo >= :id_tiempo_min
          AND cs.Kg_Neto_MP IS NOT NULL
          AND cs.Kg_Neto_MP > 0
        GROUP BY cs.ID_Geografia, cs.ID_Variedad
    """)
    with engine.connect() as conn:
        return pd.DataFrame(
            conn.execute(query, {"id_tiempo_min": id_tiempo_min}).fetchall(),
            columns=["ID_Geografia", "ID_Variedad", "kg_base"],
        )


def _obtener_id_tiempo_semana_actual(engine: Engine) -> int | None:
    """Retorna el ID_Tiempo correspondiente a la semana ISO de la fecha actual."""
    # Pasar como string ISO: el driver ODBC viejo no bindea datetime.date
    # (pyodbc HYC00 SQLBindParameter). SQL Server lo castea solo a DATE.
    hoy_iso = date.today().isoformat()
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT ID_Tiempo
            FROM Silver.Dim_Tiempo
            WHERE CAST(:fecha AS DATE) BETWEEN Fecha AND Fecha
               OR (Anio = YEAR(CAST(:fecha AS DATE)) AND Semana_ISO = DATEPART(ISO_WEEK, CAST(:fecha AS DATE)))
            ORDER BY ID_Tiempo DESC
        """), {"fecha": hoy_iso}).fetchone()
    return int(fila[0]) if fila else None


def _obtener_id_tiempo_hace_n_semanas(engine: Engine, semanas: int) -> int | None:
    """Retorna el ID_Tiempo de N semanas atrás desde hoy."""
    fecha_limite_iso = (date.today() - timedelta(weeks=semanas)).isoformat()
    with engine.connect() as conn:
        fila = conn.execute(text("""
            SELECT MIN(ID_Tiempo)
            FROM Silver.Dim_Tiempo
            WHERE Fecha >= CAST(:fecha_limite AS DATE)
        """), {"fecha_limite": fecha_limite_iso}).fetchone()
    return int(fila[0]) if fila and fila[0] else None


# ──────────────────────────────────────────────
# Cálculo de Proyección
# ──────────────────────────────────────────────

def _calcular_proyeccion(
    df_mad: pd.DataFrame,
    df_pel: pd.DataFrame,
    df_kg: pd.DataFrame,
    margen_pesimista: float,
    margen_optimista: float,
) -> pd.DataFrame:
    """
    Une los DataFrames y aplica la formula:
      kg_proyectados = kg_base * pct_maduracion * pct_productivas

    Estrategia de robustez:
    - Si Peladas no tiene datos para una combinacion, pct_productivas = 1.0
      (asume todas las plantas productivas — escenario conservador).
    - Si Cosecha_SAP no tiene historico, kg_base = 0 (proyeccion queda en 0,
      disponible para override manual en el portal).
    - Solo se descartan combinaciones sin pct_maduracion (el driver principal).
    """
    # Maduracion es el driver obligatorio
    df = df_mad.copy()

    # LEFT JOIN con Peladas: si no hay match, pct_productivas queda NaN -> se llena con 1.0
    df = df.merge(df_pel, on=["ID_Tiempo", "ID_Geografia", "ID_Variedad"], how="left")

    # LEFT JOIN con kg_base (sin ID_Tiempo — es historico ponderado por geo+variedad)
    df = df.merge(df_kg, on=["ID_Geografia", "ID_Variedad"], how="left")

    # Asegurar tipos numericos
    for col in ["pct_maduracion", "pct_productivas", "kg_base"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fallbacks: pct_productivas=1.0 si sin datos Peladas, kg_base=0 si sin Cosecha
    df["pct_productivas"] = df["pct_productivas"].fillna(1.0)
    df["kg_base"] = df["kg_base"].fillna(0.0)

    # Solo descartar si no hay maduracion (es el insumo de mayor calidad)
    df = df.dropna(subset=["pct_maduracion"])

    df["Kg_Proyectados"] = (
        df["kg_base"] * df["pct_maduracion"] * df["pct_productivas"]
    ).round(4)

    df["Kg_Pesimista"] = (df["Kg_Proyectados"] * margen_pesimista).round(4)
    df["Kg_Optimista"] = (df["Kg_Proyectados"] * margen_optimista).round(4)

    return df


# ──────────────────────────────────────────────
# Construcción de Payload
# ──────────────────────────────────────────────

def _construir_payload(
    df: pd.DataFrame,
    engine: Engine,
    id_escenario: int,
) -> list[dict]:
    """
    Genera el payload para insertar en Silver.Fact_Proyecciones.
    Resuelve ID_Campana usando el lookup estándar del proyecto.
    """
    payload = []
    cache_campana: dict[tuple, int | None] = {}
    fecha_cutoff = date.today()

    for _, fila in df.iterrows():
        id_tiempo = int(fila["ID_Tiempo"])
        id_geo = int(fila["ID_Geografia"])
        id_var = int(fila["ID_Variedad"])
        kg_proy = float(fila["Kg_Proyectados"])

        # Ignorar proyecciones negativas o cero (sin datos útiles)
        if kg_proy <= 0:
            continue

        # Resolver ID_Campana con cache
        clave_campana = (id_geo, id_var)
        if clave_campana not in cache_campana:
            cache_campana[clave_campana] = obtener_id_campana(
                id_geo, id_var, fecha_cutoff, engine
            )
        id_campana = cache_campana[clave_campana]

        payload.append({
            "ID_Tiempo":           id_tiempo,
            "ID_Geografia":        id_geo,
            "ID_Variedad":         id_var,
            "ID_Escenario":        id_escenario,
            "ID_Campana":          id_campana,
            "ID_Estado_Workflow":  _ID_WORKFLOW_BORRADOR,
            "Kg_Proyectados":      kg_proy,
            "Kg_Pesimista":        float(fila["Kg_Pesimista"]),
            "Kg_Optimista":        float(fila["Kg_Optimista"]),
            "Pct_Maduracion":      float(fila["pct_maduracion"]),
            "Pct_Productivas":     float(fila["pct_productivas"]),
            "Fecha_Cutoff":        fecha_cutoff,
            "Fecha_Evento":        fecha_cutoff,  # Se agrega para evitar error NOT NULL
            "Fecha_Sistema":       pd.Timestamp.now(),
            "MAPE":                None,
            "Version_Modelo":      "sixweek-v1",
            "Flag_Override":       False,
            "Motivo_Override":     None,
            "Estado_DQ":           "OK",
        })

    return payload


# ──────────────────────────────────────────────
# Función pública del pipeline
# ──────────────────────────────────────────────

def cargar_fact_sixweek(engine: Engine) -> dict:
    """
    Punto de entrada del pipeline para el procesador Six-Week.

    Extrae datos de las capas Silver de maduración, conteo y cosecha,
    calcula la proyección y la inserta en Silver.Fact_Proyecciones usando
    la lógica de deduplicación estándar (MERGE o WHERE NOT EXISTS).
    """
    resumen: dict = {
        "leidos":      0,
        "insertados":  0,
        "rechazados":  0,
        "cuarentena":  [],
    }

    # 1. Obtener parámetros
    margen_p = _margen_pesimista()
    margen_o = _margen_optimista()
    id_escenario = _id_escenario_base()
    semanas_hist = _semanas_historico()

    _log.info(f"[SixWeek] Parámetros — pesimista={margen_p}, optimista={margen_o}, "
               f"escenario={id_escenario}, ventana={semanas_hist}s")

    # 2. Resolver ventana temporal
    id_tiempo_actual = _obtener_id_tiempo_semana_actual(engine)
    id_tiempo_historico = _obtener_id_tiempo_hace_n_semanas(engine, semanas_hist)

    if not id_tiempo_actual:
        _log.warning("[SixWeek] No se pudo resolver ID_Tiempo para la semana actual. Abortando.")
        return _finalizar_resumen_fact(resumen)

    if not id_tiempo_historico:
        _log.warning("[SixWeek] No se pudo resolver ID_Tiempo histórico. Abortando.")
        return _finalizar_resumen_fact(resumen)

    _log.info(f"[SixWeek] Ventana — ID_Tiempo actual={id_tiempo_actual}, "
               f"ID_Tiempo histórico mínimo={id_tiempo_historico}")

    # 3. Extraer inputs de Silver
    df_mad = _extraer_maduracion(engine, id_tiempo_historico)
    df_pel = _extraer_peladas(engine, id_tiempo_historico)
    df_kg = _extraer_kg_base(engine, id_tiempo_historico)

    _log.info(f"[SixWeek] Filas extraídas — maduracion={len(df_mad)}, "
               f"peladas={len(df_pel)}, kg_base={len(df_kg)}")

    if df_mad.empty or df_pel.empty or df_kg.empty:
        _log.warning("[SixWeek] Datos insuficientes en alguna fuente Silver. Abortando.")
        return _finalizar_resumen_fact(resumen)

    # 4. Calcular proyección
    df_proy = _calcular_proyeccion(df_mad, df_pel, df_kg, margen_p, margen_o)
    resumen["leidos"] = len(df_proy)
    _log.info(f"[SixWeek] Combinaciones con proyección calculada: {len(df_proy)}")

    if df_proy.empty:
        _log.warning("[SixWeek] No se generaron proyecciones (sin combinaciones completas).")
        return _finalizar_resumen_fact(resumen)

    # 5. Construir payload
    payload = _construir_payload(df_proy, engine, id_escenario)
    _log.info(f"[SixWeek] Payload generado: {len(payload)} registros")

    if not payload:
        return _finalizar_resumen_fact(resumen)

    # 6. Insertar en Silver.Fact_Proyecciones usando transacción estándar
    with ContextoTransaccionalETL(engine) as contexto:
        conexion = contexto._conexion_activa()

        # DROP/CREATE tabla temporal para la inserción
        conexion.execute(text("""
            IF OBJECT_ID('tempdb..#Temp_Proyecciones_SixWeek') IS NOT NULL
                DROP TABLE #Temp_Proyecciones_SixWeek;

            CREATE TABLE #Temp_Proyecciones_SixWeek (
                ID_Tiempo          INT,
                ID_Geografia       INT,
                ID_Variedad        INT,
                ID_Escenario       INT,
                ID_Campana         INT,
                ID_Estado_Workflow INT,
                Kg_Proyectados     DECIMAL(18,4),
                Kg_Pesimista       DECIMAL(18,4),
                Kg_Optimista       DECIMAL(18,4),
                Pct_Maduracion     DECIMAL(10,6),
                Pct_Productivas    DECIMAL(10,6),
                Fecha_Cutoff       DATE,
                Fecha_Evento       DATE,
                Fecha_Sistema      DATETIME2,
                MAPE               DECIMAL(10,4),
                Version_Modelo     NVARCHAR(100),
                Flag_Override      BIT,
                Motivo_Override    NVARCHAR(500),
                Estado_DQ          NVARCHAR(20)
            );
        """))

        # Insertar filas en temp
        cols = [
            "ID_Tiempo", "ID_Geografia", "ID_Variedad", "ID_Escenario", "ID_Campana",
            "ID_Estado_Workflow", "Kg_Proyectados", "Kg_Pesimista", "Kg_Optimista",
            "Pct_Maduracion", "Pct_Productivas", "Fecha_Cutoff", "Fecha_Evento", "Fecha_Sistema",
            "MAPE", "Version_Modelo", "Flag_Override", "Motivo_Override", "Estado_DQ",
        ]
        placeholders = ", ".join(f":{c}" for c in cols)
        col_list = ", ".join(cols)

        conexion.execute(
            text(f"INSERT INTO #Temp_Proyecciones_SixWeek ({col_list}) VALUES ({placeholders})"),
            payload,
        )

        # MERGE: actualiza si ya existe la combinación para este escenario, inserta si no
        resultado_merge = conexion.execute(text("""
            MERGE Silver.Fact_Proyecciones AS dest
            USING #Temp_Proyecciones_SixWeek AS src
            ON (
                src.ID_Tiempo    = dest.ID_Tiempo
                AND src.ID_Geografia = dest.ID_Geografia
                AND src.ID_Variedad  = dest.ID_Variedad
                AND src.ID_Escenario = dest.ID_Escenario
            )
            WHEN MATCHED THEN UPDATE SET
                dest.Kg_Proyectados    = src.Kg_Proyectados,
                dest.Kg_Pesimista      = src.Kg_Pesimista,
                dest.Kg_Optimista      = src.Kg_Optimista,
                dest.Pct_Maduracion    = src.Pct_Maduracion,
                dest.Pct_Productivas   = src.Pct_Productivas,
                dest.ID_Campana        = ISNULL(src.ID_Campana, dest.ID_Campana),
                dest.Fecha_Cutoff      = src.Fecha_Cutoff,
                dest.Fecha_Evento      = src.Fecha_Evento,
                dest.Fecha_Sistema     = src.Fecha_Sistema,
                dest.Version_Modelo    = src.Version_Modelo,
                dest.Estado_DQ         = src.Estado_DQ
            WHEN NOT MATCHED BY TARGET THEN INSERT (
                ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario, ID_Campana,
                ID_Estado_Workflow, Kg_Proyectados, Kg_Pesimista, Kg_Optimista,
                Pct_Maduracion, Pct_Productivas, Fecha_Cutoff, Fecha_Evento, Fecha_Sistema,
                MAPE, Version_Modelo, Flag_Override, Motivo_Override, Estado_DQ
            ) VALUES (
                src.ID_Tiempo, src.ID_Geografia, src.ID_Variedad, src.ID_Escenario, src.ID_Campana,
                src.ID_Estado_Workflow, src.Kg_Proyectados, src.Kg_Pesimista, src.Kg_Optimista,
                src.Pct_Maduracion, src.Pct_Productivas, src.Fecha_Cutoff, src.Fecha_Evento, src.Fecha_Sistema,
                src.MAPE, src.Version_Modelo, src.Flag_Override, src.Motivo_Override, src.Estado_DQ
            )
            OUTPUT $action;
        """))

        filas_accion = resultado_merge.fetchall()
        n_insert = sum(1 for r in filas_accion if r[0] == "INSERT")
        n_update = sum(1 for r in filas_accion if r[0] == "UPDATE")

        resumen["insertados"] = n_insert
        resumen["actualizados"] = n_update

        _log.info(f"[SixWeek] MERGE — {n_insert} INSERT, {n_update} UPDATE")

        conexion.execute(text(
            "IF OBJECT_ID('tempdb..#Temp_Proyecciones_SixWeek') IS NOT NULL "
            "DROP TABLE #Temp_Proyecciones_SixWeek"
        ))

    return _finalizar_resumen_fact(resumen)
