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
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
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
    color: #F8FAFC;
  }}

  /* ── Status bar ── */
  .status-bar {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.72rem;
    color: #94A3B8;
    padding: 8px 14px;
    background: rgba(15, 23, 42, 0.4);
    backdrop-filter: blur(8px);
    border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
  }}
  .status-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #CBD5E1;
    transition: background 0.4s ease;
    flex-shrink: 0;
  }}
  .status-dot.live {{ background: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.2); }}
  .status-dot.error {{ background: #EF4444; }}
  .status-timestamp {{ margin-left: auto; font-family: monospace; font-size: 0.7rem; color: #94A3B8; }}

  /* ── Cards grid ── */
  .cards {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    flex: 1;
  }}
  .card {{
    background: rgba(30, 41, 59, 0.5);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px;
    padding: 16px 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    transition: all 0.3s ease;
  }}
  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--card-color, #E2E8F0);
    border-radius: 12px 12px 0 0;
  }}
  .card .icon {{ font-size: 1.6rem; opacity: 0.75; }}
  .card .label {{
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #94A3B8;
    font-weight: 700;
    text-align: center;
  }}
  .card .value {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--card-color, #F8FAFC);
    line-height: 1;
    transition: all 0.3s ease;
    text-shadow: 0 0 20px rgba(255,255,255,0.1);
  }}
  .card .sub {{
    font-size: 0.65rem;
    color: #CBD5E1;
    text-align: center;
  }}

  /* Colores por card */
  .card-latencia  {{ --card-color: #10B981; }}
  .card-corridas  {{ --card-color: #3B82F6; }}
  .card-cola      {{ --card-color: #F59E0B; }}
  .card-tiempo    {{ --card-color: #8B5CF6; }}

  /* Animación de pulso en actualización */
  @keyframes valuePulse {{
    0%   {{ transform: scale(1);   opacity: 1;   }}
    50%  {{ transform: scale(1.08); opacity: 0.7; }}
    100% {{ transform: scale(1);   opacity: 1;   }}
  }}
  .pulse {{ animation: valuePulse 0.35s ease; }}

  /* Badge de estado en corridas */
  .badge-activo {{
    background: rgba(59,130,246,0.12);
    color: #1D4ED8;
    border-radius: 99px;
    padding: 2px 8px;
    font-size: 0.62rem;
    font-weight: 700;
  }}
  .badge-idle {{
    background: rgba(16,185,129,0.12);
    color: #065F46;
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
const SSE_URL  = "http://127.0.0.1:8000/health/telemetria/stream";
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
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=Inter:wght@400;500&display=swap" rel="stylesheet">
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
    color: #F8FAFC;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding-bottom: 12px;
  }}
  .title {{ font-size: 0.95rem; font-weight: 700; color: #F8FAFC; font-family: 'Outfit', sans-serif; }}
  .status {{ font-size: 0.7rem; color: #94A3B8; display: flex; align-items: center; gap: 6px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #475569; }}
  .dot.live {{ background: #10B981; box-shadow: 0 0 0 3px rgba(16,185,129,0.2); }}

  .grid {{
    display: grid;
    grid-template-columns: 1.2fr 2fr 2fr;
    gap: 20px;
    height: 100%;
  }}
  .card {{
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  }}
  .card-label {{ font-size: 0.65rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 12px; letter-spacing: 1px; }}
  .big-val {{ font-family: 'Outfit', sans-serif; font-size: 3.8rem; font-weight: 700; color: #EF4444; line-height: 1; text-shadow: 0 0 30px rgba(239,68,68,0.2); }}
  .list-item {{
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-size: 0.78rem;
  }}
  .list-item:last-child {{ border: 0; }}
  .item-name {{ color: #CBD5E1; font-weight: 500; }}
  .item-count {{ background: rgba(255,255,255,0.05); padding: 2px 10px; border-radius: 6px; font-weight: 700; color: #F59E0B; }}
  
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
const SSE_URL = "http://127.0.0.1:8000/health/calidad/stream";
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
    # ── 3. Contenido Principal en Pestañas ──────────────────────────────────────
    tab_gen, tab_cal = st.tabs(["🖥️ Estado General", "📊 Calidad de Datos (Real-time)"])

    with tab_gen:
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

        # ── 7. Dashboard SSR — Telemetría en Vivo ──────────────────────────────
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.markdown("### 📡 Telemetría en Vivo")
        st.caption(
            "Dashboard SSR — se conecta directamente al backend vía Server-Sent Events. "
            "Actualiza latencia, corridas y cola cada 3 segundos **sin recargar el portal**."
        )
        token_jwt = st.session_state.get("jwt_token", "")
        components.html(
            _generar_dashboard_ssr(token_jwt),
            height=320,
            scrolling=False,
        )

    with tab_cal:
        st.markdown("### 🛡️ Observabilidad de Calidad")
        st.caption(
            "Métricas en tiempo real basadas en la tabla de errores de capa Bronce. "
            "Permite detectar anomalías de carga en el momento exacto en que ocurren."
        )
        token_jwt = st.session_state.get("jwt_token", "")
        components.html(
            _generar_dashboard_calidad_ssr(token_jwt),
            height=380,
            scrolling=False,
        )
        
        st.info(
            "💡 Esta información proviene de `Bronce.Seguimiento_Errores`. "
            "Si ves un pico de errores en un Fundo específico, verifica el archivo de origen."
        )

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

