"""
Modelo de Tasa de Crecimiento v2 - Arándanos
Dashboard interactivo con Plotly. Ejecutar y abrir el HTML generado.

Mejoras vs v1:
  - Visualizaciones interactivas (hover, zoom, filtros)
  - Carga optimizada con tipos de datos mínimos
  - HistGradientBoostingRegressor (10x más rápido que GBR)
  - Pipeline completo con OrdinalEncoder (evita LabelEncoder manual)
  - Dashboard HTML autocontenido con 6 gráficas
"""

import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings("ignore")

# ── 1. CARGA OPTIMIZADA ───────────────────────────────────────────────────────

print("Cargando datos...")

DTYPES_FACT = {
    "ID_Variedad": "int32", "ID_Geografia": "int32", "ID_Tiempo": "int32",
    "Medida_Crecimiento": "float32", "Dias_Desde_Poda": "int16",
    "Estado_DQ": "category", "Condicion": "category",
    "Estado_Vegetativo": "category", "Tipo_Tallo": "category",
    "Campana": "category", "Codigo_Ensayo": "category",
}
DTYPES_GEO = {"ID_Geografia": "int32", "ID_Fundo_Catalogo": "int16"}
DTYPES_VAR = {"ID_Variedad": "int32"}
DTYPES_TIEMPO = {"ID_Tiempo": "int32", "Mes": "int8", "Anio": "int16"}

BASE = "D:/Proyecto2026/ACP_DWH/"

fact = pd.read_csv(BASE + "Fact_Tasa_Crecimiento_Export.csv",
                   encoding="utf-8-sig", dtype=DTYPES_FACT)
dim_var = pd.read_csv(BASE + "Dim_Variedad.csv", encoding="utf-8-sig",
                      dtype=DTYPES_VAR)
dim_geo = pd.read_csv(BASE + "Dim_Geografia.csv", encoding="utf-8-sig",
                      dtype=DTYPES_GEO,
                      usecols=["ID_Geografia", "ID_Fundo_Catalogo"])
dim_tiempo = pd.read_csv(BASE + "Dim_Tiempo.csv", encoding="utf-8-sig",
                         dtype=DTYPES_TIEMPO,
                         usecols=["ID_Tiempo", "Mes", "Anio"])

df = (fact
      .merge(dim_var, on="ID_Variedad", how="left")
      .merge(dim_geo,    on="ID_Geografia", how="left")
      .merge(dim_tiempo, on="ID_Tiempo",   how="left"))

df["Semana_Poda"] = (df["Dias_Desde_Poda"] // 7).astype("int8")

df = df.query("Estado_DQ == 'OK' and Medida_Crecimiento > 0 and Dias_Desde_Poda >= 0").copy()

print(f"  Registros válidos : {len(df):,}")
print(f"  Variedades        : {df['Nombre_Variedad'].nunique()}")
print(f"  Rango semanas     : {df['Semana_Poda'].min()} – {df['Semana_Poda'].max()}")


# ── 2. CURVA GOMPERTZ ─────────────────────────────────────────────────────────

print("\n[1/4] Ajustando curva Gompertz...")

def gompertz(t, K, b, c):
    return K * np.exp(-b * np.exp(-c * t))

curva_base = (df[df["Semana_Poda"] <= 20]
              .groupby("Semana_Poda")["Medida_Crecimiento"]
              .agg(["median", "mean", "std", "count"])
              .reset_index()
              .rename(columns={"median": "Mediana", "mean": "Promedio",
                                "std": "Desv_std", "count": "N"}))

t_arr = curva_base["Semana_Poda"].values.astype(float)
y_arr = curva_base["Mediana"].values.astype(float)

try:
    popt, _ = curve_fit(gompertz, t_arr, y_arr, p0=[35, 5, 0.5], maxfev=10000)
    K, b, c = popt
    print(f"  K={K:.1f} cm  b={b:.3f}  c={c:.3f}")
except Exception as e:
    print(f"  Gompertz falló: {e} – usando defaults")
    K, b, c = 30.0, 5.0, 0.4

curva_base["Gompertz"] = gompertz(t_arr, K, b, c).round(2)
curva_base["IC_low"]   = (curva_base["Mediana"] - curva_base["Desv_std"]).clip(0)
curva_base["IC_high"]  = curva_base["Mediana"] + curva_base["Desv_std"]


# ── 3. ANÁLISIS POR GRUPOS ────────────────────────────────────────────────────

print("\n[2/4] Comparando curvas por grupo...")

GRUPOS = ["Nombre_Variedad", "Condicion", "Estado_Vegetativo", "Tipo_Tallo"]
grupos_resultados = {}

for g in GRUPOS:
    pico = (df[df["Semana_Poda"].between(4, 8)]
            .groupby(g)["Medida_Crecimiento"]
            .agg(Mediana_cm="median", Promedio_cm="mean",
                 Desv_std="std", N_obs="count")
            .round(2)
            .sort_values("Mediana_cm", ascending=False)
            .reset_index())
    grupos_resultados[g] = pico
    print(f"  {g}: {len(pico)} categorías")


# ── 4. MODELO PREDICTIVO (HistGradientBoosting – 10× más rápido) ─────────────

print("\n[3/4] Entrenando modelo predictivo (HistGBM)...")

FEATURES_NUM = ["Semana_Poda", "Dias_Desde_Poda", "ID_Fundo_Catalogo", "Mes", "Anio"]
FEATURES_CAT = ["Condicion", "Estado_Vegetativo", "Tipo_Tallo", "Nombre_Variedad", "Campana"]
TARGET = "Medida_Crecimiento"

df_model = df[FEATURES_NUM + FEATURES_CAT + [TARGET]].dropna()

preprocessor = ColumnTransformer([
    ("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), FEATURES_CAT),
], remainder="passthrough")

pipe = Pipeline([
    ("prep", preprocessor),
    ("gbm", HistGradientBoostingRegressor(
        max_iter=200, max_depth=5, learning_rate=0.05,
        min_samples_leaf=30, random_state=42,
    )),
])

pipe.fit(df_model[FEATURES_NUM + FEATURES_CAT], df_model[TARGET])
y_pred = pipe.predict(df_model[FEATURES_NUM + FEATURES_CAT])
mae = mean_absolute_error(df_model[TARGET], y_pred)
r2  = r2_score(df_model[TARGET], y_pred)
print(f"  MAE: {mae:.2f} cm  |  R²: {r2:.4f}")

# Importancia de variables via permutation sobre muestra (HistGBM no tiene feature_importances_)
from sklearn.inspection import permutation_importance

sample_idx = np.random.default_rng(42).choice(len(df_model), size=min(10_000, len(df_model)), replace=False)
X_sample = df_model.iloc[sample_idx][FEATURES_NUM + FEATURES_CAT]
y_sample = df_model.iloc[sample_idx][TARGET]

perm = permutation_importance(pipe, X_sample, y_sample, n_repeats=5,
                               random_state=42, n_jobs=-1)
importancias = pd.DataFrame({
    "Feature": FEATURES_NUM + FEATURES_CAT,
    "Importancia": perm.importances_mean,
}).sort_values("Importancia", ascending=False)
print(importancias.to_string(index=False))


# ── 5. PRONÓSTICO POR VARIEDAD ────────────────────────────────────────────────

print("\n[4/4] Generando pronósticos por variedad...")

UMBRAL_CM  = 25.0
UMBRAL_OBS = 50

pronostico = []
for var, sub in df.groupby("Nombre_Variedad"):
    por_semana = sub.groupby("Semana_Poda")["Medida_Crecimiento"].median()
    semanas_ok = por_semana[por_semana >= UMBRAL_CM].index
    pronostico.append({
        "Variedad": var,
        "N_obs": len(sub),
        "Semana_Pico": int(por_semana.idxmax()),
        "cm_Pico": round(float(por_semana.max()), 1),
        "Semana_>=25cm": int(semanas_ok.min()) if len(semanas_ok) else None,
    })

df_pron = (pd.DataFrame(pronostico)
           .query(f"N_obs >= {UMBRAL_OBS}")
           .sort_values("Semana_>=25cm"))


# ── 6. EXPORTAR CSV ───────────────────────────────────────────────────────────

curva_base.to_csv(BASE + "resultado_curva_base.csv", index=False)
df_pron.to_csv(BASE + "resultado_pronostico_variedades.csv", index=False)
for g, pico in grupos_resultados.items():
    pico.to_csv(BASE + f"resultado_comparativo_{g.lower()}.csv", index=False)

print("  CSVs exportados.")


# ── 7. DASHBOARD PLOTLY ───────────────────────────────────────────────────────

print("\nGenerando dashboard interactivo...")

COLORES = px.colors.qualitative.Bold

fig = make_subplots(
    rows=3, cols=2,
    subplot_titles=[
        "Curva de Crecimiento Promedio (Gompertz)",
        "Pronóstico por Variedad – Semana pico",
        "Comparativo por Condición (semanas 4–8)",
        "Comparativo por Estado Vegetativo (semanas 4–8)",
        "Comparativo por Tipo de Tallo",
        "Importancia de Variables del Modelo",
    ],
    vertical_spacing=0.12,
    horizontal_spacing=0.10,
)

# ─ Gráfica 1: Curva Gompertz ──────────────────────────────────────────────────
fig.add_trace(go.Scatter(
    x=list(curva_base["Semana_Poda"]) + list(curva_base["Semana_Poda"])[::-1],
    y=list(curva_base["IC_high"])     + list(curva_base["IC_low"])[::-1],
    fill="toself", fillcolor="rgba(99,110,250,0.15)",
    line=dict(color="rgba(0,0,0,0)"),
    name="±1 Desv.std", showlegend=True,
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=curva_base["Semana_Poda"], y=curva_base["Mediana"],
    mode="markers+lines", name="Mediana real",
    marker=dict(size=8, color="steelblue"),
    line=dict(color="steelblue", width=2),
    hovertemplate="Semana %{x}<br>Mediana: %{y:.1f} cm<extra></extra>",
), row=1, col=1)

t_smooth = np.linspace(0, 20, 200)
fig.add_trace(go.Scatter(
    x=t_smooth, y=gompertz(t_smooth, K, b, c),
    mode="lines", name=f"Gompertz (K={K:.0f}, c={c:.2f})",
    line=dict(color="crimson", width=2, dash="dash"),
    hovertemplate="t=%{x:.1f}<br>Gompertz: %{y:.1f} cm<extra></extra>",
), row=1, col=1)

fig.add_hline(y=25, line_dash="dot", line_color="green",
              annotation_text="Umbral 25 cm", row=1, col=1)

# ─ Gráfica 2: Pronóstico por variedad ────────────────────────────────────────
df_pron_plot = df_pron.sort_values("cm_Pico", ascending=True)
fig.add_trace(go.Bar(
    x=df_pron_plot["cm_Pico"],
    y=df_pron_plot["Variedad"],
    orientation="h",
    marker=dict(
        color=df_pron_plot["cm_Pico"],
        colorscale="Viridis",
        showscale=True,
        colorbar=dict(title="cm pico", x=1.02, len=0.33, y=0.83),
    ),
    text=df_pron_plot["Semana_>=25cm"].apply(
        lambda s: f"S{int(s)}" if pd.notna(s) else "–"
    ),
    textposition="outside",
    hovertemplate=(
        "<b>%{y}</b><br>Pico: %{x:.1f} cm<br>"
        "Semana pico: %{customdata[0]}<br>"
        "N obs: %{customdata[1]:,}<extra></extra>"
    ),
    customdata=df_pron_plot[["Semana_Pico", "N_obs"]].values,
    name="cm en pico",
    showlegend=False,
), row=1, col=2)

# ─ Gráfica 3: Condición ──────────────────────────────────────────────────────
g_cond = grupos_resultados["Condicion"]
fig.add_trace(go.Bar(
    x=g_cond["Condicion"], y=g_cond["Mediana_cm"],
    error_y=dict(type="data", array=g_cond["Desv_std"], visible=True),
    marker_color=COLORES[:len(g_cond)],
    text=g_cond["N_obs"].apply(lambda n: f"n={n:,}"),
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Mediana: %{y:.1f} cm<br>%{text}<extra></extra>",
    showlegend=False,
), row=2, col=1)

# ─ Gráfica 4: Estado vegetativo ──────────────────────────────────────────────
g_ev = grupos_resultados["Estado_Vegetativo"]
fig.add_trace(go.Bar(
    x=g_ev["Estado_Vegetativo"], y=g_ev["Mediana_cm"],
    error_y=dict(type="data", array=g_ev["Desv_std"], visible=True),
    marker_color=COLORES[3:3+len(g_ev)],
    text=g_ev["N_obs"].apply(lambda n: f"n={n:,}"),
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Mediana: %{y:.1f} cm<br>%{text}<extra></extra>",
    showlegend=False,
), row=2, col=2)

# ─ Gráfica 5: Tipo de tallo ──────────────────────────────────────────────────
g_tt = grupos_resultados["Tipo_Tallo"]
fig.add_trace(go.Bar(
    x=g_tt["Tipo_Tallo"], y=g_tt["Mediana_cm"],
    error_y=dict(type="data", array=g_tt["Desv_std"], visible=True),
    marker_color=COLORES[6:6+len(g_tt)],
    text=g_tt["N_obs"].apply(lambda n: f"n={n:,}"),
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Mediana: %{y:.1f} cm<br>%{text}<extra></extra>",
    showlegend=False,
), row=3, col=1)

# ─ Gráfica 6: Importancia de variables ───────────────────────────────────────
imp_plot = importancias.sort_values("Importancia")
fig.add_trace(go.Bar(
    x=imp_plot["Importancia"],
    y=imp_plot["Feature"],
    orientation="h",
    marker=dict(color=imp_plot["Importancia"], colorscale="Blues"),
    hovertemplate="<b>%{y}</b><br>Importancia: %{x:.4f}<extra></extra>",
    showlegend=False,
), row=3, col=2)

# ─ Layout global ─────────────────────────────────────────────────────────────
fig.update_layout(
    title=dict(
        text=f"<b>Dashboard – Tasa de Crecimiento de Arándanos</b>"
             f"<br><sub>MAE={mae:.2f} cm  |  R²={r2:.3f}  |  "
             f"n={len(df_model):,} observaciones</sub>",
        x=0.5, font_size=18,
    ),
    height=1300,
    template="plotly_white",
    legend=dict(orientation="h", y=1.02, x=0),
    font=dict(family="Arial", size=12),
)

# Etiquetas de ejes
fig.update_xaxes(title_text="Semana desde poda", row=1, col=1)
fig.update_yaxes(title_text="Crecimiento (cm)", row=1, col=1)
fig.update_xaxes(title_text="cm en pico", row=1, col=2)
fig.update_yaxes(title_text="Crecimiento mediano (cm)", row=2, col=1)
fig.update_yaxes(title_text="Crecimiento mediano (cm)", row=2, col=2)
fig.update_yaxes(title_text="Crecimiento mediano (cm)", row=3, col=1)
fig.update_xaxes(title_text="Importancia relativa", row=3, col=2)

# Línea umbral en gráficas 3, 4, 5
for r, c in [(2, 1), (2, 2), (3, 1)]:
    fig.add_hline(y=25, line_dash="dot", line_color="green", row=r, col=c)

OUT_HTML = BASE + "dashboard_crecimiento.html"
fig.write_html(OUT_HTML, include_plotlyjs="cdn")
print(f"\nDashboard guardado: {OUT_HTML}")

# ─ Gráfica extra: curvas por variedad (top 10) ───────────────────────────────
top10 = (grupos_resultados["Nombre_Variedad"]
         .head(10)["Nombre_Variedad"].tolist())

fig2 = go.Figure()
for i, var in enumerate(top10):
    sub = df[df["Nombre_Variedad"] == var]
    por_sem = (sub[sub["Semana_Poda"] <= 20]
               .groupby("Semana_Poda")["Medida_Crecimiento"]
               .median().reset_index())
    fig2.add_trace(go.Scatter(
        x=por_sem["Semana_Poda"], y=por_sem["Medida_Crecimiento"],
        mode="lines+markers", name=var,
        line=dict(color=COLORES[i % len(COLORES)], width=2),
        hovertemplate=f"<b>{var}</b><br>Semana %{{x}}<br>%{{y:.1f}} cm<extra></extra>",
    ))

fig2.add_hline(y=25, line_dash="dot", line_color="green",
               annotation_text="Umbral cosecha 25 cm")
fig2.update_layout(
    title="<b>Curvas de crecimiento – Top 10 variedades</b>",
    xaxis_title="Semana desde poda",
    yaxis_title="Crecimiento mediano (cm)",
    template="plotly_white",
    height=550,
    legend=dict(orientation="v", x=1.01),
    font=dict(family="Arial", size=12),
)

OUT_HTML2 = BASE + "dashboard_variedades.html"
fig2.write_html(OUT_HTML2, include_plotlyjs="cdn")
print(f"Dashboard variedades: {OUT_HTML2}")
print("\nModelo v2 completo.")
