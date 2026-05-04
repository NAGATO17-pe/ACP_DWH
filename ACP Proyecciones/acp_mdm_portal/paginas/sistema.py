"""
paginas/sistema.py — Panel de Sistema y Health · Portal MDM ACP
================================================================
Consume los endpoints:
  GET /health          — estado completo proceso + BD
  GET /health/live     — liveness del proceso HTTP
  GET /health/ready    — readiness (BD disponible)
  GET /health/ready/control — estado del esquema Control.*
  GET /health/ready/runner  — estado del runner ETL
  GET /health/lock     — estado actual del lock del runner

Funcionalidades:
  · Tarjetas de estado en tiempo real para cada subsistema
  · Indicador visual del lock del runner con estado semántico
  · Panel de latencia y versión de SQL Server
  · Historial de checks en la sesión (últimas N consultas)
  · Auto-refresh configurable por el usuario
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

import streamlit as st

from utils.api_client import get_api, URL_BACKEND
from utils.auth import tiene_permiso
from utils.componentes import badge_html, estado_vacio_html
from utils.constantes import AUTOREFRESH_OPCIONES, LOCK_ESTADOS as _LOCK_ESTADOS
from utils.formato import crear_tarjeta_kpi, header_pagina

# ── Constantes ────────────────────────────────────────────────────────────────

_BASE_URL = URL_BACKEND

_SUBSISTEMAS = [
    {
        "key":      "live",
        "endpoint": "/health/live",
        "label":    "Proceso HTTP",
        "icono":    "🌐",
        "desc":     "El servidor FastAPI está respondiendo peticiones.",
    },
    {
        "key":      "ready",
        "endpoint": "/health/ready",
        "label":    "Base de datos",
        "icono":    "🗄️",
        "desc":     "Conexión activa con SQL Server · ACP_DataWarehouse_Proyecciones.",
    },
    {
        "key":      "control",
        "endpoint": "/health/ready/control",
        "label":    "Control-Plane ETL",
        "icono":    "🧩",
        "desc":     "Esquema Control.* accesible y corridas registrables.",
    },
    {
        "key":      "runner",
        "endpoint": "/health/ready/runner",
        "label":    "Runner ETL",
        "icono":    "⚙️",
        "desc":     "El runner está libre para aceptar nuevas corridas.",
    },
]


_HISTORIAL_MAX = 10  # entradas de historial en la sesión


# ── Helpers de consulta ───────────────────────────────────────────────────────

def _consultar(endpoint: str) -> dict[str, Any]:
    """Llama a un endpoint del backend y devuelve el dict de respuesta."""
    resultado = get_api(endpoint, base_url=_BASE_URL)
    if resultado.ok and isinstance(resultado.data, dict):
        return resultado.data
    return {"estado": "error", "_http_error": resultado.error, "_status": resultado.status_code}


def _es_sano(datos: dict) -> bool:
    estado = str(datos.get("estado", "")).lower()
    return estado in ("vivo", "listo", "operativo", "libre", "ocupado", "activo")


# ── Tarjeta de subsistema ─────────────────────────────────────────────────────

def _render_tarjeta_subsistema(cfg: dict, datos: dict) -> None:
    sano   = _es_sano(datos)
    estado = datos.get("estado", "error")
    color  = "#10B981" if sano else "#EF4444"
    bg     = "#F0FDF4" if sano else "#FEF2F2"
    borde  = "#BBF7D0" if sano else "#FECACA"
    dot    = "🟢" if sano else "🔴"

    # Latencia (solo si el endpoint la trae)
    bd     = datos.get("base_datos") or {}
    lat    = bd.get("latencia_ms", "")
    lat_txt = f"<span style='color:#64748B;font-size:0.75rem;'> · {lat} ms</span>" if lat else ""

    estado_safe = html.escape(str(estado).upper())
    st.markdown(f"""
    <div style="
        background:{bg};
        border:1px solid {borde};
        border-left:4px solid {color};
        border-radius:12px;
        padding:16px 18px;
        height:100%;
        box-sizing:border-box;
        animation: fadeIn 0.3s ease;
    ">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:1.25rem;">{cfg['icono']}</span>
            <span style="font-weight:700;font-size:0.9rem;color:#1F2937;">{cfg['label']}</span>
            <span style="margin-left:auto;">{dot}</span>
        </div>
        <div style="
            display:inline-block;
            background:{color}22; color:{color};
            border:1px solid {color}44;
            border-radius:20px; padding:2px 10px;
            font-size:0.75rem; font-weight:700;
            margin-bottom:8px;
        ">{estado_safe}{lat_txt}</div>
        <p style="margin:0;font-size:0.78rem;color:#64748B;line-height:1.4;">
            {cfg['desc']}
        </p>
    </div>
    """, unsafe_allow_html=True)


# ── Panel del Lock ────────────────────────────────────────────────────────────

def _render_panel_lock(datos_lock: dict) -> None:
    estado_raw = str(datos_lock.get("estado", "error")).lower()
    lock_info  = datos_lock.get("lock") or {}
    dot, color, descripcion = _LOCK_ESTADOS.get(estado_raw, _LOCK_ESTADOS["error"])

    st.markdown(f"""
    <div style="
        background:#FFFFFF;
        border:1px solid #E5E7EB;
        border-radius:14px;
        padding:20px 24px;
        margin-bottom:4px;
        box-shadow:0 1px 4px rgba(0,0,0,0.04);
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <span style="font-size:1.5rem;">🔒</span>
            <div>
                <div style="font-weight:700;font-size:0.95rem;color:#1F2937;">Lock del Runner ETL</div>
                <div style="font-size:0.75rem;color:#64748B;">Controla el acceso exclusivo al pipeline</div>
            </div>
            <div style="margin-left:auto;font-size:1.6rem;">{dot}</div>
        </div>
        <div style="
            background:{color}11;border:1px solid {color}33;
            border-radius:8px;padding:10px 14px;
            font-size:0.84rem;color:#374151;
        ">
            {descripcion}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Detalles adicionales si el backend los trae
    if lock_info and isinstance(lock_info, dict) and "error" not in lock_info:
        with st.expander("🔎 Detalles del lock", expanded=False):
            cols = st.columns(3)
            campos = [
                ("ID Corrida",     lock_info.get("id_corrida",   "—")),
                ("Iniciado por",   lock_info.get("iniciado_por", "—")),
                ("Desde",          lock_info.get("fecha_inicio", "—")),
            ]
            for col, (lbl, val) in zip(cols, campos):
                col.metric(lbl, str(val)[:30] if val else "—")


# ── Panel de base de datos ────────────────────────────────────────────────────

def _render_panel_bd(datos_full: dict) -> None:
    bd = datos_full.get("base_datos") or {}
    if not bd:
        return

    conectado  = bd.get("conectado", False)
    base       = bd.get("base_datos", "—")
    version    = bd.get("version",    "—")
    latencia   = bd.get("latencia_ms","—")
    error_bd   = bd.get("error")

    color  = "#10B981" if conectado else "#EF4444"
    icono  = "✅"       if conectado else "❌"

    base_safe    = html.escape(str(base))
    version_safe = html.escape(str(version))
    latencia_txt = "—" if latencia == "—" else html.escape(f"{latencia} ms")
    error_html   = (
        f'<div style="margin-top:12px;font-size:0.8rem;color:#DC2626;'
        f'background:#FEF2F2;border-radius:6px;padding:8px 12px;">'
        f'{html.escape(str(error_bd))}</div>'
        if error_bd else ""
    )

    st.markdown(f"""
    <div style="
        background:#FFFFFF;border:1px solid #E5E7EB;
        border-radius:14px;padding:20px 24px;
        box-shadow:0 1px 4px rgba(0,0,0,0.04);
        margin-bottom:4px;
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
            <span style="font-size:1.4rem;">🗄️</span>
            <div style="font-weight:700;font-size:0.95rem;color:#1F2937;">SQL Server · Detalle</div>
            <span style="margin-left:auto;font-size:1.3rem;">{icono}</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div style="background:#F8FAFC;border-radius:8px;padding:10px 12px;">
                <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;
                            letter-spacing:0.7px;font-weight:700;">Base</div>
                <div style="font-size:0.88rem;font-weight:600;color:#1F2937;
                            margin-top:3px;overflow:hidden;text-overflow:ellipsis;
                            white-space:nowrap;">{base_safe}</div>
            </div>
            <div style="background:#F8FAFC;border-radius:8px;padding:10px 12px;">
                <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;
                            letter-spacing:0.7px;font-weight:700;">Versión</div>
                <div style="font-size:0.88rem;font-weight:600;color:#1F2937;margin-top:3px;">{version_safe}</div>
            </div>
            <div style="background:#F8FAFC;border-radius:8px;padding:10px 12px;">
                <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;
                            letter-spacing:0.7px;font-weight:700;">Latencia</div>
                <div style="font-size:0.88rem;font-weight:600;color:{color};margin-top:3px;">
                    {latencia_txt}
                </div>
            </div>
        </div>
        {error_html}
    </div>
    """, unsafe_allow_html=True)


# ── Panel control-plane ───────────────────────────────────────────────────────

def _render_panel_control(datos_control: dict) -> None:
    cp = datos_control.get("control_plane") or {}
    if not cp:
        return

    estado_cp = str(cp.get("estado", "—"))
    resumen   = cp.get("resumen") or {}
    lock_cp   = cp.get("lock")    or {}

    sano  = estado_cp.lower() == "operativo"
    color = "#10B981" if sano else "#F59E0B"

    resumen_html = ""
    if resumen and isinstance(resumen, dict):
        items = []
        for k, v in list(resumen.items())[:6]:
            etiqueta = html.escape(str(k).replace("_", " ").capitalize())
            valor    = html.escape(str(v))
            items.append(
                f"<div style='background:#F8FAFC;border-radius:6px;padding:8px 12px;'>"
                f"<div style='font-size:0.65rem;color:#64748B;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.6px;'>{etiqueta}</div>"
                f"<div style='font-size:0.9rem;font-weight:600;color:#1F2937;margin-top:2px;'>{valor}</div>"
                f"</div>"
            )
        resumen_html = (
            f"<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px;'>"
            + "".join(items) +
            "</div>"
        )

    estado_cp_safe = html.escape(estado_cp.upper())
    st.markdown(f"""
    <div style="
        background:#FFFFFF;border:1px solid #E5E7EB;
        border-radius:14px;padding:20px 24px;
        box-shadow:0 1px 4px rgba(0,0,0,0.04);
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <span style="font-size:1.4rem;">🧩</span>
            <div style="font-weight:700;font-size:0.95rem;color:#1F2937;">Control-Plane · Resumen</div>
            <div style="margin-left:auto;
                background:{color}22;color:{color};border:1px solid {color}44;
                border-radius:20px;padding:2px 10px;font-size:0.75rem;font-weight:700;">
                {estado_cp_safe}
            </div>
        </div>
        {resumen_html}
    </div>
    """, unsafe_allow_html=True)


# ── Historial de la sesión ────────────────────────────────────────────────────

def _registrar_historial(estado_general: str) -> None:
    if "health_historial" not in st.session_state:
        st.session_state["health_historial"] = []

    st.session_state["health_historial"].append({
        "hora":   datetime.now().strftime("%H:%M:%S"),
        "estado": estado_general,
    })

    # Mantener solo las últimas N entradas
    if len(st.session_state["health_historial"]) > _HISTORIAL_MAX:
        st.session_state["health_historial"] = st.session_state["health_historial"][-_HISTORIAL_MAX:]


def _render_historial() -> None:
    historial = st.session_state.get("health_historial", [])
    if not historial:
        return

    with st.expander("🕒 Historial de checks en esta sesión", expanded=False):
        items_html = ""
        for entry in reversed(historial):
            estado = entry["estado"]
            color  = "#10B981" if estado == "OK" else "#EF4444"
            dot    = "🟢" if estado == "OK" else "🔴"
            items_html += (
                f"<div style='display:flex;align-items:center;gap:10px;"
                f"padding:6px 0;border-bottom:1px solid #F1F5F8;font-size:0.84rem;'>"
                f"<span>{dot}</span>"
                f"<span style='color:#64748B;font-family:monospace;'>{entry['hora']}</span>"
                f"<span style='color:{color};font-weight:600;'>{estado}</span>"
                f"</div>"
            )
        st.markdown(
            f"<div style='padding:4px 0;'>{items_html}</div>",
            unsafe_allow_html=True,
        )


# ── Auto-refresh ──────────────────────────────────────────────────────────────

def _render_autorefresh() -> None:
    with st.sidebar:
        st.markdown(
            "<div style='font-size:0.7rem;font-weight:700;color:#9CA3AF;"
            "text-transform:uppercase;letter-spacing:1.2px;padding:12px 0 4px 0;'>"
            "Auto-refresh</div>",
            unsafe_allow_html=True,
        )
        intervalo = st.select_slider(
            "Intervalo",
            options=AUTOREFRESH_OPCIONES,
            value=st.session_state.get("health_refresh_interval", 0),
            format_func=lambda x: "Off" if x == 0 else f"{x}s",
            key="health_refresh_interval",
            label_visibility="collapsed",
        )

    if intervalo > 0:
        import time
        ultima = st.session_state.get("health_last_refresh", 0)
        ahora  = time.time()
        if ahora - ultima >= intervalo:
            st.session_state["health_last_refresh"] = ahora
            st.rerun()


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    header_pagina("🖥️", "Sistema · Health", "Estado en tiempo real de todos los subsistemas ACP")

    if not tiene_permiso("leer"):
        st.error("Acceso denegado. Se requiere al menos rol Viewer.")
        return

    _render_autorefresh()

    col_acc1, col_acc2, col_acc3 = st.columns([1, 1, 4])
    with col_acc1:
        if st.button("🔄 Actualizar ahora", key="btn_health_reload", type="primary"):
            st.rerun()
    with col_acc2:
        ts_actual = datetime.now().strftime("%H:%M:%S")
        st.markdown(
            f"<div style='padding:8px 0;font-size:0.8rem;color:#64748B;'>Última consulta: {ts_actual}</div>",
            unsafe_allow_html=True,
        )

    # ── 1. Consultar todos los subsistemas en paralelo (secuencial aquí, rápido) ──
    resultados: dict[str, dict] = {}
    with st.spinner("Verificando subsistemas…"):
        for sub in _SUBSISTEMAS:
            resultados[sub["key"]] = _consultar(sub["endpoint"])

        datos_full    = _consultar("/health")
        datos_lock    = _consultar("/health/lock")
        datos_control = _consultar("/health/ready/control")

    # ── 2. Estado general ──────────────────────────────────────────────────────
    todos_sanos = all(_es_sano(v) for v in resultados.values())
    estado_general = "OK" if todos_sanos else "DEGRADADO"
    _registrar_historial(estado_general)

    color_general = "#10B981" if todos_sanos else "#F59E0B"
    icono_general = "✅ Todo operativo" if todos_sanos else "⚠️ Hay subsistemas con problemas"

    st.markdown(f"""
    <div style="
        background:{'#F0FDF4' if todos_sanos else '#FFFBEB'};
        border:1px solid {'#BBF7D0' if todos_sanos else '#FDE68A'};
        border-left:5px solid {color_general};
        border-radius:12px;padding:14px 20px;margin-bottom:24px;
        display:flex;align-items:center;gap:12px;
        animation:fadeIn 0.3s ease;
    ">
        <span style="font-size:1.4rem;">{'🟢' if todos_sanos else '🟡'}</span>
        <div>
            <div style="font-weight:700;font-size:0.95rem;color:#1F2937;">{icono_general}</div>
            <div style="font-size:0.78rem;color:#64748B;margin-top:2px;">
                {len(_SUBSISTEMAS)} subsistemas verificados · {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 3. Tarjetas de subsistemas ─────────────────────────────────────────────
    st.markdown("### 🔌 Estado de subsistemas")
    cols = st.columns(len(_SUBSISTEMAS))
    for col, sub in zip(cols, _SUBSISTEMAS):
        with col:
            _render_tarjeta_subsistema(sub, resultados[sub["key"]])

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # ── 4. Panels de detalle ───────────────────────────────────────────────────
    st.markdown("### 🔍 Diagnóstico detallado")

    col_bd, col_lock = st.columns(2)
    with col_bd:
        _render_panel_bd(datos_full)
    with col_lock:
        _render_panel_lock(datos_lock)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    _render_panel_control(datos_control)

    # ── 5. Historial de la sesión ──────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    _render_historial()

    # ── 6. Info de versión ─────────────────────────────────────────────────────
    version   = html.escape(str(datos_full.get("version",  "—")))
    entorno   = html.escape(str(datos_full.get("entorno",  "—")).upper())
    servicio  = html.escape(str(datos_full.get("servicio", "—")))

    st.markdown(f"""
    <div style="
        margin-top:24px;
        border-top:1px solid #E5E7EB;padding-top:14px;
        display:flex;gap:24px;flex-wrap:wrap;
        font-size:0.76rem;color:#94A3B8;
    ">
        <span>🏷️ Servicio: <b style="color:#64748B;">{servicio}</b></span>
        <span>📦 Versión: <b style="color:#64748B;">{version}</b></span>
        <span>🌍 Entorno: <b style="color:#64748B;">{entorno}</b></span>
        <span style="margin-left:auto;">ACP Equipo de Proyecciones · 2026</span>
    </div>
    """, unsafe_allow_html=True)
