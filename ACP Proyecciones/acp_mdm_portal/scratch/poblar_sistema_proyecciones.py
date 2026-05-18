"""
poblar_sistema_proyecciones.py — Poblamiento masivo para validación Six-Week
=============================================================================
Genera +1000 registros/semana en Conteo, Peladas, Pesos, Cosecha SAP y Proyecciones.
Rango: Feb-Jun 2026 (evaluaciones), Ene-Jun 2026 (cosecha real).
Usa geografías, variedades y catálogos existentes para integridad referencial.
"""
import sys, os, random, math
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import ejecutar_query, obtener_engine
from sqlalchemy import text

# ── Configuración ──────────────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

# Variedades principales para la prueba (IDs reales del DWH)
VARIEDADES = [
    (27, "Sekoya Pop"),
    (28, "Sekoya Beauty"),
    (30, "Ventura"),
    (32, "Atlas"),
    (34, "Clockwork"),
]

# Módulos operativos: 1-8
MODULOS_ACTIVOS = [1, 2, 3, 4, 5, 6, 7, 8]

# Estados fenológicos (IDs reales)
ESTADOS = [3, 4, 5, 6, 7, 8, 9]  # pequena, verde, f1, f2, crema, madura, cosechable

# Campaña 2026
ID_CAMPANA = 3

# Semanas de evaluación: un lunes por semana, Feb-Jun 2026
def generar_fechas_semanales(inicio, fin):
    """Genera un lunes por semana ISO en el rango."""
    fechas = []
    d = inicio
    while d <= fin:
        # Avanzar al lunes
        d_lunes = d - timedelta(days=d.weekday())
        if d_lunes >= inicio and d_lunes <= fin and d_lunes not in fechas:
            fechas.append(d_lunes)
        d += timedelta(days=7)
    return sorted(set(fechas))

FECHAS_EVAL = generar_fechas_semanales(date(2026, 2, 2), date(2026, 6, 22))
FECHAS_COSECHA = generar_fechas_semanales(date(2026, 1, 5), date(2026, 6, 22))

def id_tiempo(d):
    return int(d.strftime("%Y%m%d"))

# ── Cargar geografías reales ───────────────────────────────────────────────────
print("Cargando catálogos...")
df_geo = ejecutar_query("""
    SELECT g.ID_Geografia, m.Modulo, t.Turno, v.Valvula
    FROM Silver.Dim_Geografia g
    JOIN Silver.Dim_Modulo_Catalogo m ON g.ID_Modulo_Catalogo = m.ID_Modulo_Catalogo
    JOIN Silver.Dim_Turno_Catalogo t ON g.ID_Turno_Catalogo = t.ID_Turno_Catalogo
    JOIN Silver.Dim_Valvula_Catalogo v ON g.ID_Valvula_Catalogo = v.ID_Valvula_Catalogo
    WHERE g.Es_Vigente = 1 AND m.Modulo BETWEEN 1 AND 8 AND t.Turno > 0
""")
print(f"  Geografías disponibles: {len(df_geo)}")

# Agrupar geografías por módulo para distribución uniforme
geo_por_modulo = {}
for mod in MODULOS_ACTIVOS:
    sub = df_geo[df_geo["Modulo"] == mod]
    if not sub.empty:
        geo_por_modulo[mod] = sub.to_dict(orient="records")

print(f"  Módulos con geografía: {list(geo_por_modulo.keys())}")

# ── Curvas de maduración realistas (S-curve por semana del año) ────────────────
def curva_maduracion(sem_iso):
    """Distribución de estados fenológicos según semana ISO (curva S)."""
    # Simula un ciclo: Ene=pre-cosecha, Feb-Abr=cosecha temprana, May-Jun=cosecha plena
    t = max(0, min(1, (sem_iso - 5) / 20))  # normalizado 0..1
    return {
        3: max(0, 0.25 * (1 - t)**2),         # pequena: decrece
        4: max(0, 0.20 * (1 - t)),             # verde: decrece
        5: max(0, 0.15 * math.sin(math.pi * t)),  # fase_1: pico medio
        6: max(0, 0.15 * math.sin(math.pi * t * 0.8)),  # fase_2
        7: max(0, 0.10 + 0.15 * t),            # crema: crece
        8: max(0, 0.05 + 0.20 * t),            # madura: crece
        9: max(0, 0.02 + 0.25 * t**1.5),       # cosechable: crece rápido
    }

# ── Generador: Fact_Conteo_Fenologico ──────────────────────────────────────────
def generar_conteo(fechas):
    """Genera +1000 registros por semana con distribución realista."""
    rows = []
    for fecha in fechas:
        idt = id_tiempo(fecha)
        sem_iso = fecha.isocalendar()[1]
        dist = curva_maduracion(sem_iso)

        for mod, geos in geo_por_modulo.items():
            # Seleccionar 3-5 geografías por módulo
            n_geos = min(len(geos), random.randint(3, 5))
            selected_geos = random.sample(geos, n_geos)

            for geo in selected_geos:
                for id_var, _ in VARIEDADES:
                    for id_estado, pct in dist.items():
                        if pct < 0.01:
                            continue
                        # 1-3 puntos de muestreo
                        n_puntos = random.randint(1, 3)
                        for punto in range(1, n_puntos + 1):
                            cant = max(1, int(np.random.poisson(pct * 50) + np.random.normal(0, 3)))
                            rows.append({
                                "ID_Geografia": geo["ID_Geografia"],
                                "ID_Tiempo": idt,
                                "ID_Variedad": id_var,
                                "ID_Personal": -1,
                                "ID_Estado_Fenologico": id_estado,
                                "Cantidad_Organos": cant,
                                "Fecha_Evento": datetime.combine(fecha, datetime.min.time()),
                                "Fecha_Sistema": datetime.now(),
                                "Estado_DQ": "OK",
                                "Punto": punto,
                                "ID_Campana": ID_CAMPANA,
                                "Fecha_Registro": datetime.now(),
                            })
    return pd.DataFrame(rows)

# ── Generador: Fact_Peladas ────────────────────────────────────────────────────
def generar_peladas(fechas):
    """Genera censo de plantas por unidad geográfica."""
    rows = []
    for fecha in fechas:
        idt = id_tiempo(fecha)
        for mod, geos in geo_por_modulo.items():
            n_geos = min(len(geos), random.randint(3, 5))
            selected_geos = random.sample(geos, n_geos)
            for geo in selected_geos:
                for id_var, _ in VARIEDADES:
                    prod = random.randint(120, 180)
                    no_prod = random.randint(5, 25)
                    rows.append({
                        "ID_Geografia": geo["ID_Geografia"],
                        "ID_Tiempo": idt,
                        "ID_Variedad": id_var,
                        "ID_Personal": -1,
                        "Punto": random.randint(1, 5),
                        "Botones_Florales": random.randint(0, 15),
                        "Flores": random.randint(0, 20),
                        "Bayas_Pequenas": random.randint(5, 40),
                        "Bayas_Grandes": random.randint(3, 25),
                        "Fase_1": random.randint(2, 15),
                        "Fase_2": random.randint(2, 12),
                        "Bayas_Cremas": random.randint(1, 10),
                        "Bayas_Maduras": random.randint(1, 8),
                        "Bayas_Cosechables": random.randint(0, 5),
                        "Plantas_Productivas": prod,
                        "Plantas_No_Productivas": no_prod,
                        "Muestras": random.randint(3, 10),
                        "Fecha_Evento": datetime.combine(fecha, datetime.min.time()),
                        "Fecha_Sistema": datetime.now(),
                        "Estado_DQ": "OK",
                        "ID_Campana": ID_CAMPANA,
                    })
    return pd.DataFrame(rows)

# ── Generador: Fact_Evaluacion_Pesos ───────────────────────────────────────────
def generar_pesos(fechas):
    """Genera pesos de baya por módulo/variedad/semana."""
    rows = []
    for fecha in fechas:
        idt = id_tiempo(fecha)
        for mod, geos in geo_por_modulo.items():
            geo = random.choice(geos)
            for id_var, nombre_var in VARIEDADES:
                # Peso promedio: 2.5-4.5g, varía por variedad
                base = 2.5 + hash(nombre_var) % 20 / 10.0
                peso = max(1.5, base + np.random.normal(0, 0.3))
                rows.append({
                    "ID_Geografia": geo["ID_Geografia"],
                    "ID_Tiempo": idt,
                    "ID_Variedad": id_var,
                    "ID_Personal": -1,
                    "Peso_Promedio_Baya_g": round(peso, 2),
                    "Cantidad_Bayas_Muestra": random.randint(50, 200),
                    "Peso_Proyectado_Baya_g": round(peso * 1.05, 2),
                    "Fecha_Evento": datetime.combine(fecha, datetime.min.time()),
                    "Fecha_Sistema": datetime.now(),
                    "Estado_DQ": "OK",
                    "ID_Campana": ID_CAMPANA,
                })
    return pd.DataFrame(rows)

# ── Generador: Fact_Cosecha_SAP ────────────────────────────────────────────────
def generar_cosecha_sap(fechas):
    """Genera cosecha real por módulo/variedad con curva estacional."""
    rows = []
    for fecha in fechas:
        idt = id_tiempo(fecha)
        sem_iso = fecha.isocalendar()[1]
        # Curva de producción estacional
        factor = max(0.2, math.sin(math.pi * (sem_iso - 1) / 26))
        for mod, geos in geo_por_modulo.items():
            geo = random.choice(geos)
            for id_var, nombre_var in VARIEDADES:
                kg_base = 500 + hash(nombre_var) % 300
                kg_bruto = max(50, kg_base * factor + np.random.normal(0, 50))
                kg_neto = kg_bruto * random.uniform(0.88, 0.95)
                jabas = max(1, int(kg_bruto / 12))
                rows.append({
                    "ID_Geografia": geo["ID_Geografia"],
                    "ID_Tiempo": idt,
                    "ID_Variedad": id_var,
                    "ID_Condicion_Cultivo": 1,
                    "Kg_Brutos": round(kg_bruto, 2),
                    "Kg_Neto_MP": round(kg_neto, 2),
                    "Cantidad_Jabas": jabas,
                    "Lote": f"L{fecha.strftime('%Y%m%d')}-M{mod}",
                    "Almacen": "ALM-01",
                    "Doc_Remision": f"DR-{idt}-{mod}",
                    "Codigo_Cliente": "CLI-ACP-001",
                    "Responsable": "Sistema Prueba",
                    "Descripcion_Material": nombre_var,
                    "Codigo_SAP_Material": f"SAP-{id_var:04d}",
                    "Fecha_Recepcion": datetime.combine(fecha + timedelta(days=1), datetime.min.time()),
                    "Fecha_Evento": datetime.combine(fecha, datetime.min.time()),
                    "Fecha_Sistema": datetime.now(),
                    "Estado_DQ": "OK",
                    "ID_Campana": ID_CAMPANA,
                })
    return pd.DataFrame(rows)

# ── Generador: Fact_Proyecciones ───────────────────────────────────────────────
def generar_proyecciones(fechas):
    """Genera proyecciones anteriores (Escenario 4 = Six-Week) para comparación."""
    rows = []
    for fecha in fechas:
        for w in range(1, 7):
            fecha_proy = fecha + timedelta(weeks=w)
            idt_proy = id_tiempo(fecha_proy)
            for mod, geos in geo_por_modulo.items():
                geo = random.choice(geos)
                for id_var, nombre_var in VARIEDADES:
                    kg_base = 200 + hash(nombre_var) % 200
                    decay = [1.0, 1.0, 0.8, 0.8, 0.8, 0.8][w-1]
                    kg = max(10, kg_base * decay + np.random.normal(0, 30))
                    rows.append({
                        "ID_Geografia": geo["ID_Geografia"],
                        "ID_Tiempo": idt_proy,
                        "ID_Variedad": id_var,
                        "ID_Escenario": 4,
                        "ID_Estado_Workflow": 3,
                        "Kg_Proyectados": round(kg, 2),
                        "MAPE": round(random.uniform(5, 20), 2),
                        "Version_Modelo": "SixWeek-v1.0-test",
                        "Fecha_Cutoff": datetime.combine(fecha, datetime.min.time()),
                        "ID_Version_Datos": 1,
                        "Flag_Override": False,
                        "Motivo_Override": None,
                        "Fecha_Evento": datetime.combine(fecha, datetime.min.time()),
                        "Fecha_Sistema": datetime.now(),
                        "Estado_DQ": "OK",
                        "ID_Campana": ID_CAMPANA,
                        "Kg_Pesimista": round(kg * 0.9906, 2),
                        "Kg_Optimista": round(kg * 1.0107, 2),
                        "Pct_Maduracion": round(random.uniform(0.3, 0.9), 3),
                        "Pct_Productivas": round(random.uniform(0.85, 0.98), 3),
                    })
    return pd.DataFrame(rows)

# -- Insercion masiva -------------------------------------------------------
def insertar_df(df, tabla, desc):
    """Inserta un DataFrame en SQL Server usando pyodbc raw con fast_executemany."""
    if df.empty:
        print(f"  [WARN] {desc}: DataFrame vacio, saltando.")
        return
    engine = obtener_engine()
    cols = list(df.columns)
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join([f"[{c}]" for c in cols])
    sql = f"INSERT INTO Silver.[{tabla}] ({col_names}) VALUES ({placeholders})"

    # Convertir a lista de tuplas
    data = [tuple(row) for row in df.itertuples(index=False, name=None)]

    print(f"  [..] {desc}: Insertando {len(data)} filas en Silver.{tabla}...")
    raw_conn = engine.raw_connection()
    try:
        cursor = raw_conn.cursor()
        cursor.fast_executemany = True
        # Insertar en lotes de 1000
        batch_size = 1000
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany(sql, batch)
        raw_conn.commit()
        print(f"  [OK] {desc}: {len(data)} filas insertadas.")
    except Exception as e:
        raw_conn.rollback()
        print(f"  [ERROR] {desc}: {e}")
        raise
    finally:
        raw_conn.close()

# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("POBLAMIENTO MASIVO - Proyecciones Six-Week")
    print(f"Fechas evaluacion: {FECHAS_EVAL[0]} -> {FECHAS_EVAL[-1]} ({len(FECHAS_EVAL)} semanas)")
    print(f"Fechas cosecha:    {FECHAS_COSECHA[0]} -> {FECHAS_COSECHA[-1]} ({len(FECHAS_COSECHA)} semanas)")
    print(f"Variedades:        {[v[1] for v in VARIEDADES]}")
    print(f"Modulos:           {MODULOS_ACTIVOS}")
    print("=" * 70)

    # 1. Conteo Fenológico
    print("\n[1/5] Generando Fact_Conteo_Fenologico...")
    df_conteo = generar_conteo(FECHAS_EVAL)
    # Eliminar duplicados exactos
    df_conteo = df_conteo.drop_duplicates(
        subset=["ID_Geografia", "ID_Tiempo", "ID_Variedad", "ID_Estado_Fenologico", "Punto"],
        keep="first"
    )
    print(f"  Registros unicos generados: {len(df_conteo)}")
    print(f"  Registros por semana (promedio): {len(df_conteo) // len(FECHAS_EVAL)}")
    insertar_df(df_conteo, "Fact_Conteo_Fenologico", "Conteo Fenologico")

    # 2. Peladas (Censo)
    print("\n[2/5] Generando Fact_Peladas...")
    df_peladas = generar_peladas(FECHAS_EVAL)
    df_peladas = df_peladas.drop_duplicates(
        subset=["ID_Geografia", "ID_Tiempo", "ID_Variedad", "Punto"],
        keep="first"
    )
    print(f"  Registros unicos generados: {len(df_peladas)}")
    insertar_df(df_peladas, "Fact_Peladas", "Peladas (Censo)")

    # 3. Pesos
    print("\n[3/5] Generando Fact_Evaluacion_Pesos...")
    df_pesos = generar_pesos(FECHAS_EVAL)
    df_pesos = df_pesos.drop_duplicates(
        subset=["ID_Geografia", "ID_Tiempo", "ID_Variedad"],
        keep="first"
    )
    print(f"  Registros unicos generados: {len(df_pesos)}")
    insertar_df(df_pesos, "Fact_Evaluacion_Pesos", "Pesos Baya")

    # 4. Cosecha SAP
    print("\n[4/5] Generando Fact_Cosecha_SAP...")
    df_cosecha = generar_cosecha_sap(FECHAS_COSECHA)
    df_cosecha = df_cosecha.drop_duplicates(
        subset=["ID_Geografia", "ID_Tiempo", "ID_Variedad"],
        keep="first"
    )
    print(f"  Registros unicos generados: {len(df_cosecha)}")
    insertar_df(df_cosecha, "Fact_Cosecha_SAP", "Cosecha SAP")

    # 5. Proyecciones anteriores (solo primeras 8 semanas de evaluación)
    print("\n[5/5] Generando Fact_Proyecciones...")
    fechas_proy = FECHAS_EVAL[:8]
    df_proy = generar_proyecciones(fechas_proy)
    df_proy = df_proy.drop_duplicates(
        subset=["ID_Geografia", "ID_Tiempo", "ID_Variedad", "ID_Escenario"],
        keep="first"
    )
    print(f"  Registros unicos generados: {len(df_proy)}")
    insertar_df(df_proy, "Fact_Proyecciones", "Proyecciones Anteriores")

    # ── Resumen Final ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN DE POBLAMIENTO")
    print("=" * 70)
    for tbl, cnt in [
        ("Fact_Conteo_Fenologico", len(df_conteo)),
        ("Fact_Peladas", len(df_peladas)),
        ("Fact_Evaluacion_Pesos", len(df_pesos)),
        ("Fact_Cosecha_SAP", len(df_cosecha)),
        ("Fact_Proyecciones", len(df_proy)),
    ]:
        print(f"  {tbl:40s} → {cnt:>6,} filas")
    total = len(df_conteo) + len(df_peladas) + len(df_pesos) + len(df_cosecha) + len(df_proy)
    print(f"  {'TOTAL':40s} -> {total:>6,} filas")
    print("=" * 70)
    print("[OK] Poblamiento completado exitosamente.")
