"""
app.py — Portal MDM ACP Geographic Phenology (Enterprise)
Punto de entrada principal. Ejecutar con: streamlit run app.py
"""
import html
import importlib

import streamlit as st

from utils.auth import cerrar_sesion, login_gate, obtener_usuario, tiene_permiso
from utils.constantes import ROL_BADGES
from utils.formato import aplicar_css

st.set_page_config(
    page_title="ACP MDM Portal",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Login Gate ────────────────────────────────────────────────────────────────
# Si no está autenticado, muestra la pantalla de login y detiene la ejecución.
if not login_gate():
    st.stop()

# ── A partir de aquí, el usuario está autenticado ────────────────────────────
aplicar_css()

usuario = obtener_usuario()

# Escapa campos provenientes del backend antes de interpolar en HTML
_nombre_safe  = html.escape(str(usuario.get("nombre", "")))
_avatar_safe  = html.escape(str(usuario.get("avatar", "")))
_rol_label    = ROL_BADGES.get(usuario.get("rol", ""), usuario.get("rol", ""))
_rol_safe     = html.escape(str(_rol_label))

# ── Sidebar con secciones agrupadas ───────────────────────────────────────
with st.sidebar:
    # ── Header: Logo + info de usuario ──
    st.markdown(f"""
        <div class="sidebar-logo">
            <span style="font-size:1.4rem; line-height:1;">🌿</span>
            <h2>ACP MDM</h2>
        </div>
    """, unsafe_allow_html=True)

    # ── User card — compact ──
    st.markdown(f"""
        <div style="
            background: #F4F8F6;
            border: 1px solid #E9EEF2;
            border-radius: 8px;
            padding: 8px 12px;
            margin: 0 10px 8px 10px;
            display: flex;
            align-items: center;
            gap: 9px;
        ">
            <div style="
                font-size: 1.1rem; line-height: 1;
                background: rgba(27,107,90,0.1);
                border-radius: 6px;
                width: 30px; height: 30px;
                display: flex; align-items: center; justify-content: center;
                flex-shrink: 0;
            ">{_avatar_safe}</div>
            <div style="min-width:0; overflow:hidden;">
                <div style="font-size: 0.8rem; font-weight: 600; color: #1F2937;
                            white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{_nombre_safe}</div>
                <div style="font-size: 0.68rem; color: #6B7280;">{_rol_safe}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ── Navegación Unificada (Árbol de Opciones) ──
    opciones_navegacion = {
        "📊 PANEL PRINCIPAL": [
            "🏠  Inicio",
            "🔴  Cuarentena",
            "🔗  Homologación",
            "📋  Auditoría ETL",
        ],
        "📋 CATÁLOGOS MAESTROS": [
            "🍇  Variedades",
            "📍  Geografía",
            "👤  Personal",
        ],
    }
    
    # Agregar Sistema (health) — visible para todos los autenticados
    opciones_navegacion["🖥️ SISTEMA"] = [
        "🖥️  Sistema · Health",
    ]

    # Agregar Configuración solo si tiene permisos
    if tiene_permiso("configurar") or tiene_permiso("escribir"):
        opciones_navegacion["⚙️ CONFIGURACIÓN"] = [
            "📋  Reglas de Validación",
            "⚙️  Parámetros Pipeline",
            "🛠️  Pruebas BD",
        ]

    # Lista plana para el combo con etiquetas de grupo (formato árbol)
    lista_plana = []
    for grupo, items in opciones_navegacion.items():
        lista_plana.extend(items)

    st.markdown('<div class="sidebar-section">Navegación del Portal</div>', unsafe_allow_html=True)
    
    pagina_activa = st.radio(
        "Seleccione Sección",
        options=lista_plana,
        index=0,
        key="nav_unificada",
        label_visibility="collapsed"
    )

    # ── Botones de acción ──
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    if st.button("🚪 Cerrar sesión", key="btn_logout", width='stretch'):
        cerrar_sesion()
        st.rerun()

    # Botón de refresco de caché (solo admin/operador)
    if tiene_permiso("configurar"):
        if st.button("🔄 Refrescar datos", key="btn_clear_cache", width='stretch',
                     help="Limpia el caché local del portal y recarga todos los datos del backend"):
            st.cache_data.clear()
            st.toast("Caché limpiado. Los datos se recargarán del backend.", icon="🔄")
            st.rerun()

    st.markdown("""
        <div class="sidebar-footer">
            ACP Equipo de Proyecciones · 2026
        </div>
    """, unsafe_allow_html=True)

# ── Persistencia de estado de página ─────────────────────────────────────
# Evitamos recargas innecesarias
if "current_page" not in st.session_state:
    st.session_state.current_page = pagina_activa

st.session_state.current_page = pagina_activa

# ── Enrutamiento dinámico ─────────────────────────────────────────────────
_nombre = pagina_activa.split("  ", 1)[-1].strip() if "  " in pagina_activa else pagina_activa.strip()

_RUTAS = {
    "Inicio":              "paginas.inicio",
    "Cuarentena":          "paginas.cuarentena",
    "Homologación":        "paginas.homologacion",
    "Auditoría ETL":       "paginas.auditoria",
    "Sistema · Health":    "paginas.sistema",
    "Variedades":          "paginas.catalogos.variedades",
    "Geografía":           "paginas.catalogos.geografia",
    "Personal":            "paginas.catalogos.personal",
    "Reglas de Validación": "paginas.configuracion.reglas_validacion",
    "Parámetros Pipeline": "paginas.configuracion.parametros_pipeline",
    "Pruebas BD":          "paginas.configuracion.consola_admin",
}

modulo = _RUTAS.get(_nombre, "paginas.inicio")
pg = importlib.import_module(modulo)
pg.render()