"""
Fórmula central (por semana N, por unidad Módulo×Turno×Válvula×Variedad):
    Kg_N = Σ_estados(Conteo_estado × %Madura_N × Plantas × Peso_baya_kg_N × %Prod_N)
           × decay_factor[N]

Asunciones heredadas del Excel que se mantienen por compatibilidad:
    - Cada punto de muestreo representa 10 plantas (PLANTAS_POR_PUNTO).
    - Si Fact_Peladas no tiene datos para id_tiempo, se usa el corte anterior
      disponible (MAX(ID_Tiempo) <= :t).
    - El lookup de pesos usa Módulo+Variedad+Semana_ISO (sin Turno/Válvula),
      igual que la hoja «Pesos» del Excel.
    - Los pesos se buscan en la semana iso = sem_base + (w-1), es decir W1 usa
      el peso de la semana de evaluación, W2 el de la siguiente, etc.
    - Si no hay pesos en el año en curso, se usa el histórico más reciente del
      mismo rango de semanas (fallback inter-anual); ver lookup_peso_baya.
    - cerrar_matriz resuelve los None en cadena secuencial: cada None = 1 − Σ
      (semanas anteriores ya resueltas). Replica exactamente la lógica del Excel
      (p.ej. fase_1 S5 = 1−(S1+S2+S3+S4) y luego S6 = 1−(S1+…+S5) usando S5
      ya calculado). Valores negativos se saturan a 0.0.

Sin efectos secundarios: no escribe a SQL, solo retorna DataFrames.
"""

from __future__ import annotations

import datetime as dt
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# ── Configuración (Constantes del Modelo) ───────────────────────────────────

# Estados que aportan a cada semana (corte W1-W6)
ESTADOS_POR_SEMANA = {
    1: ["cosechable", "maduras", "cremas", "fase_2", "fase_1"],
    2: ["cremas", "fase_2", "fase_1", "maduras", "cosechable"],
    3: ["fase_1", "verdes", "fase_2"],
    4: ["verdes", "pequena", "fase_1", "fase_2"],
    5: ["verdes", "pequena", "fase_1"],
    6: ["verdes", "pequena", "fase_1"],
}

DECAY_FACTOR = {1: 1.0, 2: 1.0, 3: 0.8, 4: 0.8, 5: 0.8, 6: 0.8}

# Margenes de sensibilidad
MARGEN_PESIMISTA = 0.9906
MARGEN_OPTIMISTA = 1.0107

# Pattern de productivas
DELTA_PRODUCTIVAS = {1: 0.0, 2: +0.02, 3: 0.0, 4: -0.03, 5: +0.01, 6: +0.01}

# Matriz editable por el usuario
# Las casillas con valor son INPUTS. Las casillas en None son AUTO (= 1 − Σ anteriores).
MATRIZ_INPUTS_DEFAULT = {
    "cosechable":  {1: 1.0, 2: None},
    "maduras":     {1: 1.0, 2: None},
    "cremas":      {1: 1.0, 2: None},
    "fase_2":      {1: 0.14, 2: 0.40, 3: None},          # S3 = 1 − (S1+S2)
    "fase_1":      {1: 0.0, 2: 0.0, 3: 0.10, 4: 0.60,
                    5: None, 6: None},                    # S5/S6 reparten el resto
    # verdes: S3=0 y S4=0 son fijos (no cosecha todavía). S5 y S6 son inputs del
    # usuario porque varían por campo/variedad — el Excel no tiene un valor único.
    # El remanente (1 − S5 − S6) queda en 0 porque esas bayas maduran en W7+,
    # fuera del corte de 6 semanas proyectadas. Comportamiento intencional.
    # Valores por defecto tomados de la fila más representativa del Excel (M=1, Sekoya Pop).
    "verdes":      {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.16, 6: 0.17},
    # pequena: en el Excel la columna % Pequeña S4 (col AK) es SIEMPRE celda vacía
    # en las 735 filas de datos — nunca es una fórmula 1-Σ. Se usa 0.0 explícito
    # para que cerrar_matriz no lo trate como auto-calculado.
    "pequena":     {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0},
}

ID_ESTADO_MAP = {
    9: "cosechable",
    8: "maduras",
    7: "cremas",
    6: "fase_2",
    5: "fase_1",
    4: "verdes",
    3: "pequena",
}

# Cada punto de muestreo en Fact_Conteo_Fenologico representa este número de plantas.
# Asunción heredada del Excel — cambiar aquí si el protocolo de campo cambia.
PLANTAS_POR_PUNTO: int = 10


def validar_matriz_inputs(inputs: dict[str, dict[int, float | None]]) -> dict[str, dict]:
    """
    Valida la matriz de inputs antes de cerrarla.

    Por estado revisa:
        - Suma de inputs (ignorando None) > 1.0  → exceso de saturación.
        - Algún valor fuera de [0, 1].
        - Estado sin Nones y suma < 1  → cola fuera del corte W1-W6 (advertencia).

    Retorna {estado: {"suma": float, "tiene_nones": bool, "errores": [str], "advertencias": [str]}}
    """
    reporte: dict[str, dict] = {}
    for estado, semanas in inputs.items():
        suma = 0.0
        tiene_nones = False
        errores: list[str] = []
        advertencias: list[str] = []

        for w in range(1, 7):
            val = semanas.get(w)
            if val is None:
                tiene_nones = True
                continue
            try:
                fval = float(val)
            except (TypeError, ValueError):
                errores.append(f"W{w}: valor no numérico ({val!r}).")
                continue
            if fval < 0 or fval > 1:
                errores.append(f"W{w}: {fval:.3f} fuera del rango [0, 1].")
                continue
            suma += fval

        # Suma > 1: el estado pretende cosechar más del 100% de su contenido.
        if suma > 1.0 + 1e-6:
            errores.append(f"Suma de inputs = {suma:.3f} > 1.00 (excede el 100%).")

        # Si la suma es < 1 sin Nones, el estado deja una cola fuera del corte W1-W6.
        # Es válido (puede ser intencional para verdes/pequena), solo informamos.
        if (not tiene_nones) and suma < 1.0 - 1e-6:
            advertencias.append(
                f"Suma = {suma:.3f} < 1.00 — el {(1 - suma) * 100:.1f}% restante "
                f"queda fuera del corte W1-W6 (no se cosecha en este horizonte)."
            )

        reporte[estado] = {
            "suma": round(suma, 6),
            "tiene_nones": tiene_nones,
            "errores": errores,
            "advertencias": advertencias,
        }
    return reporte


def cerrar_matriz(inputs: dict[str, dict[int, float | None]]) -> dict[str, list[float]]:
    """
    Recibe los inputs del usuario por estado y completa las celdas None
    usando una cadena secuencial: cada None = 1 − Σ(semanas anteriores ya resueltas).

    Esto replica exactamente la lógica del Excel operacional:
      - Cremas  S2 = 1 − S1
      - Fase2   S3 = 1 − (S1 + S2)
      - Fase1   S5 = 1 − (S1 + S2 + S3 + S4)
      - Fase1   S6 = 1 − (S1 + S2 + S3 + S4 + S5)  ← usa S5 ya calculado

    El orden ascendente de semanas garantiza que el None anterior ya está resuelto
    cuando se calcula el siguiente. Valores negativos se saturan a 0.0.

    Retorna {estado: [W1, W2, W3, W4, W5, W6]}.
    """
    matriz_cerrada: dict[str, list[float]] = {}

    for estado, semanas in inputs.items():
        # Construir dict mutable W1..W6 (None donde no hay input)
        valores: dict[int, float | None] = {}
        for w in range(1, 7):
            val = semanas.get(w)
            valores[w] = None if val is None else float(val)

        # Resolver Nones en orden ascendente (cadena: cada None usa los anteriores ya resueltos)
        for w in range(1, 7):
            if valores[w] is None:
                suma_anteriores = sum(
                    valores[s]                # type: ignore[arg-type]
                    for s in range(1, w)
                    if valores[s] is not None
                )
                valores[w] = max(0.0, round(1.0 - suma_anteriores, 10))

        matriz_cerrada[estado] = [float(valores[w]) for w in range(1, 7)]  # type: ignore[arg-type]

    return matriz_cerrada



# ── Extracción de datos ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_fechas_disponibles() -> list[int]:
    """
    Retorna la unión de semanas con datos en cualquiera de las 3 tablas fuente.
    Si una semana tiene datos en Peladas pero no en Conteo, igual aparece en el dropdown.
    La validación de completitud se hace al momento de seleccionar la semana
    mediante verificar_integridad_datos(), que advierte qué falta sin bloquear.
    """
    from utils.db import ejecutar_query

    sql = """
        SELECT MAX(f.ID_Tiempo) as ID_Tiempo
        FROM (
            SELECT ID_Tiempo FROM Silver.Fact_Conteo_Fenologico WITH (NOLOCK)
            UNION
            SELECT ID_Tiempo FROM Silver.Fact_Peladas WITH (NOLOCK)
            UNION
            SELECT ID_Tiempo FROM Silver.Fact_Evaluacion_Pesos WITH (NOLOCK)
        ) f
        JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
        GROUP BY dt.Anio, dt.Semana_ISO
        ORDER BY ID_Tiempo DESC
    """
    df = ejecutar_query(sql)
    return df["ID_Tiempo"].tolist() if not df.empty else []


@st.cache_data(ttl=600, show_spinner="Cargando combinaciones disponibles...")
def obtener_combinaciones_disponibles(id_tiempo: int) -> pd.DataFrame:
    """
    Retorna el universo COMPLETO de combinaciones (Fundo, Modulo, Variedad, Condicion)
    con datos en Fact_Conteo_Fenologico para la fecha indicada.

    Es la "fuente de verdad" para la cascada bidireccional de filtros del UI:
    cualquier dropdown se puede filtrar entre sí sobre este DataFrame.

    Notas de modelado:
    - Fundo viene directamente de Dim_Geografia → Dim_Fundo_Catalogo.
    - Condición se cruza con Dim_Condicion_Cultivo a través de Fact_Cosecha_SAP
      (la condición orgánica/convencional se asigna a nivel de cosecha, no de
      geografía). Si una geografía no tiene cosecha registrada, queda con
      Condicion = NULL → se mostrará como "Sin condición" en la UI.

    Columnas devueltas: Fundo, Modulo, Variedad, Condicion (todas strings).
    """
    from utils.db import ejecutar_query

    sql = """
        SELECT DISTINCT
            f_cat.Fundo                                    AS Fundo,
            CAST(m_cat.Modulo AS NVARCHAR(50))             AS Modulo,
            v.Nombre_Variedad                              AS Variedad,
            ISNULL(cc.Sustrato + ' - ' + cc.Certificacion,
                   'Sin condición')                        AS Condicion
        FROM Silver.Fact_Conteo_Fenologico f WITH (NOLOCK)
        JOIN Silver.Dim_Variedad v WITH (NOLOCK)
            ON f.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK)
            ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m_cat WITH (NOLOCK)
            ON g.ID_Modulo_Catalogo = m_cat.ID_Modulo_Catalogo
        JOIN Silver.Dim_Fundo_Catalogo f_cat WITH (NOLOCK)
            ON g.ID_Fundo_Catalogo = f_cat.ID_Fundo_Catalogo
        LEFT JOIN Silver.Fact_Cosecha_SAP cs WITH (NOLOCK)
            ON cs.ID_Geografia = g.ID_Geografia
           AND cs.ID_Variedad  = f.ID_Variedad
        LEFT JOIN Silver.Dim_Condicion_Cultivo cc WITH (NOLOCK)
            ON cs.ID_Condicion_Cultivo = cc.ID_Condicion
        WHERE f.ID_Tiempo = :t
    """
    df = ejecutar_query(sql, params={"t": id_tiempo})

    if df.empty:
        return pd.DataFrame(columns=["Fundo", "Modulo", "Variedad", "Condicion"])

    # Normalizar tipos a string para que las comparaciones en la UI sean estables
    for col in ["Fundo", "Modulo", "Variedad", "Condicion"]:
        df[col] = df[col].astype(str).fillna("Sin condición")

    return df.drop_duplicates().reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def verificar_integridad_datos(id_tiempo: int, modulo: int | None = None, variedad: str | None = None, condicion: str | None = None) -> dict[str, bool]:
    """
    Verifica si existen los 3 pilares de datos para la selección.
    Retorna {'conteo': bool, 'peladas': bool, 'pesos': bool}
    """
    from utils.db import ejecutar_query
    import pandas as pd
    
    res = {"conteo": False, "peladas": False, "pesos": False}

    # 1. Conteo
    # Usamos JOIN a Dim_Modulo_Catalogo (igual que en extraer_datos_granulares)
    # para evitar subquery que puede devolver múltiples filas si Modulo no es único.
    filtro_c = ""
    params_c = {"t": id_tiempo}
    if modulo:
        filtro_c += " AND m.Modulo = :m"
        params_c["m"] = modulo
    if variedad:
        filtro_c += " AND v.Nombre_Variedad = :v"
        params_c["v"] = variedad

    df_c = ejecutar_query(
        f"""SELECT TOP 1 1
        FROM Silver.Fact_Conteo_Fenologico f WITH (NOLOCK)
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON f.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Tiempo dt ON f.ID_Tiempo = dt.ID_Tiempo
        WHERE dt.Anio = (SELECT Anio FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          AND dt.Semana_ISO = (SELECT Semana_ISO FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          {filtro_c}""",
        params=params_c,
    )
    res["conteo"] = not df_c.empty
    
    # 2. Censo de Plantas: se toma el registro del censo 2026
    df_p = ejecutar_query("SELECT TOP 1 1 FROM Silver.Fact_Censo_Plantas WITH (NOLOCK)", params={})
    res["peladas"] = not df_p.empty
    
    # 3. Pesos: se toma la semana ISO solicitada
    filtro_w = ""
    params_w: dict = {"t": id_tiempo}
    if variedad:
        filtro_w = " AND v.Nombre_Variedad = :v"
        params_w["v"] = variedad

    df_w = ejecutar_query(
        f"""SELECT TOP 1 1
        FROM Silver.Fact_Evaluacion_Pesos p WITH (NOLOCK)
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON p.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Tiempo dt ON p.ID_Tiempo = dt.ID_Tiempo
        WHERE dt.Anio = (SELECT Anio FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          AND dt.Semana_ISO = (SELECT Semana_ISO FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          {filtro_w}""",
        params=params_w,
    )
    res["pesos"] = not df_w.empty

    return res


@st.cache_data(ttl=300, show_spinner="Cargando datos granulares...")
def extraer_datos_granulares(
    id_tiempo: int,
    modulo: int | None = None,
    variedad: str | None = None,
    condicion: str | None = None,
    fundo: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Extrae las 3 fuentes principales con granularidad (Mod, Turno, Valv, Var)
    aplicando filtros opcionales de Módulo, Variedad, Condición y Fundo.

    El filtrado opera de forma libre: cualquier filtro puede ir solo o combinado.
    Por ejemplo: condicion='Suelo - Organico' sin modulo trae todas las unidades
    orgánicas de la semana.
    """
    from utils.db import ejecutar_query

    # 1. Filtros dinámicos
    filtro_conteo = ""
    filtro_plantas = ""
    params_conteo = {"t": id_tiempo}
    params_plantas = {"t": id_tiempo}

    if modulo:
        filtro_conteo += " AND m.Modulo = :m"
        filtro_plantas += " AND m.Modulo = :m"
        params_conteo["m"] = modulo
        params_plantas["m"] = modulo
    if variedad:
        filtro_conteo += " AND v.Nombre_Variedad = :v"
        params_conteo["v"] = variedad
    if fundo:
        # Filtro por nombre de Fundo (Dim_Fundo_Catalogo.Fundo)
        filtro_conteo += " AND f_cat.Fundo = :fnd"
        filtro_plantas += " AND f_cat.Fundo = :fnd"
        params_conteo["fnd"] = fundo
        params_plantas["fnd"] = fundo
    if condicion:
        # Buscamos el ID_Condicion que corresponde al nombre compuesto 'Sustrato - Certificacion'.
        # Se usan parámetros nombrados (:sus, :cert) en lugar de interpolación directa
        # para mantener consistencia con el resto de filtros y evitar inyección SQL.
        partes = condicion.split(" - ")
        if len(partes) == 2:
            sus, cert = partes[0], partes[1]
            filtro_cond = (
                " AND g.ID_Geografia IN ("
                "SELECT cs.ID_Geografia FROM Silver.Fact_Cosecha_SAP cs "
                "JOIN Silver.Dim_Condicion_Cultivo c ON cs.ID_Condicion_Cultivo = c.ID_Condicion "
                "WHERE c.Sustrato = :sus AND c.Certificacion = :cert)"
            )
            filtro_conteo += filtro_cond
            filtro_plantas += filtro_cond
            params_conteo["sus"] = sus
            params_conteo["cert"] = cert
            params_plantas["sus"] = sus
            params_plantas["cert"] = cert



    # 1. Conteo por estado fenológico — incluye Fundo, Condicion y Certificacion
    # para trazabilidad. La Condicion/Certificacion vienen vía OUTER APPLY a
    # Fact_Cosecha_SAP (asignación por geografía+variedad). Si no hay cosecha
    # registrada queda 'Sin condición' / 'Sin certificación'.
    #
    # Certificacion se traer aparte (no derivada del nombre) para clasificar
    # Orgánico vs Convencional sin heurísticas de string.
    df_conteo = ejecutar_query(
        f"""SELECT
            f_cat.Fundo AS fundo,
            m.Modulo AS modulo,
            t.Turno AS turno,
            v_val.Valvula AS valvula,
            v.Nombre_Variedad AS variedad,
            ISNULL(cond_oa.Condicion, 'Sin condición') AS condicion,
            ISNULL(cond_oa.Certificacion, 'Sin certificación') AS certificacion,
            f.ID_Estado_Fenologico AS id_estado,
            SUM(f.Cantidad_Organos * 1.0) AS total_organos,
            COUNT(DISTINCT f.Punto) AS puntos
        FROM Silver.Fact_Conteo_Fenologico f WITH (NOLOCK)
        JOIN Silver.Dim_Tiempo dt_f ON f.ID_Tiempo = dt_f.ID_Tiempo
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON f.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Turno_Catalogo t WITH (NOLOCK) ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo v_val WITH (NOLOCK) ON g.ID_Valvula_Catalogo = v_val.ID_Valvula_Catalogo
        JOIN Silver.Dim_Fundo_Catalogo f_cat WITH (NOLOCK) ON g.ID_Fundo_Catalogo = f_cat.ID_Fundo_Catalogo
        OUTER APPLY (
            SELECT TOP 1
                cc.Sustrato + ' - ' + cc.Certificacion AS Condicion,
                cc.Certificacion                       AS Certificacion
            FROM Silver.Fact_Cosecha_SAP cs WITH (NOLOCK)
            JOIN Silver.Dim_Condicion_Cultivo cc WITH (NOLOCK)
                ON cs.ID_Condicion_Cultivo = cc.ID_Condicion
            WHERE cs.ID_Geografia = g.ID_Geografia
              AND cs.ID_Variedad = v.ID_Variedad
            ORDER BY cs.ID_Tiempo DESC
        ) cond_oa
        WHERE dt_f.Anio = (SELECT Anio FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          AND dt_f.Semana_ISO = (SELECT Semana_ISO FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t)
          {filtro_conteo}
        GROUP BY f_cat.Fundo, m.Modulo, t.Turno, v_val.Valvula, v.Nombre_Variedad,
                 cond_oa.Condicion, cond_oa.Certificacion, f.ID_Estado_Fenologico""",
        params=params_conteo,
    )

    # 2. Plantas por unidad (Silver.Fact_Censo_Plantas)
    # Se utiliza el censo para obtener la población total de plantas.
    # Dado que el censo no trae el desglose de productivas/no-productivas,
    # se asume 100% de productividad base (S1), la cual se ajustará por el patrón DELTA_PRODUCTIVAS.
    df_plantas = ejecutar_query(
        f"""SELECT
            m.Modulo AS modulo,
            t.Turno AS turno,
            v_val.Valvula AS valvula,
            CAST(SUM(f.Cantidad_Plantas) AS FLOAT) AS plantas_sampleadas,
            1.0 AS pct_productivas_s1
        FROM Silver.Fact_Censo_Plantas f WITH (NOLOCK)
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON f.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo v_val ON g.ID_Valvula_Catalogo = v_val.ID_Valvula_Catalogo
        JOIN Silver.Dim_Fundo_Catalogo f_cat ON g.ID_Fundo_Catalogo = f_cat.ID_Fundo_Catalogo
        WHERE 1=1 {filtro_plantas}
        GROUP BY m.Modulo, t.Turno, v_val.Valvula""",
        params=params_plantas,
    )

    # 3. Peso de baya — replicando la hoja 'Pesos' del Excel.
    # El Excel tiene el peso historico por Semana ISO x Modulo x Variedad.
    # Para cada semana proyectada Wn, usa el peso historico de la semana (sem_base + n).
    # Esto NO es buscar datos futuros: es usar el HISTORICO del mismo rango ISO
    # del año anterior (o el mas reciente disponible para ese numero de semana).
    df_sem_base = ejecutar_query(
        "SELECT DATEPART(ISO_WEEK, Fecha) AS sem_base, YEAR(Fecha) AS anio_base "
        "FROM Silver.Dim_Tiempo WHERE ID_Tiempo = :t",
        params={"t": id_tiempo},
    )
    sem_base = int(df_sem_base.iloc[0]["sem_base"]) if not df_sem_base.empty else 1
    anio_base = int(df_sem_base.iloc[0]["anio_base"]) if not df_sem_base.empty else 2026

    # Nivel 1: Pesos del año en curso para el rango sem_base+1 a sem_base+6
    # (igual que el Excel: BL2=sem+1 para W1, BM2=sem+2 para W2, etc.)
    max_sem_anio = 53 if dt.date(anio_base, 12, 28).isocalendar()[1] == 53 else 52
    sem_ini = sem_base + 1
    sem_fin = sem_base + 6

    if sem_fin <= max_sem_anio:
        filtro_sem = "DATEPART(ISO_WEEK, t.Fecha) BETWEEN :s1 AND :s2 AND YEAR(t.Fecha) = :y"
        params_p = {"s1": sem_ini, "s2": sem_fin, "y": anio_base}
    else:
        # Rollover al año siguiente
        filtro_sem = (
            "(YEAR(t.Fecha) = :y AND DATEPART(ISO_WEEK, t.Fecha) >= :s1) "
            "OR (YEAR(t.Fecha) = :y2 AND DATEPART(ISO_WEEK, t.Fecha) <= :s2)"
        )
        params_p = {"s1": sem_ini, "s2": sem_fin % max_sem_anio, "y": anio_base, "y2": anio_base + 1}

    df_pesos = ejecutar_query(
        f"""SELECT
            m.Modulo AS modulo,
            v.Nombre_Variedad AS variedad,
            DATEPART(ISO_WEEK, t.Fecha) AS semana_iso,
            AVG(p.Peso_Promedio_Baya_g) / 1000.0 AS peso_baya_kg
        FROM Silver.Fact_Evaluacion_Pesos p WITH (NOLOCK)
        JOIN Silver.Dim_Tiempo t WITH (NOLOCK) ON p.ID_Tiempo = t.ID_Tiempo
        JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON p.ID_Variedad = v.ID_Variedad
        JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON p.ID_Geografia = g.ID_Geografia
        JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        WHERE {filtro_sem}
        GROUP BY m.Modulo, v.Nombre_Variedad, DATEPART(ISO_WEEK, t.Fecha)""",
        params=params_p,
    )

    # Nivel 2 (fallback inter-anual): si no hay pesos del año en curso
    # para ese rango ISO, se usa el histórico de CUALQUIER año disponible.
    # Esto replica exactamente lo que hace el Excel cuando referencia datos
    # de campañas anteriores en la hoja Pesos.
    if df_pesos.empty:
        if sem_fin <= 53:
            filtro_hist = "DATEPART(ISO_WEEK, t.Fecha) BETWEEN :s1 AND :s2"
            params_h = {"s1": sem_ini, "s2": sem_fin}
        else:
            filtro_hist = (
                "DATEPART(ISO_WEEK, t.Fecha) >= :s1 "
                "OR DATEPART(ISO_WEEK, t.Fecha) <= :s2"
            )
            params_h = {"s1": sem_ini, "s2": sem_fin % 53}

        df_pesos = ejecutar_query(
            f"""SELECT
                m.Modulo AS modulo,
                v.Nombre_Variedad AS variedad,
                DATEPART(ISO_WEEK, t.Fecha) AS semana_iso,
                AVG(p.Peso_Promedio_Baya_g) / 1000.0 AS peso_baya_kg
            FROM Silver.Fact_Evaluacion_Pesos p WITH (NOLOCK)
            JOIN Silver.Dim_Tiempo t WITH (NOLOCK) ON p.ID_Tiempo = t.ID_Tiempo
            JOIN Silver.Dim_Variedad v WITH (NOLOCK) ON p.ID_Variedad = v.ID_Variedad
            JOIN Silver.Dim_Geografia g WITH (NOLOCK) ON p.ID_Geografia = g.ID_Geografia
            JOIN Silver.Dim_Modulo_Catalogo m WITH (NOLOCK) ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
            WHERE {filtro_hist}
            GROUP BY m.Modulo, v.Nombre_Variedad, DATEPART(ISO_WEEK, t.Fecha)""",
            params=params_h,
        )

    return df_conteo, df_plantas, df_pesos


def _semanas_en_anio(anio: int) -> int:
    """Retorna 52 o 53 según el calendario ISO del año dado.
    El 28 de diciembre siempre pertenece a la última semana ISO del año."""
    return dt.date(anio, 12, 28).isocalendar()[1]


def lookup_peso_baya(modulo: int, variedad: str, df_pesos: pd.DataFrame, sem_base: int, anio_base: int) -> dict[int, float]:
    """
        W2 usa el peso historico de la semana (sem_base + 2) ... etc.
    Esto NO es buscar datos futuros: el Excel referencia el historico del mismo
    numero de semana ISO de campanas anteriores almacenado en Fact_Evaluacion_Pesos.

    Cadena de fallback (de mayor a menor prioridad):
        1. Peso de sem_base+w para ese Modulo + Variedad.
        2. Peso de sem_base+w para CUALQUIER Modulo con esa Variedad.
        3. Peso mas reciente disponible para esa Variedad (sem <= sem_base).
        4. Hardcoded 2.89 g (promedio real histórico del Excel).
    """
    PESO_FALLBACK_KG = 0.00289  # 2.89 g - Promedio real del Excel (mediana 2.73g)
    max_sem = _semanas_en_anio(anio_base)

    subset_mv = df_pesos[(df_pesos["modulo"] == modulo) & (df_pesos["variedad"] == variedad)]
    subset_v  = df_pesos[df_pesos["variedad"] == variedad]

    pesos = {}
    for w in range(1, 7):
        # Semana objetivo para Wn (con rollover ISO correcto)
        target_sem = sem_base + w
        if target_sem > max_sem:
            target_sem -= max_sem

        # Prioridad 1: Modulo + Variedad, semana exacta
        val = subset_mv[subset_mv["semana_iso"] == target_sem]["peso_baya_kg"].mean()
        if pd.isna(val) or val == 0:
            # Prioridad 2: cualquier Modulo, semana exacta
            val = subset_v[subset_v["semana_iso"] == target_sem]["peso_baya_kg"].mean()
        if pd.isna(val) or val == 0:
            # Prioridad 3: Modulo + Variedad, semana mas reciente disponible (<= sem_base)
            recientes = subset_mv[subset_mv["semana_iso"] <= sem_base]
            if not recientes.empty:
                val = recientes.sort_values("semana_iso", ascending=False).iloc[0]["peso_baya_kg"]
        if pd.isna(val) or val == 0:
            # Prioridad 4: cualquier Variedad, cualquier semana disponible
            val = subset_v["peso_baya_kg"].mean()

        pesos[w] = PESO_FALLBACK_KG if (pd.isna(val) or val == 0) else float(val)

    return pesos


def calcular_pct_productivas(s1: float) -> list[float]:
    """
    Aplica el patrón temporal del Excel para % plantas productivas:
        S1 = input real medido en campo
        S2 = min(S1 + 2%,  100%)
        S3 = S2            (delta=0 reproduce S3=S2 del Excel)
        S4 = min(S3 - 3%,  100%)
        S5 = min(S4 + 1%,  100%)
        S6 = min(S5 + 1%,  100%)

    Si s1 es NaN (campo sin evaluar dentro de una fila existente de Peladas),
    se usa 0.0 — dato ausente no equivale a 100% productivo.
    Las unidades sin fila en Peladas se descartan antes de llegar aquí (ver ejecutar_proyeccion).
    """
    res = [0.0] * 6
    curr = s1 if not pd.isna(s1) else 0.0
    for w in range(1, 7):
        delta = DELTA_PRODUCTIVAS.get(w, 0.0)
        curr = min(1.0, max(0.0, curr + delta))
        res[w - 1] = curr
    return res


def kg_unidad_semana(
    conteo_estados: dict[int, float],
    matriz_cerrada: dict[str, list[float]],
    plantas: float,
    pesos_w: dict[int, float],
    pct_prod_w: list[float],
) -> list[float]:
    """
    Fórmula central del Excel para una unidad (Módulo×Turno×Válvula×Variedad).

    Por cada semana N (1-6):
        Kg_N = Σ_estados(conteo[e] × matriz[e][N] × plantas × peso_kg[N] × pct_prod[N])
               × DECAY_FACTOR[N]

    Args:
        conteo_estados: {id_estado: bayas_por_planta} — órganos/planta por estado fenológico.
        matriz_cerrada: {nombre_estado: [pct_W1, …, pct_W6]} — salida de cerrar_matriz().
        plantas:        total de plantas de la unidad (de Fact_Peladas).
        pesos_w:        {1..6: peso_baya_kg} — lookup histórico de Fact_Evaluacion_Pesos.
        pct_prod_w:     [pct_W1, …, pct_W6] — salida de calcular_pct_productivas().

    Returns:
        Lista de 6 floats con los kg proyectados por semana [W1, …, W6].
    """
    kg_semanas = [0.0] * 6
    for w_idx in range(6):
        w_num = w_idx + 1
        sum_estados = 0.0
        
        for id_est, cant in conteo_estados.items():
            estado_nom = ID_ESTADO_MAP.get(id_est)
            if estado_nom and estado_nom in matriz_cerrada:
                # Formula: Conteo * %Mad * Plantas * Peso * %Prod
                pct_mad = matriz_cerrada[estado_nom][w_idx]
                sum_estados += cant * pct_mad * plantas * pesos_w[w_num] * pct_prod_w[w_idx]
        
        kg_semanas[w_idx] = sum_estados * DECAY_FACTOR[w_num]
        
    return kg_semanas

# ── Proyección anterior almacenada en Fact_Proyecciones ──────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def extraer_proyeccion_anterior(
    id_tiempo_base: int,
    modulo: int | None = None,
    variedad: str | None = None,
    condicion: str | None = None,
    fundo: str | None = None,
) -> pd.DataFrame:
    """
    Recupera la proyección guardada filtrada por el contexto actual
    (Fundo/Mod/Var/Cond). Cualquiera puede ir vacío ('Todos').
    """
    from utils.db import ejecutar_query

    fecha_base = datetime.strptime(str(id_tiempo_base), "%Y%m%d")
    ids_semanas = [
        int((fecha_base + timedelta(days=(i + 1) * 7)).strftime("%Y%m%d"))
        for i in range(6)
    ]
    placeholders = ",".join(str(x) for x in ids_semanas)

    try:
        where_extra = ""
        params = {}
        if modulo:
            where_extra += " AND ID_Geografia IN (SELECT ID_Geografia FROM Silver.Dim_Geografia g JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo WHERE m.Modulo = :mod)"
            params["mod"] = str(modulo)
        if variedad:
            where_extra += " AND ID_Variedad = (SELECT ID_Variedad FROM Silver.Dim_Variedad WHERE Nombre_Variedad = :var)"
            params["var"] = variedad
        if fundo:
            # Trazabilidad por Fundo: Dim_Geografia → Dim_Fundo_Catalogo
            where_extra += (
                " AND ID_Geografia IN ("
                "SELECT g2.ID_Geografia FROM Silver.Dim_Geografia g2 "
                "JOIN Silver.Dim_Fundo_Catalogo fc2 ON g2.ID_Fundo_Catalogo = fc2.ID_Fundo_Catalogo "
                "WHERE fc2.Fundo = :fnd)"
            )
            params["fnd"] = fundo
        if condicion:
            partes = condicion.split(" - ")
            if len(partes) == 2:
                sus, cert = partes[0], partes[1]
                where_extra += (
                    " AND ID_Geografia IN ("
                    "SELECT cs.ID_Geografia FROM Silver.Fact_Cosecha_SAP cs "
                    "JOIN Silver.Dim_Condicion_Cultivo c ON cs.ID_Condicion_Cultivo = c.ID_Condicion "
                    "WHERE c.Sustrato = :sus AND c.Certificacion = :cert)"
                )
                params["sus"] = sus
                params["cert"] = cert

        sql = f"SELECT ID_Tiempo, SUM(Kg_Proyectados) AS kg_anterior FROM Silver.Fact_Proyecciones WITH (NOLOCK) WHERE ID_Tiempo IN ({placeholders}) AND ID_Escenario = 4 {where_extra} GROUP BY ID_Tiempo"

        df = ejecutar_query(sql, params=params)
        if df.empty:
            return pd.DataFrame(columns=["semana", "semana_label", "fecha_semana", "kg_anterior"])

        rows = []
        for i, id_t in enumerate(ids_semanas):
            fecha_sem = fecha_base + timedelta(weeks=i + 1)
            kg = df.loc[df["ID_Tiempo"] == id_t, "kg_anterior"].sum() if id_t in df["ID_Tiempo"].values else 0.0
            rows.append({
                "semana": i + 1,
                "semana_label": f"W{i+1} ({fecha_sem.strftime('%d/%m')})",
                "fecha_semana": fecha_sem.date(),
                "kg_anterior": float(kg),
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["semana", "semana_label", "fecha_semana", "kg_anterior"])


# ── Función pública principal ─────────────────────────────────────────────────

def ejecutar_proyeccion(
    id_tiempo: int,
    matriz_inputs: dict[str, dict[int, float | None]],
    margen_pesimista: float,
    margen_optimista: float,
    modulo: int | None = None,
    variedad: str | None = None,
    condicion: str | None = None,
    fundo: str | None = None,
) -> dict:
    """
    Motor central de proyecciones SIX-WEEK.
    Calcula 6 semanas a futuro partiendo de una fecha de evaluación.

    Filtros opcionales (todos pueden combinarse libremente):
        modulo:    int — número del módulo a proyectar.
        variedad:  str — nombre de la variedad.
        condicion: str — 'Sustrato - Certificación' (e.g. 'Suelo - Organico').
        fundo:     str — nombre del fundo (Dim_Fundo_Catalogo.Fundo).
    """
    if matriz_inputs is None:
        matriz_inputs = MATRIZ_INPUTS_DEFAULT

    # 1. Extraer datos del DWH
    df_conteo, df_plantas, df_pesos = extraer_datos_granulares(
        id_tiempo, modulo, variedad, condicion, fundo
    )
    
    if df_conteo.empty:
        return {"df_semanal": pd.DataFrame(), "df_detalle": pd.DataFrame(), "kpis": {}}
    
    # Si faltan plantas o pesos, permitimos continuar (se usarán fallbacks unitarios más adelante)
    if df_plantas.empty:
        st.warning("⚠️ No se encontraron datos de plantas (Peladas). Usando Ha estándar (1500 pl).")
    if df_pesos.empty:
        st.warning("⚠️ No se encontraron pesos históricos para este rango de semanas. Usando default (3.5g).")

    # 2. Cerrar la matriz de % con 1 - Σ
    matriz_cerrada = cerrar_matriz(matriz_inputs)
    
    # 3. Determinar semana base y año (para rollover ISO correcto)
    fecha_base = datetime.strptime(str(id_tiempo), "%Y%m%d")
    sem_base = fecha_base.isocalendar()[1]
    anio_base = fecha_base.year
    
    # 4. Procesar por unidad (Módulo, Turno, Válvula, Variedad)
    # Agrupamos por la unidad operativa. Fundo y Condicion son atributos derivados
    # del grupo (vienen del JOIN, son únicos por unidad), los recogemos del primer
    # row del grupo.
    unidades = df_conteo.groupby(["modulo", "turno", "valvula", "variedad"])

    filas_detalle = []

    # Contadores para KPIs avanzados
    total_plantas_proy = 0
    unidades_con_datos = 0

    for (mod, tur, valv, var), group in unidades:
        # Trazabilidad: Fundo, Condicion y Certificacion son únicos por
        # (mod, turno, valv, var) — vienen del JOIN a Dim_Condicion_Cultivo.
        # Certificacion se guarda aparte (sin derivar del string Condicion)
        # para clasificar Orgánico vs Convencional sin heurísticas frágiles.
        fundo_unidad = str(group["fundo"].iloc[0]) if "fundo" in group.columns else "—"
        condicion_unidad = (
            str(group["condicion"].iloc[0]) if "condicion" in group.columns else "Sin condición"
        )
        certificacion_unidad = (
            str(group["certificacion"].iloc[0]) if "certificacion" in group.columns
            else "Sin certificación"
        )
        # puntos = COUNT(DISTINCT Punto) de la query. Si la columna Punto está NULL
        # en la DB, COUNT devuelve 0 y se trata la unidad como 1 punto virtual.
        # Asunción del Excel: cada punto representa 10 plantas muestreadas.
        puntos_val = group["puntos"].max()
        if puntos_val == 0:
            puntos_val = 1

        # Conteos por estado normalizados a bayas/planta (= total_organos / puntos×PLANTAS_POR_PUNTO)
        conteo_estados = {}
        for _, row in group.iterrows():
            conteo_estados[row["id_estado"]] = row["total_organos"] / (puntos_val * PLANTAS_POR_PUNTO)
        
        # Datos de plantas y prod inicial
        p_row = df_plantas[
            (df_plantas["modulo"] == mod) & 
            (df_plantas["turno"] == tur) & 
            (df_plantas["valvula"] == valv)
        ]

        if p_row.empty:
            num_plantas_total = 1500.0
            pct_prod_s1 = 0.80 # Fallback 80% si no hay censo
        else:
            # Intentar usar plantas_sampleadas (campo específico de Peladas)
            val_p = p_row.iloc[0].get("plantas_sampleadas", p_row.iloc[0].get("Plantas_Productivas", 1500.0))
            num_plantas_total = float(val_p) if pd.notna(val_p) and val_p > 0 else 1500.0
            
            val_pct = p_row.iloc[0].get("pct_productivas_s1", 0.0)
            pct_prod_s1 = float(val_pct) if pd.notna(val_pct) else 0.0
            unidades_con_datos += 1
        
        total_plantas_proy += num_plantas_total
        
        # Lookup pesos (W1-W6)
        pesos_w = lookup_peso_baya(mod, var, df_pesos, sem_base, anio_base)
        
        # Calcular productivas (W1-W6)
        prod_w = calcular_pct_productivas(pct_prod_s1)
        
        # Calcular kg por semana (Formula central)
        # Nota: kg_unidad_semana ahora recibe conteo_estados (bayas/planta por estado)
        kg_semanas = kg_unidad_semana(conteo_estados, matriz_cerrada, num_plantas_total, pesos_w, prod_w)
        
        # Guardar resultados
        for i, kg in enumerate(kg_semanas):
            w_num = i + 1
            fecha_sem = fecha_base + timedelta(days=w_num * 7) # Sincronizado: siempre +7 días
            id_t_sem = int(fecha_sem.strftime("%Y%m%d"))
            filas_detalle.append({
                "fundo": fundo_unidad,
                "condicion": condicion_unidad,
                "certificacion": certificacion_unidad,
                "modulo": mod,
                "turno": tur,
                "valvula": valv,
                "variedad": var,
                "semana": w_num,
                "id_tiempo_proy": id_t_sem,
                "semana_label": f"W{w_num} ({fecha_sem.strftime('%d/%m')})",
                "fecha_semana": fecha_sem.date(),
                "kg_base": round(kg, 2),
                "kg_pesimista": round(kg * margen_pesimista, 2),
                "kg_optimista": round(kg * margen_optimista, 2),
            })


    df_detalle = pd.DataFrame(filas_detalle)
    if df_detalle.empty:
        return {"df_semanal": pd.DataFrame(), "df_detalle": pd.DataFrame(), "kpis": {}}

    # 5. Agregar a nivel semana
    df_semanal = (
        df_detalle.groupby(["semana", "semana_label", "fecha_semana"])
        .agg(kg_base=("kg_base", "sum"), kg_pesimista=("kg_pesimista", "sum"), kg_optimista=("kg_optimista", "sum"))
        .reset_index()
        .sort_values("semana")
    )

    # 6. Calcular KPIs
    total_base = df_semanal["kg_base"].sum()
    total_opt = df_semanal["kg_optimista"].sum()
    total_pes = df_semanal["kg_pesimista"].sum()
    
    try:
        variedad_top = df_detalle.groupby("variedad")["kg_base"].sum().idxmax() if total_base > 0 else "—"
    except (ValueError, KeyError):
        variedad_top = "—"

    return {
        "df_semanal": df_semanal,
        "df_detalle": df_detalle,
        "kpis": {
            "total_base": total_base,
            "total_opt": total_opt,
            "total_pes": total_pes,
            "variedad_top": variedad_top,
            "total_plantas": total_plantas_proy,
            "kg_por_planta": total_base / total_plantas_proy if total_plantas_proy > 0 else 0,
            "unidades_cubiertas": unidades_con_datos,
            "unidades_totales": len(unidades)
        },
    }


# ── Persistencia genérica en Config.Parametros_Pipeline ─────────────────────

import json as _json

_CLAVE_MATRIZ   = "PROY_SIXWEEK_MATRIZ_INPUTS"
_MODULO_PARAM   = "sixweek"
_TIPO_DATO_PARAM = "JSON"


def _persist_param_json(clave: str, payload_dict: dict, descripcion: str) -> bool:
    """
    Helper genérico que persiste un dict como JSON en Config.Parametros_Pipeline
    usando MERGE idempotente. Centraliza el patrón antes duplicado.
    """
    from utils.db import ejecutar_comando

    try:
        ejecutar_comando(
            """
            MERGE Config.Parametros_Pipeline AS dest
            USING (SELECT :clave AS Clave) AS src
              ON dest.Clave = src.Clave
            WHEN MATCHED THEN UPDATE
                SET Valor = :valor,
                    Descripcion = :desc,
                    Modulo = :mod,
                    Tipo_Dato = :tipo
            WHEN NOT MATCHED THEN
                INSERT (Clave, Valor, Descripcion, Modulo, Tipo_Dato)
                VALUES (:clave, :valor, :desc, :mod, :tipo);
            """,
            params={
                "clave": clave,
                "valor": _json.dumps(payload_dict, ensure_ascii=False),
                "desc": descripcion,
                "mod": _MODULO_PARAM,
                "tipo": _TIPO_DATO_PARAM,
            },
        )
        return True
    except Exception as exc:
        st.error(f"Error guardando '{clave}': {exc}")
        return False


def _leer_param_json(clave: str) -> dict | None:
    """Recupera un parámetro JSON. Devuelve None si no existe o es ilegible."""
    from utils.db import ejecutar_query

    try:
        df = ejecutar_query(
            "SELECT Valor FROM Config.Parametros_Pipeline WHERE Clave = :c",
            params={"c": clave},
        )
        if df.empty or not df.iloc[0]["Valor"]:
            return None
        return _json.loads(df.iloc[0]["Valor"])
    except Exception:
        return None


# ── Matriz de inputs ─────────────────────────────────────────────────────────

def guardar_matriz_inputs(matriz: dict[str, dict[int, float | None]]) -> bool:
    """Persiste la matriz de % maduración (semanas serializadas como str)."""
    serializable = {
        est: {str(w): v for w, v in semanas.items()}
        for est, semanas in matriz.items()
    }
    return _persist_param_json(
        _CLAVE_MATRIZ, serializable,
        "Matriz de inputs % maduración Six-Week (editada por usuario)",
    )


def cargar_matriz_inputs() -> dict[str, dict[int, float | None]] | None:
    """Recupera la última matriz guardada. None si no existe."""
    data = _leer_param_json(_CLAVE_MATRIZ)
    if not data:
        return None
    return {
        est: {int(w): (None if v is None else float(v)) for w, v in semanas.items()}
        for est, semanas in data.items()
    }


# ── Márgenes optimista/pesimista ─────────────────────────────────────────────
# DEPRECADO (2026-05-07): los márgenes ya NO se exponen en la UI ni se persisten.
# Los valores operativos se mantienen como constantes MARGEN_PESIMISTA y
# MARGEN_OPTIMISTA al inicio del módulo (defaults del Excel: 0.9906 / 1.0107).
#
# Se conservan las firmas como wrappers a las constantes para no romper
# cualquier import externo legacy. NO USAR EN CÓDIGO NUEVO.

import warnings as _warnings


def guardar_margenes(pesimista: float, optimista: float) -> bool:
    """DEPRECADO. Los márgenes son constantes — esta función es no-op."""
    _warnings.warn(
        "guardar_margenes está deprecado: los márgenes ya no se persisten. "
        "Usa las constantes MARGEN_PESIMISTA / MARGEN_OPTIMISTA.",
        DeprecationWarning, stacklevel=2,
    )
    return False


def cargar_margenes() -> tuple[float, float]:
    """DEPRECADO. Devuelve siempre los defaults (constantes del módulo)."""
    _warnings.warn(
        "cargar_margenes está deprecado: usa MARGEN_PESIMISTA / MARGEN_OPTIMISTA "
        "directamente.",
        DeprecationWarning, stacklevel=2,
    )
    return MARGEN_PESIMISTA, MARGEN_OPTIMISTA


# ── Persistencia: resultados a Silver.Fact_Proyecciones ──────────────────────

# ID del escenario "Six-Week Manual UI" — se reutiliza el mismo escenario base.
_ID_ESCENARIO_SIXWEEK = 4
_ID_WORKFLOW_BORRADOR = 1
_VERSION_MODELO = "sixweek-manual-ui-v1"


def _resolver_id_geografia(modulo: int, turno: int, valvula: int) -> int | None:
    """Lookup del ID_Geografia para (Módulo, Turno, Válvula)."""
    from utils.db import ejecutar_query

    df = ejecutar_query(
        """
        SELECT TOP 1 g.ID_Geografia
        FROM Silver.Dim_Geografia g
        JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
        JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
        JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
        WHERE CAST(m.Modulo AS NVARCHAR) = :m 
          AND CAST(t.Turno AS NVARCHAR) = :t 
          AND CAST(v.Valvula AS NVARCHAR) = :v
        """,
        params={"m": str(modulo), "t": str(turno), "v": str(valvula)},
    )

    return int(df.iloc[0]["ID_Geografia"]) if not df.empty else None


def _resolver_id_variedad(nombre: str) -> int | None:
    from utils.db import ejecutar_query

    df = ejecutar_query(
        "SELECT TOP 1 ID_Variedad FROM Silver.Dim_Variedad WHERE Nombre_Variedad = :n",
        params={"n": nombre},
    )
    return int(df.iloc[0]["ID_Variedad"]) if not df.empty else None


def _id_tiempo_para_fecha(fecha: dt.date) -> int | None:
    """Resuelve ID_Tiempo a partir de una fecha, creando si no existe sería un cambio
    en la dimensión: aquí solo lookup. Si no hay match, retorna None."""
    from utils.db import ejecutar_query

    df = ejecutar_query(
        "SELECT TOP 1 ID_Tiempo FROM Silver.Dim_Tiempo WHERE Fecha = :f",
        params={"f": fecha},
    )
    return int(df.iloc[0]["ID_Tiempo"]) if not df.empty else None


def guardar_proyeccion(
    df_detalle: pd.DataFrame,
    id_tiempo_base: int,
    margen_pesimista: float = MARGEN_PESIMISTA,
    margen_optimista: float = MARGEN_OPTIMISTA,
) -> dict:
    """
    Persiste df_detalle (granularidad Mod×Turno×Válvula×Variedad×Semana) en
    Silver.Fact_Proyecciones usando MERGE para idempotencia.

    Cada fila en df_detalle representa Kg proyectados para una semana futura,
    no para id_tiempo_base. Se mapea fecha_semana → ID_Tiempo de Dim_Tiempo.

    Retorna {"insertados": n, "saltados": n, "errores": [str]}.
    """
    from utils.db import ejecutar_comando

    if df_detalle.empty:
        return {"insertados": 0, "saltados": 0, "errores": ["DataFrame vacío"]}

    # Cache de lookups para evitar re-consultas
    cache_geo: dict[tuple, int | None] = {}
    cache_var: dict[str, int | None] = {}
    cache_tiempo: dict[dt.date, int | None] = {}

    insertados = 0
    saltados = 0
    errores: list[str] = []
    fecha_sistema = pd.Timestamp.now()
    fecha_cutoff = datetime.strptime(str(id_tiempo_base), "%Y%m%d").date()

    for _, row in df_detalle.iterrows():
        # Usar str para los catálogos para evitar errores con 'SIN_VALVULA'
        clave_geo = (str(row["modulo"]), str(row["turno"]), str(row["valvula"]))
        if clave_geo not in cache_geo:
            cache_geo[clave_geo] = _resolver_id_geografia(*clave_geo)
        id_geo = cache_geo[clave_geo]

        var_nombre = str(row["variedad"])
        if var_nombre not in cache_var:
            cache_var[var_nombre] = _resolver_id_variedad(var_nombre)
        id_var = cache_var[var_nombre]

        fecha_sem = row["fecha_semana"]
        if hasattr(fecha_sem, "date"):
            fecha_sem = fecha_sem.date()
        if fecha_sem not in cache_tiempo:
            cache_tiempo[fecha_sem] = _id_tiempo_para_fecha(fecha_sem)
        id_tiempo_sem = cache_tiempo[fecha_sem]

        if id_geo is None or id_var is None or id_tiempo_sem is None:
            saltados += 1
            continue

        kg_base = float(row["kg_base"])


        try:
            ejecutar_comando(
                """
                MERGE Silver.Fact_Proyecciones AS dest
                USING (SELECT
                        :id_t AS ID_Tiempo, :id_g AS ID_Geografia,
                        :id_v AS ID_Variedad, :id_e AS ID_Escenario
                    ) AS src
                  ON dest.ID_Tiempo = src.ID_Tiempo
                 AND dest.ID_Geografia = src.ID_Geografia
                 AND dest.ID_Variedad = src.ID_Variedad
                 AND dest.ID_Escenario = src.ID_Escenario
                WHEN MATCHED THEN UPDATE SET
                    Kg_Proyectados = :kgb,
                    Kg_Pesimista = :kgp,
                    Kg_Optimista = :kgo,
                    Fecha_Cutoff = :fc,
                    Fecha_Evento = :fe,
                    Fecha_Sistema = :fs,
                    Version_Modelo = :ver,
                    Estado_DQ = 'OK'
                WHEN NOT MATCHED THEN INSERT (
                    ID_Tiempo, ID_Geografia, ID_Variedad, ID_Escenario,
                    ID_Estado_Workflow, Kg_Proyectados, Kg_Pesimista, Kg_Optimista,
                    Fecha_Cutoff, Fecha_Evento, Fecha_Sistema,
                    Version_Modelo, Flag_Override, Estado_DQ
                ) VALUES (
                    :id_t, :id_g, :id_v, :id_e,
                    :id_wf, :kgb, :kgp, :kgo,
                    :fc, :fe, :fs,
                    :ver, 0, 'OK'
                );
                """,
                params={
                    "id_t": id_tiempo_sem,
                    "id_g": id_geo,
                    "id_v": id_var,
                    "id_e": _ID_ESCENARIO_SIXWEEK,
                    "id_wf": _ID_WORKFLOW_BORRADOR,
                    "kgb": kg_base,
                    "kgp": float(row["kg_pesimista"]),
                    "kgo": float(row["kg_optimista"]),
                    "fc": fecha_cutoff,
                    "fe": fecha_sem,
                    "fs": fecha_sistema,
                    "ver": _VERSION_MODELO,
                },
            )
            insertados += 1
        except Exception as exc:
            errores.append(f"Mod={clave_geo} Var={var_nombre} Sem={fecha_sem}: {exc}")
            saltados += 1

    return {"insertados": insertados, "saltados": saltados, "errores": errores}

