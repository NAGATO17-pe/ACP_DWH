"""
utils/componentes.py — Componentes reutilizables del Portal MDM ACP (Enterprise)
==================================================================================
Módulo ÚNICO de UI compartida. Todas las páginas importan desde aquí.

Componentes disponibles
-----------------------
  mostrar_kpis()                  — Fila de métricas st.metric estandarizada
  badge_html()                    — Badge HTML semántico (severidad/estado)
  estado_vacio_html()             — Estado vacío elegante (HTML puro)
  seccion_tabla_con_guardar()     — Tabla con paginación local + guardar
  banner_aviso()                  — Banner de aviso estándar
  health_status_panel()           — Panel de salud de conexión descriptivo
  mostrar_dialogo_confirmacion()  — Modal de confirmación
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


# ── 1. KPIs normalizados ──────────────────────────────────────────────────────

def mostrar_kpis(metricas: list[dict]) -> None:
    """
    Renderiza una fila de métricas con `st.metric` en columnas iguales.

    Cada dict:  label, value, delta (opt), delta_color (opt: "normal"|"inverse"|"off")
    """
    cols = st.columns(len(metricas))
    for col, m in zip(cols, metricas):
        col.metric(
            label=m["label"],
            value=m["value"],
            delta=m.get("delta"),
            delta_color=m.get("delta_color", "normal"),
        )


# ── 3. Badge HTML unificado ───────────────────────────────────────────────────

_BADGE_PALETTE: dict[str, tuple[str, str, str]] = {
    "CRÍTICO":         ("#C0392B", "rgba(192, 57,  43, 0.12)", "#C0392B"),
    "ALTO":            ("#E67E22", "rgba(230,126,  34, 0.12)", "#E67E22"),
    "MEDIO":           ("#1E6B35", "rgba( 30,107,  53, 0.12)", "#1E6B35"),
    "PENDIENTE":       ("#3949AB", "rgba( 57, 73, 171, 0.12)", "#3949AB"),
    "EN_REVISIÓN":     ("#E29D45", "rgba(226,157,  69, 0.12)", "#E29D45"),
    "RESUELTO":        ("#1E6B35", "rgba( 30,107,  53, 0.12)", "#1E6B35"),
    "RECHAZADO":       ("#7C3AED", "rgba(124, 58, 237, 0.12)", "#7C3AED"),
    "EN_CUARENTENA":   ("#C0392B", "rgba(192, 57,  43, 0.12)", "#C0392B"),
    "✅ OK":           ("#2E8B57", "rgba( 46,139,  87, 0.12)", "#2E8B57"),
    "⚠️ Con errores":  ("#E67E22", "rgba(230,126,  34, 0.12)", "#E67E22"),
    "❌ Falló":        ("#C0392B", "rgba(192, 57,  43, 0.12)", "#C0392B"),
    "OK":              ("#2E8B57", "rgba( 46,139,  87, 0.12)", "#2E8B57"),
    "success":         ("#027A48", "#ECFDF3",                 "#027A48"),
    "error":           ("#B42318", "#FEF3F2",                 "#B42318"),
}
_BADGE_DEFAULT = ("#555555", "rgba(128,128,128,0.10)", "#aaaaaa")


def badge_html(texto: str, tipo: str | None = None) -> str:
    """Genera un <span> badge semántico HTML."""
    clave = tipo if tipo is not None else texto
    fg, bg, border = _BADGE_PALETTE.get(clave, _BADGE_DEFAULT)
    return (
        f"<span style='"
        f"background:{bg}; color:{fg}; border:1px solid {border}; "
        f"padding:2px 10px; border-radius:12px; "
        f"font-size:0.78rem; font-weight:700; "
        f"display:inline-block; line-height:1.6;"
        f"'>{texto}</span>"
    )


# ── 4. Estado vacío elegante ─────────────────────────────────────────────────

def estado_vacio_html(
    icono: str = "📭",
    titulo: str = "Sin datos disponibles",
    subtitulo: str = "No se encontraron registros para mostrar.",
) -> None:
    """Renderiza un estado vacío con HTML premium (reemplaza Lottie)."""
    st.markdown(
        f"""
        <div style="
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 56px 24px; text-align: center;
            background: var(--secondary-background-color);
            border: 1px solid rgba(128,128,128,0.15); border-radius: 16px;
            margin: 16px 0;
            animation: fadeIn 0.4s ease;
        ">
            <div style="font-size:3.8rem; margin-bottom:16px; opacity:0.55;
                        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">
                {icono}
            </div>
            <h4 style="margin:0 0 8px 0; color:var(--text-color); opacity:0.8;
                       font-size:1.1rem; font-weight:600;">
                {titulo}
            </h4>
            <p style="margin:0; color:var(--text-color); opacity:0.50;
                      font-size:0.92rem; max-width:360px;">
                {subtitulo}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── 5. Tabla local con guardar ───────────────────────────────────────────────

def seccion_tabla_con_guardar(
    df: pd.DataFrame,
    key: str,
    titulo: str = "📋 Registros",
    page_size: int = 15,
    columnas_check: list[str] | None = None,
    columnas_ocultas: list[str] | None = None,
    btn_key: str | None = None,
    btn_label: str = "💾 Guardar cambios",
    caption: str = "Paginación profesional activa.",
    mostrar_boton_guardar: bool = True,
) -> None:
    """
    Tabla con paginación local (para datos que ya están en memoria).
    Usar seccion_tabla_sql_paginada() cuando sea posible.
    """
    if titulo:
        st.markdown(f"### {titulo}")

    if df.empty:
        estado_vacio_html(
            icono="📭", titulo="Sin registros",
            subtitulo="No hay datos registrados en este catálogo.",
        )
        return

    if caption:
        st.caption(caption)

    from utils.formato import renderizar_tabla_premium
    renderizar_tabla_premium(
        df, key=key, page_size=page_size,
        columnas_check=columnas_check,
        columnas_ocultas=columnas_ocultas,
    )

    if mostrar_boton_guardar:
        _btn_key = btn_key or f"btn_{key}_guardar"
        if st.button(btn_label, key=_btn_key, type="primary"):
            st.toast("Operación completada.", icon="✅")


# ── 7. Banner de aviso estandarizado ─────────────────────────────────────────

def banner_aviso(mensaje: str) -> None:
    """Renderiza el banner de aviso naranja estándar del portal."""
    st.markdown(
        f'<div class="banner-aviso">⚠️ <b>Atención:</b> {mensaje}</div>',
        unsafe_allow_html=True,
    )


# ── 8. Panel de salud de conexión ────────────────────────────────────────────

def health_status_panel() -> bool:
    """Muestra un badge de conexión basado en la disponibilidad del Backend."""
    from utils.api_client import get_api, obtener_url_backend

    resultado = get_api("/health/live", base_url=obtener_url_backend())
    if resultado.ok:
        st.sidebar.markdown(badge_html("Servidor API Conectado", "success"), unsafe_allow_html=True)
        return True

    st.sidebar.markdown(badge_html("Servidor API Desconectado", "error"), unsafe_allow_html=True)
    return False

def mostrar_dialogo_confirmacion(titulo: str, mensaje: str, callback: callable, *args, **kwargs):
    """
    Despliega un modal de confirmación limpio usando st.dialog (1.37+) o 
    st.experimental_dialog (1.34+).
    """
    if hasattr(st, "dialog"):
        decorator = st.dialog
    elif hasattr(st, "experimental_dialog"):
        decorator = st.experimental_dialog
    else:
        # Fallback para versiones muy antiguas
        st.warning(mensaje)
        if st.button("Confirmar fallback"):
            callback(*args, **kwargs)
        return

    @decorator(titulo)
    def _modal():
        st.markdown(f"**{mensaje}**")
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Sí, Confirmar", type="primary", width='stretch'):
                callback(*args, **kwargs)
                st.rerun()
        with col2:
            if st.button("❌ Cancelar", width='stretch'):
                st.rerun()

    _modal()
