"""
utils/sidebar_badges.py — Badges de estado en tiempo real para el sidebar
Dos indicadores persistentes que el operador ve al abrir el portal:

  · Cuarentena  — conteo de registros con estado = 'PENDIENTE'
  · ETL         — estado del backend (activo / degradado) + tiempo relativo

Cache TTL: 300 s (5 min). No bloquea navegación — falla silenciosamente.
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from utils.api_client import get_api, obtener_url_backend


# ── Fetch con caché ────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_cuarentena_pendientes() -> int | None:
    """Devuelve el conteo de registros PENDIENTE en cuarentena, o None si falla."""
    resultado = get_api("/cuarentena/resumen")
    if resultado.ok and isinstance(resultado.data, dict):
        return int(resultado.data.get("PENDIENTE", 0))
    return None


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_health() -> dict | None:
    """Devuelve el dict de /health, o None si falla."""
    resultado = get_api("/health", base_url=obtener_url_backend())
    if resultado.ok and isinstance(resultado.data, dict):
        return resultado.data
    return None


# ── Tiempo relativo ────────────────────────────────────────────────────────────

def _tiempo_relativo(iso_ts: str) -> str:
    """Convierte un ISO timestamp a texto relativo: 'hace 3 min', 'hace 2h', etc."""
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        delta = int((datetime.now(tz=timezone.utc) - ts).total_seconds())
        if delta < 60:
            return "ahora"
        if delta < 3600:
            return f"hace {delta // 60} min"
        if delta < 86400:
            return f"hace {delta // 3600}h"
        return f"hace {delta // 86400}d"
    except Exception:
        return ""


# ── Render ─────────────────────────────────────────────────────────────────────

def render_sidebar_badges() -> None:
    """
    Renderiza el bloque de badges de estado en el sidebar.
    Diseñado para llamarse dentro de `with st.sidebar:`, antes del st.radio.
    Falla silenciosamente: si el backend no responde, no muestra nada.
    """
    pendientes = _fetch_cuarentena_pendientes()
    health     = _fetch_health()

    # Si ambos fallan (backend caído), no renderizar nada
    if pendientes is None and health is None:
        return

    filas_html = []

    # ── Badge Cuarentena ──────────────────────────────────────────────────────
    if pendientes is not None:
        if pendientes == 0:
            dot_color  = "#2db87a"   # verde-cosecha
            dot_bg     = "rgba(45, 184, 122, 0.12)"
            valor_txt  = "✓ 0"
            label_color = "rgba(45, 184, 122, 0.7)"
        else:
            dot_color  = "#EF4444"
            dot_bg     = "rgba(239, 68, 68, 0.12)"
            valor_txt  = str(pendientes)
            label_color = "#EF4444"

        filas_html.append(f"""
        <div class="sb-badge-row">
            <span class="sb-badge-dot" style="background:{dot_color};box-shadow:0 0 6px {dot_color}55;"></span>
            <span class="sb-badge-label">Cuarentena</span>
            <span class="sb-badge-value" style="color:{label_color};">{valor_txt}
                <span class="sb-badge-sub">pendiente{'s' if pendientes != 1 else ''}</span>
            </span>
        </div>
        """)

    # ── Badge ETL / Health ────────────────────────────────────────────────────
    if health is not None:
        estado = str(health.get("estado", "")).lower()
        ts     = health.get("timestamp", "")
        tiempo = _tiempo_relativo(ts) if ts else ""

        activo = estado in ("activo", "vivo", "listo", "operativo")
        if activo:
            dot_color   = "#2db87a"
            dot_bg      = "rgba(45, 184, 122, 0.12)"
            label_color = "rgba(45, 184, 122, 0.7)"
            estado_txt  = "ok"
        else:
            dot_color   = "#EF4444"
            dot_bg      = "rgba(239, 68, 68, 0.12)"
            label_color = "#EF4444"
            estado_txt  = "degradado"

        tiempo_html = (
            f'<span class="sb-badge-sub">{tiempo}</span>'
            if tiempo else ""
        )
        filas_html.append(f"""
        <div class="sb-badge-row">
            <span class="sb-badge-dot" style="background:{dot_color};box-shadow:0 0 6px {dot_color}55;"></span>
            <span class="sb-badge-label">ETL</span>
            <span class="sb-badge-value" style="color:{label_color};">{estado_txt} {tiempo_html}</span>
        </div>
        """)

    if not filas_html:
        return

    st.markdown(
        f"""
        <div class="sb-badges-panel">
            {''.join(filas_html)}
        </div>
        """,
        unsafe_allow_html=True,
    )
utils/sidebar_badges.py
Obtiene conteos para los badges del sidebar (p. ej. "Cuarentena (12)").

Usa GET /api/v1/cuarentena/resumen — una sola query SQL GROUP BY en el
backend — en lugar de descargar miles de registros para contarlos en cliente.
"""

from __future__ import annotations

import streamlit as st

from utils.api_client import get_api

_CACHE_TTL_SEG = 60  # refresca el badge cada minuto


@st.cache_data(ttl=_CACHE_TTL_SEG, show_spinner=False)
def _fetch_resumen_cuarentena() -> dict:
    resultado = get_api("/cuarentena/resumen")
    if resultado.ok and isinstance(resultado.data, dict):
        return resultado.data
    return {"total": 0, "pendientes": 0, "resueltos": 0, "descartados": 0}


def conteo_cuarentena_pendientes() -> int:
    """Devuelve el número de registros con estado PENDIENTE."""
    return _fetch_resumen_cuarentena().get("pendientes", 0)


def resumen_cuarentena() -> dict:
    """Devuelve el dict completo {total, pendientes, resueltos, descartados}."""
    return _fetch_resumen_cuarentena()
