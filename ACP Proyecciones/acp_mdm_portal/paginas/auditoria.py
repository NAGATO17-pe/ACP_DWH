"""
paginas/auditoria.py — Panel de Auditoría ETL · Portal MDM ACP
================================================================
Consume los endpoints:
  GET /api/v1/auditoria/log-carga          — historial completo
  GET /api/v1/auditoria/log-carga/{tabla}  — último estado de una tabla

Funcionalidades:
  · KPIs de resumen de la sesión de carga más reciente
  · Tabla de historial con filtros por estado y búsqueda de tabla
  · Detalle por tabla: última carga, filas OK/rechazadas, duración
  · Exportación CSV del historial filtrado
  · Auto-refresh configurable
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from utils.api_client import get_api, mostrar_error_api
from utils.auth import tiene_permiso
from utils.componentes import badge_html, estado_vacio_html, banner_aviso
from utils.formato import header_pagina, renderizar_tabla_premium, crear_panel_metricas_premium
from utils.componentes import badge_html, estado_vacio_html, mostrar_kpis
from utils.constantes import (
    ESTADO_COLORES as _ESTADO_COLORES,
    ESTADO_ICONOS as _ESTADO_ICONOS,
    LIMITE_HISTORIAL_DEFAULT as _LIMITE_DEFAULT,
    OPCIONES_LIMITE_HISTORIAL,
    PAGE_SIZE_DEFAULT as _PAGE_SIZE,
)
from utils.formato import crear_tarjeta_kpi, header_pagina, renderizar_tabla_premium


# ── Helpers de datos ──────────────────────────────────────────────────────────

def _cargar_historial(limite: int) -> list[dict]:
    """Consulta directa al backend — sin caché. Siempre datos frescos."""
    resultado = get_api(f"/auditoria/log-carga?limite={limite}")
    if resultado.ok and isinstance(resultado.data, list):
        return resultado.data
    return []


def _a_dataframe(registros: list[dict]) -> pd.DataFrame:
    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)

    for col in ("fecha_inicio", "fecha_fin"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "duracion_segundos" in df.columns:
        df["duracion_segundos"] = pd.to_numeric(df["duracion_segundos"], errors="coerce")

    return df


def _formatear_duracion(segundos) -> str:
    try:
        s = int(segundos)
        if s < 60:
            return f"{s}s"
        m, s = divmod(s, 60)
        return f"{m}m {s:02d}s"
    except (TypeError, ValueError):
        return "—"


def _icono_estado(estado: str) -> str:
    return _ESTADO_ICONOS.get(str(estado).upper(), "❓")


# ── Sección KPIs ──────────────────────────────────────────────────────────────

def _render_kpis(df: pd.DataFrame) -> None:
    if df.empty:
        return

    total_corridas   = df["id_log"].nunique() if "id_log" in df.columns else len(df)
    total_ok         = int(df["filas_insertadas"].sum()) if "filas_insertadas" in df.columns else 0
    total_rechaz     = int(df["filas_rechazadas"].sum()) if "filas_rechazadas" in df.columns else 0
    corridas_ok      = int((df["estado"] == "OK").sum()) if "estado" in df.columns else 0
    corridas_error   = int((df["estado"] == "ERROR").sum()) if "estado" in df.columns else 0
    tablas_distintas = df["tabla_destino"].nunique() if "tabla_destino" in df.columns else 0

    ultima_fecha = "—"
    if "fecha_inicio" in df.columns and not df["fecha_inicio"].isna().all():
        ultima_fecha = df["fecha_inicio"].dropna().max().strftime("%d/%m %H:%M")

    duracion_prom = "—"
    if "duracion_segundos" in df.columns:
        prom = df["duracion_segundos"].dropna().mean()
        duracion_prom = _formatear_duracion(prom)

    # Barra de progreso OK vs Error
    pct_ok = round((corridas_ok / total_corridas) * 100, 1) if total_corridas > 0 else 0

    # Usar componente premium centralizado
    crear_panel_metricas_premium(
        metricas=[
            {"label": "Última corrida", "value": ultima_fecha, "color": "#e8a020"},
            {"label": "Tablas", "value": str(tablas_distintas)},
            {"label": "Filas OK", "value": f"{total_ok:,}", "color": "#2db87a"},
            {"label": "Rechazadas", "value": f"{total_rechaz:,}", "color": "#EF4444" if total_rechaz else "#8fa897"},
            {"label": "Errores", "value": str(corridas_error), "color": "#EF4444" if corridas_error else "#2db87a"},
            {"label": "Duración", "value": duracion_prom}
        ],
        pct_progreso=pct_ok,
        texto_progreso="Tasa de éxito de corridas",
        labels_progreso={"ok": f"{corridas_ok} exitosas", "error": f"{corridas_error} con error"}
    )



# ── Sección filtros ───────────────────────────────────────────────────────────

def _render_filtros(df: pd.DataFrame) -> pd.DataFrame:
    with st.container(border=True):
        st.markdown(
            "<p style='font-size:0.65rem;font-weight:700;color:rgba(255,255,255,0.35);"
            "text-transform:uppercase;letter-spacing:2px;margin-bottom:10px;'>Filtros</p>",
            unsafe_allow_html=True,
        )
        col_b, col_e, col_t, col_d = st.columns([2, 1, 2, 1])

        with col_b:
            busqueda = st.text_input(
                "Buscar tabla",
                placeholder="ej: fact_tareo, dim_geo…",
                key="aud_busqueda",
                label_visibility="collapsed",
            )

        with col_e:
            estados_disp = ["Todos"] + sorted(df["estado"].dropna().unique().tolist()) if "estado" in df.columns else ["Todos"]
            estado_sel = st.selectbox("Estado", estados_disp, key="aud_estado", label_visibility="collapsed")

        with col_t:
            if "fecha_inicio" in df.columns and not df["fecha_inicio"].isna().all():
                fecha_min = df["fecha_inicio"].dropna().min().date()
                fecha_max = df["fecha_inicio"].dropna().max().date()
                rango = st.date_input(
                    "Rango de fechas",
                    value=(fecha_min, fecha_max),
                    min_value=fecha_min,
                    max_value=fecha_max,
                    key="aud_fechas",
                    label_visibility="collapsed",
                )
                fecha_desde = rango[0] if isinstance(rango, (list, tuple)) and len(rango) > 0 else fecha_min
                fecha_hasta = rango[1] if isinstance(rango, (list, tuple)) and len(rango) > 1 else fecha_max
            else:
                fecha_desde = fecha_hasta = None

        with col_d:
            limite = st.selectbox("Límite", OPCIONES_LIMITE_HISTORIAL, index=2, key="aud_limite", label_visibility="collapsed")

    # Aplicar filtros
    dff = df.copy()

    if busqueda and "tabla_destino" in dff.columns:
        dff = dff[dff["tabla_destino"].str.contains(busqueda, case=False, na=False)]

    if estado_sel != "Todos" and "estado" in dff.columns:
        dff = dff[dff["estado"] == estado_sel]

    if fecha_desde and fecha_hasta and "fecha_inicio" in dff.columns:
        dff = dff[
            (dff["fecha_inicio"].dt.date >= fecha_desde) &
            (dff["fecha_inicio"].dt.date <= fecha_hasta)
        ]

    return dff, limite


# ── Tabla historial ───────────────────────────────────────────────────────────

def _preparar_vista(df: pd.DataFrame) -> pd.DataFrame:
    vista = df.copy()

    # Ícono de estado
    if "estado" in vista.columns:
        vista[""] = vista["estado"].apply(_icono_estado)

    # Formatear fechas compactas
    for col_ts in ("fecha_inicio", "fecha_fin"):
        if col_ts in vista.columns:
            vista[col_ts] = vista[col_ts].dt.strftime("%m/%d %H:%M").fillna("—")

    # Duración legible
    if "duracion_segundos" in vista.columns:
        vista["duración"] = vista["duracion_segundos"].apply(_formatear_duracion)

    # Truncar mensaje de error
    if "mensaje_error" in vista.columns:
        vista["error"] = vista["mensaje_error"].fillna("").str[:60]

    cols_orden = [
        "", "tabla_destino", "estado", "filas_insertadas",
        "filas_rechazadas", "duración", "fecha_inicio", "error",
    ]
    cols_presentes = [c for c in cols_orden if c in vista.columns]
    vista = vista[cols_presentes]

    vista = vista.rename(columns={
        "tabla_destino":    "Tabla",
        "estado":           "Estado",
        "filas_insertadas": "Filas OK",
        "filas_rechazadas": "Rechaz.",
        "fecha_inicio":     "Inicio",
    })

    return vista


def _render_tabla_historial(df: pd.DataFrame) -> None:
    if df.empty:
        estado_vacio_html(
            icono="📋",
            titulo="Sin registros de auditoría",
            subtitulo="No hay corridas ETL que coincidan con los filtros aplicados.",
        )
        return

    vista = _preparar_vista(df)

    col_info, col_exp = st.columns([3, 1])
    with col_info:
        st.caption(f"{len(df)} registro(s) · Actualizado: {datetime.now().strftime('%H:%M:%S')}")
    with col_exp:
        csv_bytes = io.BytesIO()
        df.to_csv(csv_bytes, index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ Exportar CSV",
            data=csv_bytes.getvalue(),
            file_name=f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="btn_export_auditoria",
        )

    renderizar_tabla_premium(vista, key="aud_historial", page_size=_PAGE_SIZE)


# ── Sección detalle por tabla ─────────────────────────────────────────────────

def _render_detalle_tabla(df: pd.DataFrame) -> None:
    if df.empty or "tabla_destino" not in df.columns:
        return

    tablas = sorted(df["tabla_destino"].dropna().unique().tolist())
    if not tablas:
        return

    st.divider()
    st.markdown("### 🔍 Detalle por tabla")

    col_sel, col_ref = st.columns([3, 1])
    with col_sel:
        tabla_sel = st.selectbox(
            "Seleccionar tabla",
            tablas,
            key="aud_tabla_sel",
            label_visibility="collapsed",
        )
    with col_ref:
        if st.button("🔄 Consultar backend", key="btn_aud_detalle", type="secondary"):
            st.cache_data.clear()

    resultado = get_api(f"/auditoria/log-carga/{tabla_sel}")

    if not resultado.ok:
        if resultado.status_code == 404:
            banner_aviso(f"No hay registros de auditoría para **{tabla_sel}**.")
        else:
            mostrar_error_api(resultado, "Error al consultar el detalle.")
        return

    datos = resultado.data if isinstance(resultado.data, dict) else {}

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)

        estado_raw   = str(datos.get("estado", "—")).upper()
        icono_estado = _ESTADO_ICONOS.get(estado_raw, "❓")
        badge_tipo   = _ESTADO_COLORES.get(estado_raw, "PENDIENTE")

        with c1:
            _texto_estado = f"{icono_estado} {datos.get('estado', '—')}"
            st.markdown(
                f"<div style='font-size:0.7rem;color:#64748B;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;'>Estado</div>"
                + badge_html(_texto_estado, badge_tipo),
                unsafe_allow_html=True,
            )
        with c2:
            filas_ok = datos.get("filas_insertadas", 0) or 0
            st.markdown(
                f"<div style='font-size:0.65rem;color:#8fa897;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:0.8px;margin-bottom:4px;'>Filas insertadas</div>"
                f"<div style='font-size:1.35rem;font-weight:700;color:#2db87a;"
                f"font-family:JetBrains Mono,monospace;'>{int(filas_ok):,}</div>",
                unsafe_allow_html=True,
            )
        with c3:
            filas_r = datos.get("filas_rechazadas", 0) or 0
            color_r = "#EF4444" if filas_r else "#8fa897"
            st.markdown(
                f"<div style='font-size:0.65rem;color:#8fa897;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:0.8px;margin-bottom:4px;'>Rechazadas</div>"
                f"<div style='font-size:1.35rem;font-weight:700;color:{color_r};"
                f"font-family:JetBrains Mono,monospace;'>{int(filas_r):,}</div>",
                unsafe_allow_html=True,
            )
        with c4:
            dur = _formatear_duracion(datos.get("duracion_segundos"))
            st.markdown(
                f"<div style='font-size:0.65rem;color:#8fa897;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:0.8px;margin-bottom:4px;'>Duración</div>"
                f"<div style='font-size:1.35rem;font-weight:700;color:#e8a020;"
                f"font-family:JetBrains Mono,monospace;'>{dur}</div>",
                unsafe_allow_html=True,
            )

        # Fechas
        fi = datos.get("fecha_inicio")
        ff = datos.get("fecha_fin")
        if fi or ff:
            st.markdown(
                f"<p style='font-size:0.8rem;color:#8fa897;margin-top:10px;'>"
                f"⏱ Inicio: <b style='color:#e8f0ec'>{fi or '—'}</b> &nbsp;|&nbsp; Fin: <b style='color:#e8f0ec'>{ff or '—'}</b></p>",
                unsafe_allow_html=True,
            )

        # Mensaje de error
        error_msg = datos.get("mensaje_error") or ""
        if error_msg:
            st.error(f"**Error registrado:** {error_msg}", icon="🚨")


# ── Sección distribución de estados ──────────────────────────────────────────

def _render_resumen_estados(df: pd.DataFrame) -> None:
    if df.empty or "estado" not in df.columns:
        return

    conteo = df["estado"].value_counts()
    total  = len(df)

    bloques = ""
    paleta = {
        "OK":      "#2db87a",
        "ERROR":   "#EF4444",
        "RUNNING": "#e8a020",
        "SKIPPED": "#8fa897",
    }

    for estado, cnt in conteo.items():
        pct   = round((cnt / total) * 100, 1)
        color = paleta.get(str(estado).upper(), "#8fa897")
        icono = _ESTADO_ICONOS.get(str(estado).upper(), "❓")
        bloques += f"""
        <div style="
            background: rgba(26, 46, 30, 0.5);
            border: 1px solid rgba(255,255,255,0.07);
            border-bottom: 2px solid {color}44;
            border-radius: 14px;
            padding: 18px 16px;
            flex: 1; min-width: 140px;
            display: flex; flex-direction: column; align-items: center; gap: 6px;
        ">
            <div style="font-size:1.6rem;">{icono}</div>
            <div style="font-family:'JetBrains Mono',monospace; font-size:1.6rem; font-weight:700;
                        color:{color};">{cnt}</div>
            <div style="font-size:0.6rem; text-transform:uppercase; letter-spacing:2px;
                        color:#8fa897; font-weight:700;">{estado}</div>
            <div style="font-size:0.7rem; color:{color}; font-weight:600; opacity:0.8;">{pct}%</div>
        </div>"""

    st.markdown(
        f"<div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:16px; margin-bottom:24px;'>{bloques}</div>",
        unsafe_allow_html=True,
    )



# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    header_pagina("📋", "Auditoría ETL", "Historial completo de cargas · Trazabilidad de corridas")

    if not tiene_permiso("leer"):
        st.error("Acceso denegado. Se requiere al menos rol Viewer.")
        return

    # Barra de acciones: refresco y configuración de límite
    col_titulo, col_acc = st.columns([4, 1])
    with col_acc:
        if st.button("🔄 Recargar", key="btn_aud_reload", help="Limpia caché y recarga del backend"):
            st.cache_data.clear()
            st.rerun()

    # Carga inicial de datos
    with st.spinner("Cargando historial de auditoría…"):
        registros = _cargar_historial(_LIMITE_DEFAULT)

    if not registros:
        estado_vacio_html(
            icono="📭",
            titulo="Sin historial de auditoría",
            subtitulo="No se encontraron registros. Verifica que el backend esté corriendo y que se hayan ejecutado corridas ETL.",
        )
        return

    df = _a_dataframe(registros)

    # ── KPIs + barra de progreso (panel unificado) ──────────────────────────
    _render_kpis(df)

    # ── Filtros + tabla ──────────────────────────────────────────────────────
    st.markdown("### 📊 Historial de corridas")
    dff, limite_nuevo = _render_filtros(df)

    # Si el usuario cambia el límite, recargar
    if limite_nuevo != _LIMITE_DEFAULT:
        with st.spinner("Recargando con nuevo límite…"):
            registros = _cargar_historial(limite_nuevo)
        df  = _a_dataframe(registros)
        dff = df  # resetear filtros tras cambio de límite

    _render_tabla_historial(dff)

    # ── Detalle por tabla (consulta directa al backend) ──────────────────────
    _render_detalle_tabla(df)
