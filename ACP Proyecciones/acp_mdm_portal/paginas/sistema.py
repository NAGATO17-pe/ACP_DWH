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
import streamlit.components.v1 as components

from utils.api_client import get_api, obtener_url_backend
from utils.auth import tiene_permiso
from utils.componentes import badge_html, estado_vacio_html, banner_aviso
from utils.formato import header_pagina

# URL del API (misma que usa api_client para SSE y health)
from utils.api_client import get_api, URL_BACKEND
from utils.auth import tiene_permiso
from utils.componentes import badge_html, estado_vacio_html
from utils.constantes import AUTOREFRESH_OPCIONES, LOCK_ESTADOS as _LOCK_ESTADOS
from utils.formato import crear_tarjeta_kpi, header_pagina

# ── Constantes ────────────────────────────────────────────────────────────────

_BASE_URL = URL_BACKEND

_SUBSISTEMAS = [
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

_LOCK_ESTADOS: dict[str, tuple[str, str, str]] = {
    "libre":    ("🟢", "#2db87a", "Sin corridas activas. Listo para ejecutar."),
    "ocupado":  ("🟡", "#e8a020", "Una corrida está en ejecución actualmente."),
    "vencido":  ("🔴", "#EF4444", "El lock lleva demasiado tiempo activo. Posible corrida colgada."),
    "error":    ("🔴", "#EF4444", "No se pudo leer el estado del lock."),
    "no_listo": ("⚪", "#8fa897", "Control-plane o BD no disponibles."),
}

_HISTORIAL_MAX = 10  # entradas de historial en la sesión


# ── Helpers de consulta ───────────────────────────────────────────────────────

def _consultar(endpoint: str) -> dict[str, Any]:
    """Llama a un endpoint del backend y devuelve el dict de respuesta."""
    resultado = get_api(endpoint, base_url=obtener_url_backend())
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
    color  = "#2db87a" if sano else "#EF4444"
    bg     = "rgba(45,184,122,0.06)" if sano else "rgba(239,68,68,0.06)"
    borde  = "rgba(45,184,122,0.22)" if sano else "rgba(239,68,68,0.22)"
    dot    = "🟢" if sano else "🔴"

    # Latencia (solo si el endpoint la trae)
    bd     = datos.get("base_datos") or {}
    lat    = bd.get("latencia_ms", "")
    lat_txt = f"<span style='color:#8fa897;font-size:0.75rem;'> · {lat} ms</span>" if lat else ""

    estado_safe = html.escape(str(estado).upper())
    st.markdown(f"""
    <div style="
        background:{bg};
        border:1px solid {borde};
        border-top:2px solid {color};
        border-radius:12px;
        padding:16px 18px;
        height:100%;
        box-sizing:border-box;
        animation: fadeIn 0.3s ease;
    ">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
            <span style="font-size:1.25rem;">{cfg['icono']}</span>
            <span style="font-weight:700;font-size:0.9rem;color:#e8f0ec;">{cfg['label']}</span>
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
        <p style="margin:0;font-size:0.78rem;color:#8fa897;line-height:1.4;">
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
        background:rgba(26,46,30,0.35);
        border:1px solid rgba(255,255,255,0.08);
        border-radius:14px;
        padding:20px 24px;
        margin-bottom:4px;
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
            <span style="font-size:1.5rem;">🔒</span>
            <div>
                <div style="font-weight:700;font-size:0.95rem;color:#e8f0ec;">Lock del Runner ETL</div>
                <div style="font-size:0.75rem;color:#8fa897;">Controla el acceso exclusivo al pipeline</div>
            </div>
            <div style="margin-left:auto;font-size:1.6rem;">{dot}</div>
        </div>
        <div style="
            background:{color}15;border:1px solid {color}35;
            border-radius:8px;padding:10px 14px;
            font-size:0.84rem;color:#e8f0ec;
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
                ("ID Corrida",   lock_info.get("id_corrida",   "—")),
                ("Iniciado por", lock_info.get("iniciado_por", "—")),
                ("Desde",        lock_info.get("fecha_inicio", "—")),
            ]
            for col, (lbl, val) in zip(cols, campos):
                val_txt = str(val)[:30] if val else "—"
                col.markdown(
                    f"<div style='font-size:0.65rem;color:#8fa897;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:0.8px;margin-bottom:4px;'>{lbl}</div>"
                    f"<div style='font-size:0.95rem;font-weight:600;color:#e8f0ec;"
                    f"font-family:JetBrains Mono,monospace;'>{val_txt}</div>",
                    unsafe_allow_html=True,
                )


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

    color  = "#2db87a" if conectado else "#EF4444"
    icono  = "✅"       if conectado else "❌"

    base_safe    = html.escape(str(base))
    version_safe = html.escape(str(version))
    latencia_txt = "—" if latencia == "—" else html.escape(f"{latencia} ms")
    error_html   = (
        f'<div style="margin-top:12px;font-size:0.8rem;color:#EF4444;'
        f'background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:6px;padding:8px 12px;">'
        f'{html.escape(str(error_bd))}</div>'
        if error_bd else ""
    )

    st.markdown(f"""
    <div style="
        background:rgba(26,46,30,0.35);border:1px solid rgba(255,255,255,0.08);
        border-radius:14px;padding:20px 24px;
        margin-bottom:4px;
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
            <span style="font-size:1.4rem;">🗄️</span>
            <div style="font-weight:700;font-size:0.95rem;color:#e8f0ec;">SQL Server · Detalle</div>
            <span style="margin-left:auto;font-size:1.3rem;">{icono}</span>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
            <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 12px;">
                <div style="font-size:0.65rem;color:#8fa897;text-transform:uppercase;
                            letter-spacing:0.7px;font-weight:700;">Base</div>
                <div style="font-size:0.88rem;font-weight:600;color:#e8f0ec;
                            margin-top:3px;overflow:hidden;text-overflow:ellipsis;
                            white-space:nowrap;">{base_safe}</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 12px;">
                <div style="font-size:0.65rem;color:#8fa897;text-transform:uppercase;
                            letter-spacing:0.7px;font-weight:700;">Versión</div>
                <div style="font-size:0.88rem;font-weight:600;color:#e8f0ec;margin-top:3px;">{version_safe}</div>
            </div>
            <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:10px 12px;">
                <div style="font-size:0.65rem;color:#8fa897;text-transform:uppercase;
                            letter-spacing:0.7px;font-weight:700;">Latencia</div>
                <div style="font-size:0.88rem;font-weight:600;color:{color};margin-top:3px;font-family:'JetBrains Mono',monospace;">
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
    color = "#2db87a" if sano else "#e8a020"

    resumen_html = ""
    if resumen and isinstance(resumen, dict):
        items = []
        for k, v in list(resumen.items())[:6]:
            etiqueta = html.escape(str(k).replace("_", " ").capitalize())
            valor    = html.escape(str(v))
            items.append(
                f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);border-radius:6px;padding:8px 12px;'>"
                f"<div style='font-size:0.65rem;color:#8fa897;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.6px;'>{etiqueta}</div>"
                f"<div style='font-size:0.9rem;font-weight:600;color:#e8f0ec;margin-top:2px;'>{valor}</div>"
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
        background:rgba(26,46,30,0.35);border:1px solid rgba(255,255,255,0.08);
        border-radius:14px;padding:20px 24px;
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
            <span style="font-size:1.4rem;">🧩</span>
            <div style="font-weight:700;font-size:0.95rem;color:#e8f0ec;">Control-Plane · Resumen</div>
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
            color  = "#2db87a" if estado == "OK" else "#EF4444"
            dot    = "🟢" if estado == "OK" else "🔴"
            items_html += (
                f"<div style='display:flex;align-items:center;gap:10px;"
                f"padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.84rem;'>"
                f"<span>{dot}</span>"
                f"<span style='color:#8fa897;font-family:monospace;'>{entry['hora']}</span>"
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
            "<div style='font-size:0.7rem;font-weight:700;color:rgba(255,255,255,0.35);"
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


# ── Dashboard SSR — Telemetría en Vivo ────────────────────────────────────────

def _generar_dashboard_ssr(token: str) -> str:
    """
    Retorna un documento HTML completo que abre un EventSource al endpoint SSE
    /health/telemetria/stream y actualiza 4 métricas en tiempo real:
      · Latencia SQL Server (ms)
      · Corridas activas (PENDIENTE/EJECUTANDO)
      · Comandos en cola
      · Timestamp del servidor
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    font-family: 'Inter', sans-serif;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px;
    height: 100vh;
    overflow: hidden;
    color: #e8f0ec;
  }}

  /* ── Status bar ── */
  .status-bar {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.72rem;
    color: #8fa897;
    padding: 8px 14px;
    background: rgba(5, 15, 8, 0.5);
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.07);
  }}
  .status-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #4d6b54;
    transition: background 0.4s ease;
    flex-shrink: 0;
  }}
  .status-dot.live {{ background: #2db87a; box-shadow: 0 0 0 3px rgba(45,184,122,0.2); }}
  .status-dot.error {{ background: #EF4444; }}
  .status-timestamp {{ margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #8fa897; }}

  /* ── Cards grid ── */
  .cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    flex: 1;
  }}
  .card {{
    background: rgba(26, 46, 30, 0.5);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 16px 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    position: relative;
    overflow: hidden;
  }}
  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--card-color, #4d6b54);
    border-radius: 12px 12px 0 0;
  }}
  .card .icon {{ font-size: 1.6rem; opacity: 0.75; }}
  .card .label {{
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8fa897;
    font-weight: 700;
    text-align: center;
  }}
  .card .value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--card-color, #e8f0ec);
    line-height: 1;
    transition: color 0.3s ease, opacity 0.3s ease;
  }}
  .card .sub {{
    font-size: 0.65rem;
    color: #8fa897;
    text-align: center;
  }}

  /* Colores por card — paleta verde-tierra */
  .card-latencia  {{ --card-color: #2db87a; }}
  .card-corridas  {{ --card-color: #e8a020; }}
  .card-cola      {{ --card-color: #8fa897; }}
  .card-tiempo    {{ --card-color: #4d6b54; }}

  /* Animación de pulso en actualización */
  @keyframes valuePulse {{
    0%   {{ transform: scale(1);   opacity: 1;   }}
    50%  {{ transform: scale(1.06); opacity: 0.6; }}
    100% {{ transform: scale(1);   opacity: 1;   }}
  }}
  .pulse {{ animation: valuePulse 0.35s ease; }}

  /* Badge de estado en corridas */
  .badge-activo {{
    background: rgba(232,160,32,0.12);
    color: #e8a020;
    border-radius: 99px;
    padding: 2px 8px;
    font-size: 0.62rem;
    font-weight: 700;
  }}
  .badge-idle {{
    background: rgba(45,184,122,0.12);
    color: #2db87a;
    border-radius: 99px;
    padding: 2px 8px;
    font-size: 0.62rem;
    font-weight: 700;
  }}
</style>
</head>
<body>

<!-- Status bar -->
<div class="status-bar">
  <div class="status-dot" id="dot"></div>
  <span id="status-txt">Conectando al backend…</span>
  <span class="status-timestamp" id="srv-ts">—</span>
</div>

<!-- 4 Metric cards -->
<div class="cards">

  <div class="card card-latencia">
    <span class="icon">🗄️</span>
    <div class="label">Latencia SQL</div>
    <div class="value" id="val-latencia">—</div>
    <div class="sub">ms (round-trip)</div>
  </div>

  <div class="card card-corridas">
    <span class="icon">⚙️</span>
    <div class="label">Corridas Activas</div>
    <div class="value" id="val-corridas">—</div>
    <div class="sub" id="badge-corridas">PENDIENTE / EJECUTANDO</div>
  </div>

  <div class="card card-cola">
    <span class="icon">📬</span>
    <div class="label">Cola de Comandos</div>
    <div class="value" id="val-cola">—</div>
    <div class="sub" id="badge-cola">pendientes · procesando</div>
  </div>

  <div class="card card-tiempo">
    <span class="icon">🕐</span>
    <div class="label">Hora Servidor</div>
    <div class="value" id="val-hora" style="font-size:1.1rem;">—</div>
    <div class="sub">UTC · Sincronizado</div>
  </div>

</div>

<script>
const SSE_URL  = "{obtener_url_backend()}/health/telemetria/stream";
const TOKEN    = "{token}";

const dot       = document.getElementById('dot');
const statusTxt = document.getElementById('status-txt');
const srvTs     = document.getElementById('srv-ts');

const elLatencia = document.getElementById('val-latencia');
const elCorridas = document.getElementById('val-corridas');
const elBadgeCor = document.getElementById('badge-corridas');
const elCola     = document.getElementById('val-cola');
const elBadgeCola= document.getElementById('badge-cola');
const elHora     = document.getElementById('val-hora');

function animarCambio(el, nuevoValor) {{
  if (el.textContent === nuevoValor) return;
  el.textContent = nuevoValor;
  el.classList.remove('pulse');
  void el.offsetWidth; // reflow para reiniciar animación
  el.classList.add('pulse');
  el.addEventListener('animationend', () => el.classList.remove('pulse'), {{ once: true }});
}}

function conectar() {{
  const headers = TOKEN ? {{ 'Authorization': 'Bearer ' + TOKEN }} : {{}};
  // EventSource nativo no soporta headers personalizados en algunos browsers,
  // pero el endpoint de telemetría no requiere autenticación.
  const es = new EventSource(SSE_URL);

  es.addEventListener('telemetria', (e) => {{
    try {{
      const data = JSON.parse(e.data);

      // Status bar
      dot.className = 'status-dot ' + (data.conectado ? 'live' : 'error');
      statusTxt.textContent = data.conectado
        ? `Conectado · SQL Server ${{data.version_sql || ''}}`
        : '⚠️ Sin conexión a SQL Server';

      // Timestamp del servidor (extraer solo HH:MM:SS de ISO)
      if (data.timestamp) {{
        const ts = new Date(data.timestamp);
        srvTs.textContent = ts.toISOString().substring(11, 19) + ' UTC';
        animarCambio(elHora, ts.toISOString().substring(11, 19));
      }}

      // Latencia
      const lat = data.latencia_ms;
      animarCambio(elLatencia, lat !== null && lat !== undefined ? String(lat) : '—');

      // Corridas activas
      const cor = data.corridas_activas ?? 0;
      animarCambio(elCorridas, String(cor));
      elBadgeCor.innerHTML = cor > 0
        ? `<span class="badge-activo">${{cor}} en ejecución</span>`
        : '<span class="badge-idle">Sistema libre</span>';

      // Cola de comandos
      const pend = data.comandos_pendientes ?? 0;
      const proc = data.comandos_procesando ?? 0;
      animarCambio(elCola, String(pend + proc));
      elBadgeCola.textContent = `${{pend}} pend. · ${{proc}} proc.`;

    }} catch(err) {{
      console.error('Error parseando telemetría:', err);
    }}
  }});

  es.addEventListener('error', (e) => {{
    dot.className = 'status-dot error';
    statusTxt.textContent = '⚠️ Reconectando…';
    // EventSource reintenta automáticamente
  }});
}}

conectar();
</script>
</body>
</html>"""



def _generar_dashboard_calidad_ssr(token: str) -> str:
    """
    Dashboard SSR para Observabilidad de Calidad.
    Se conecta a /health/calidad/stream y muestra errores de hoy, top tipos y fundos.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: transparent;
    font-family: 'Inter', sans-serif;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 20px;
    height: 100vh;
    overflow: hidden;
    color: #e8f0ec;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    padding-bottom: 12px;
  }}
  .title {{ font-size: 0.95rem; font-weight: 700; color: #e8f0ec; }}
  .status {{ font-size: 0.7rem; color: #8fa897; display: flex; align-items: center; gap: 6px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #4d6b54; }}
  .dot.live {{ background: #2db87a; box-shadow: 0 0 0 3px rgba(45,184,122,0.2); }}

  .grid {{
    display: grid;
    grid-template-columns: 1.2fr 2fr 2fr;
    gap: 16px;
    height: 100%;
  }}
  .card {{
    background: rgba(26, 46, 30, 0.5);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    padding: 18px;
    display: flex;
    flex-direction: column;
  }}
  .card-label {{ font-size: 0.65rem; font-weight: 700; color: #8fa897; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 1px; }}
  .big-val {{ font-family: 'JetBrains Mono', monospace; font-size: 3.8rem; font-weight: 700; color: #EF4444; line-height: 1; }}
  .list-item {{
    display: flex;
    justify-content: space-between;
    padding: 9px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 0.78rem;
  }}
  .list-item:last-child {{ border: 0; }}
  .item-name {{ color: #e8f0ec; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 72%; }}
  .item-count {{ background: rgba(232,160,32,0.12); padding: 2px 10px; border-radius: 6px; font-weight: 700; color: #e8a020; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; flex-shrink: 0; }}

  @keyframes pulse {{
    0% {{ opacity: 1; }}
    50% {{ opacity: 0.5; }}
    100% {{ opacity: 1; }}
  }}
  .updating {{ animation: pulse 0.5s ease-in-out; }}
</style>
</head>
<body>
  <div class="header">
    <div class="title">🛡️ Observabilidad de Calidad (Capa Bronce)</div>
    <div class="status">
      <div class="dot" id="dot"></div>
      <span id="status-txt">Sincronizando...</span>
    </div>
  </div>

  <div class="grid">
    <!-- Card 1: Total hoy -->
    <div class="card">
      <div class="card-label">🚨 Errores de Hoy</div>
      <div style="flex:1; display:flex; align-items:center; justify-content:center;">
        <div class="big-val" id="val-total">0</div>
      </div>
      <div style="font-size:0.65rem; color:#94A3B8; text-align:center;">Registros rechazados hoy</div>
    </div>

    <!-- Card 2: Top Tipos -->
    <div class="card">
      <div class="card-label">📊 Tipos de Error Críticos</div>
      <div id="list-tipos" style="flex:1;">
        <div style="color:#CBD5E1; font-size:0.7rem; padding-top:20px; text-align:center;">Esperando datos...</div>
      </div>
    </div>

    <!-- Card 3: Top Fundos -->
    <div class="card">
      <div class="card-label">📍 Fundos con Incidencias</div>
      <div id="list-fundos" style="flex:1;">
        <div style="color:#CBD5E1; font-size:0.7rem; padding-top:20px; text-align:center;">Esperando datos...</div>
      </div>
    </div>
  </div>

<script>
const SSE_URL = "{obtener_url_backend()}/health/calidad/stream";
const dot = document.getElementById('dot');
const statusTxt = document.getElementById('status-txt');
const valTotal = document.getElementById('val-total');
const listTipos = document.getElementById('list-tipos');
const listFundos = document.getElementById('list-fundos');

function updateList(container, data, keyName) {{
  if (!data || data.length === 0) {{
    container.innerHTML = '<div style="color:#CBD5E1; font-size:0.7rem; padding-top:20px; text-align:center;">Sin incidencias hoy ✨</div>';
    return;
  }}
  container.innerHTML = data.map(item => `
    <div class="list-item">
      <span class="item-name" title="${{item[keyName]}}">${{item[keyName]}}</span>
      <span class="item-count">${{item.Cuenta}}</span>
    </div>
  `).join('');
}}

function conectar() {{
  const es = new EventSource(SSE_URL);

  es.addEventListener('calidad', (e) => {{
    const data = JSON.parse(e.data);
    dot.className = 'dot live';
    statusTxt.textContent = 'En vivo · Actualizado ' + new Date().toLocaleTimeString();
    
    // Animar cambio
    valTotal.classList.add('updating');
    valTotal.textContent = data.total_hoy;
    setTimeout(() => valTotal.classList.remove('updating'), 500);

    updateList(listTipos, data.top_tipos, 'Tipo_Error_Raw');
    updateList(listFundos, data.top_fundos, 'Fundo_Raw');
  }});

  es.addEventListener('error', () => {{
    dot.className = 'dot';
    statusTxt.textContent = '⚠️ Reconectando...';
  }});
}}

conectar();
</script>
</body>
</html>"""


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:

    header_pagina("🖥️", "Sistema · Health", "Estado en tiempo real de todos los subsistemas ACP")

    if not tiene_permiso("leer"):
        st.error("Acceso denegado. Se requiere al menos rol Viewer.")
        return

    _render_autorefresh()

    # ── Consultar todos los subsistemas ──────────────────────────────────────
    resultados: dict[str, dict] = {}
    with st.spinner("Verificando subsistemas…"):
        for sub in _SUBSISTEMAS:
            resultados[sub["key"]] = _consultar(sub["endpoint"])

        datos_full    = _consultar("/health")
        datos_lock    = _consultar("/health/lock")
        datos_control = _consultar("/health/ready/control")

    todos_sanos    = all(_es_sano(v) for v in resultados.values())
    estado_general = "OK" if todos_sanos else "DEGRADADO"
    _registrar_historial(estado_general)

    # ════════════════════════════════════════════════════════════════════════
    # ZONA 1 — ANSWER FIRST
    # Banner dominante + tarjetas de subsistemas + botón de acción primaria
    # ════════════════════════════════════════════════════════════════════════
    ts_actual     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    icono_general = "✅ Todo operativo" if todos_sanos else "⚠️ Subsistemas con problemas"
    bg_banner     = "rgba(45,184,122,0.07)"  if todos_sanos else "rgba(232,160,32,0.07)"
    bd_banner     = "rgba(45,184,122,0.28)"  if todos_sanos else "rgba(232,160,32,0.28)"
    dot_banner    = "🟢"                     if todos_sanos else "🟡"
    n_ok          = sum(1 for v in resultados.values() if _es_sano(v))
    n_total       = len(_SUBSISTEMAS)

    # Fila superior: banner a la izquierda, botón alineado a la derecha
    col_banner, col_btn = st.columns([5, 1])
    with col_banner:
        st.markdown(f"""
        <div style="
            background:{bg_banner};
            border:1px solid {bd_banner};
            border-radius:14px;
            padding:18px 24px;
            display:flex;align-items:center;gap:14px;
        ">
            <span style="font-size:2rem;line-height:1;">{dot_banner}</span>
            <div style="flex:1;">
                <div style="font-weight:700;font-size:1.05rem;color:#e8f0ec;margin-bottom:3px;">
                    {icono_general}
                </div>
                <div style="font-size:0.78rem;color:#8fa897;">
                    {n_ok} de {n_total} subsistemas operativos · Consultado {ts_actual}
                </div>
            </div>
            <div style="
                background:{'rgba(45,184,122,0.15)' if todos_sanos else 'rgba(232,160,32,0.15)'};
                color:{'#2db87a' if todos_sanos else '#e8a020'};
                border:1px solid {'rgba(45,184,122,0.4)' if todos_sanos else 'rgba(232,160,32,0.4)'};
                border-radius:99px;padding:4px 14px;
                font-size:0.75rem;font-weight:700;letter-spacing:0.5px;
            ">
                {estado_general}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_btn:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Actualizar", key="btn_health_reload", type="primary", use_container_width=True):
            st.rerun()

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # Tarjetas de subsistemas — siempre visibles (responden la pregunta principal)
    cols = st.columns(n_total)
    for col, sub in zip(cols, _SUBSISTEMAS):
        with col:
            _render_tarjeta_subsistema(sub, resultados[sub["key"]])

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # ZONA 2 — DIAGNÓSTICO (colapsado por defecto; expandido si hay errores)
    # ════════════════════════════════════════════════════════════════════════
    with st.expander(
        "🔍 Diagnóstico detallado — BD · Lock · Control-Plane · Historial",
        expanded=not todos_sanos,
    ):
        col_bd, col_lock = st.columns(2)
        with col_bd:
            _render_panel_bd(datos_full)
        with col_lock:
            _render_panel_lock(datos_lock)

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        _render_panel_control(datos_control)
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        _render_historial()

    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # ZONA 3 — TELEMETRÍA EN VIVO (tabs SSR)
    # ════════════════════════════════════════════════════════════════════════
    token_jwt = st.session_state.get("jwt_token", "")

    tab_gen, tab_cal = st.tabs(["📡 Telemetría en vivo", "🛡️ Calidad de datos (real-time)"])

    with tab_gen:
        st.caption(
            "Dashboard SSR — se conecta directamente al backend vía Server-Sent Events. "
            "Actualiza latencia, corridas y cola cada 3 segundos **sin recargar el portal**."
        )
        components.html(
            _generar_dashboard_ssr(token_jwt),
            height=320,
            scrolling=False,
        )

    with tab_cal:
        st.caption(
            "Métricas en tiempo real desde `Bronce.Seguimiento_Errores`. "
            "Un pico en un Fundo específico indica problema en el archivo de origen."
        )
        components.html(
            _generar_dashboard_calidad_ssr(token_jwt),
            height=380,
            scrolling=False,
        )
        banner_aviso(
            "Esta información proviene de `Bronce.Seguimiento_Errores`. "
            "Si ves un pico de errores en un Fundo específico, verifica el archivo de origen."
        )

    # ── Footer de versión ──────────────────────────────────────────────────
    version  = html.escape(str(datos_full.get("version",  "—")))
    entorno  = html.escape(str(datos_full.get("entorno",  "—")).upper())
    servicio = html.escape(str(datos_full.get("servicio", "—")))

    st.markdown(f"""
    <div style="
        margin-top:28px;
        border-top:1px solid rgba(255,255,255,0.07);
        padding-top:14px;
        display:flex;gap:24px;flex-wrap:wrap;
        font-size:0.76rem;color:#8fa897;
    ">
        <span>🏷️ Servicio: <b style="color:#e8f0ec;">{servicio}</b></span>
        <span>📦 Versión: <b style="color:#e8f0ec;">{version}</b></span>
        <span>🌍 Entorno: <b style="color:#e8f0ec;">{entorno}</b></span>
        <span style="margin-left:auto;">ACP Equipo de Proyecciones · 2026</span>
    </div>
    """, unsafe_allow_html=True)

