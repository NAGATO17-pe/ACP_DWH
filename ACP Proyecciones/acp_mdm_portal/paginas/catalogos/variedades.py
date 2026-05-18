"""
paginas/catalogos/variedades.py — Catálogo de Variedades · Portal MDM ACP
==========================================================================
Permite alternar entre dos fuentes de datos:
  · MDM   → MDM.Catalogo_Variedades   (maestro oficial: solo lectura)
  · Dim   → Silver.Dim_Variedad        (dimensión DWH: CRUD admin)

Operaciones disponibles en Dim (solo admin):
  · Crear nueva variedad
  · Desactivar variedad  (soft-delete con trazabilidad)
  · Reactivar variedad
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.api_client import get_api, patch_api, post_api
from utils.auth import tiene_permiso
from utils.componentes import estado_vacio_html, banner_aviso
from utils.formato import header_pagina, renderizar_tabla_premium, crear_panel_metricas_premium


# ── Constantes de fuentes ─────────────────────────────────────────────────────

_FUENTES = {
    "🗂️  Catálogo MDM": {
        "endpoint":    "/catalogos/variedades?pagina=1&tamano=10000",
        "badge_txt":   "MDM.Catalogo_Variedades",
        "badge_color": "#2db87a",
        "desc":        "Catálogo maestro oficial de variedades. Solo lectura.",
        "renombres": {
            "nombre_canonico": "Nombre Canónico",
            "breeder":         "Breeder / Casa",
            "es_activa":       "Activa",
        },
        "col_nombre":  "Nombre Canónico",
        "col_breeder": "Breeder / Casa",
        "escribible":  False,
    },
    "📐  Dim. DWH Silver": {
        "endpoint":    "/catalogos/variedades/dim?pagina=1&tamano=10000",
        "badge_txt":   "Silver.Dim_Variedad",
        "badge_color": "#e8a020",
        "desc":        "Dimensión DWH homologada. Admins pueden crear y desactivar.",
        "renombres": {
            "id_variedad":        "ID",
            "nombre_variedad":    "Nombre Variedad",
            "breeder":            "Breeder / Casa",
            "es_activa":          "Activa",
            "fecha_creacion":     "Creado",
            "fecha_modificacion": "Modificado",
        },
        "col_nombre":  "Nombre Variedad",
        "col_breeder": "Breeder / Casa",
        "escribible":  True,
    },
}


# ── Mediación de errores del backend ─────────────────────────────────────────

def _mensaje_error_usuario(status_code: int | None, error_raw: str | None, accion: str) -> str:
    """
    Convierte la respuesta cruda del backend en un mensaje accionable para el
    operador. Nunca expone stacktraces, queries SQL ni nombres internos.

    accion : 'desactivar' | 'reactivar' | 'crear'
    """
    raw = (error_raw or "").lower()

    if status_code == 401 or status_code == 403:
        return "No tienes permisos para esta acción. Solicita acceso de Admin."
    if status_code == 404:
        return "El registro no existe o ya fue eliminado. Actualiza la página."
    if status_code == 409:
        if accion == "crear":
            return "Ya existe una variedad con ese nombre en la dimensión."
        return "El registro ya está en el estado solicitado."
    if status_code is None or status_code >= 500:
        return "El servidor no respondió. Reintenta en unos segundos."
    if "timeout" in raw or "timed out" in raw:
        return "La operación tardó demasiado. Reintenta."
    if "connection" in raw or "refused" in raw:
        return "Sin conexión con el backend. Verifica que el servidor esté activo."

    # Mensaje genérico — nunca exponer raw
    verbos = {"desactivar": "desactivar", "reactivar": "reactivar", "crear": "crear"}
    return f"No se pudo {verbos.get(accion, 'completar')} la variedad. Intenta nuevamente."


# ── Carga de datos ────────────────────────────────────────────────────────────

def _cargar(endpoint: str) -> pd.DataFrame:
    """Consulta directa al backend — sin caché."""
    resultado = get_api(endpoint)
    if resultado.ok and isinstance(resultado.data, dict):
        datos = resultado.data.get("datos", [])
        if datos:
            return pd.DataFrame(datos)
    return pd.DataFrame()


# ── KPIs adaptativos ──────────────────────────────────────────────────────────

def _render_kpis_mdm(df: pd.DataFrame) -> None:
    activas   = int(df["Activa"].sum()) if "Activa" in df.columns else len(df)
    inactivas = len(df) - activas
    breeders  = df["Breeder / Casa"].nunique() if "Breeder / Casa" in df.columns else 0
    crear_panel_metricas_premium([
        {"label": "Total Variedades", "value": str(len(df)),   "color": "#e8a020"},
        {"label": "Activas",          "value": str(activas),   "color": "#2db87a"},
        {"label": "Inactivas",        "value": str(inactivas), "color": "#EF4444" if inactivas else "#8fa897"},
        {"label": "Casas Breeder",    "value": str(breeders),  "color": "#8fa897"},
    ])


def _render_kpis_dim(df: pd.DataFrame) -> None:
    activas   = int(df["Activa"].sum()) if "Activa" in df.columns else len(df)
    inactivas = len(df) - activas
    breeders  = df["Breeder / Casa"].nunique() if "Breeder / Casa" in df.columns else 0
    crear_panel_metricas_premium([
        {"label": "Total Dim_Variedad", "value": str(len(df)),   "color": "#e8a020"},
        {"label": "Activas",            "value": str(activas),   "color": "#2db87a"},
        {"label": "Desactivadas",       "value": str(inactivas), "color": "#EF4444" if inactivas else "#8fa897"},
        {"label": "Casas Breeder",      "value": str(breeders),  "color": "#8fa897"},
    ])


# ── Filtros ───────────────────────────────────────────────────────────────────

def _render_filtro(df: pd.DataFrame, col_nombre: str, col_breeder: str, clave: str, mostrar_estado: bool = False) -> pd.DataFrame:
    with st.container(border=True):
        cols = st.columns([2, 1, 1] if mostrar_estado else [2, 1])

        with cols[0]:
            busqueda = st.text_input(
                "🔍 Buscar variedad",
                placeholder="Ej: Biloxi, O'Neal, Summer…",
                key=f"var_busqueda_{clave}",
                label_visibility="collapsed",
            )
        with cols[1]:
            breeders = ["Todos"] + sorted(df[col_breeder].dropna().unique().tolist()) \
                if col_breeder in df.columns else ["Todos"]
            breeder_sel = st.selectbox(
                "Casa breeder", breeders,
                key=f"var_breeder_{clave}",
                label_visibility="collapsed",
            )
        if mostrar_estado and len(cols) > 2:
            with cols[2]:
                estado_sel = st.selectbox(
                    "Estado", ["Todos", "Activas", "Desactivadas"],
                    key=f"var_estado_{clave}",
                    label_visibility="collapsed",
                )
        else:
            estado_sel = "Todos"

    dff = df.copy()
    if busqueda and col_nombre in dff.columns:
        dff = dff[dff[col_nombre].str.contains(busqueda, case=False, na=False)]
    if breeder_sel != "Todos" and col_breeder in dff.columns:
        dff = dff[dff[col_breeder] == breeder_sel]
    if estado_sel == "Activas" and "Activa" in dff.columns:
        dff = dff[dff["Activa"] == True]
    elif estado_sel == "Desactivadas" and "Activa" in dff.columns:
        dff = dff[dff["Activa"] == False]

    return dff


# ── Formulario de creación (solo admin, solo Dim) ─────────────────────────────

def _render_formulario_crear(df: pd.DataFrame) -> bool:
    """Devuelve True si se creó una variedad y hay que recargar."""
    with st.expander("➕ Agregar nueva variedad a Dim_Variedad", expanded=False):
        with st.form("form_crear_dim_variedad", clear_on_submit=True):
            col_n, col_b = st.columns([2, 1])
            with col_n:
                nombre = st.text_input(
                    "Nombre Variedad *",
                    placeholder="Ej: Summer Sunshine",
                    help="Debe ser único en Silver.Dim_Variedad.",
                )
            with col_b:
                breeder = st.text_input(
                    "Breeder / Casa",
                    placeholder="Ej: Mississippi State",
                    help="Opcional.",
                )
            submitted = st.form_submit_button("💾 Crear variedad", type="primary")

        if submitted:
            if not nombre.strip():
                banner_aviso("El nombre de la variedad es obligatorio.")
                return False

            # Verificar que no exista ya en el DataFrame en memoria
            nombres_existentes = (
                df["Nombre Variedad"].str.lower().tolist()
                if "Nombre Variedad" in df.columns else []
            )
            if nombre.strip().lower() in nombres_existentes:
                banner_aviso(f"Ya existe una variedad con el nombre **{nombre.strip()}** en la dimensión.")
                return False

            resultado = post_api(
                "/catalogos/variedades/dim",
                {"nombre_variedad": nombre.strip(), "breeder": breeder.strip() or None},
            )
            if resultado.ok:
                st.success(f"✅ Variedad **{nombre.strip()}** creada correctamente.")
                return True
            banner_aviso(_mensaje_error_usuario(resultado.status_code, resultado.error, "crear"))
    return False


# ── Botones de desactivar / reactivar por fila ────────────────────────────────

_PENDIENTE_KEY = "var_accion_pendiente"  # {"accion": "...", "id": int, "nombre": str}


def _render_banner_confirmacion(accion: str, nombre: str) -> tuple[bool, bool]:
    """
    Banner inline de confirmación (sin modal — restricción impeccable).
    Retorna (confirmado, cancelado).
    """
    verbos = {
        "desactivar": ("🔴", "Desactivar",  "se ocultará de las proyecciones futuras", "#EF4444"),
        "reactivar":  ("🟢", "Reactivar",   "volverá a aparecer en las proyecciones",  "#2db87a"),
    }
    icono, verbo, consecuencia, color = verbos[accion]

    st.markdown(f"""
    <div style="
        background:rgba(232,160,32,0.08);
        border:1px solid rgba(232,160,32,0.35);
        border-left:3px solid #e8a020;
        border-radius:12px;
        padding:14px 18px;
        margin:12px 0;
    ">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <span style="font-size:1.2rem;">{icono}</span>
            <span style="font-weight:700;color:#e8f0ec;font-size:0.95rem;">
                ¿Confirmar {verbo.lower()} variedad?
            </span>
        </div>
        <div style="font-size:0.82rem;color:#8fa897;padding-left:30px;">
            <b style="color:#e8f0ec;font-family:'JetBrains Mono',monospace;">{nombre}</b>
            — {consecuencia}.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_c, col_x, _ = st.columns([1, 1, 4])
    confirmado = col_c.button(
        f"✓ Sí, {verbo.lower()}",
        key=f"confirm_{accion}",
        type="primary",
        use_container_width=True,
    )
    cancelado = col_x.button(
        "✗ Cancelar",
        key=f"cancel_{accion}",
        use_container_width=True,
    )
    return confirmado, cancelado


def _render_acciones_dim(df: pd.DataFrame) -> bool:
    """Renderiza controles de acción para Dim_Variedad. Devuelve True si hubo cambio."""
    if "ID" not in df.columns:
        return False

    st.markdown("#### ⚙️ Gestionar estado de variedad")

    opciones = [f"[{int(row['ID'])}] {row['Nombre Variedad']}" for _, row in df.iterrows()]
    if not opciones:
        banner_aviso("No hay variedades que gestionar con los filtros actuales.")
        return False

    col_sel, col_btn_d, col_btn_r = st.columns([3, 1, 1])
    with col_sel:
        seleccion = st.selectbox(
            "Seleccionar variedad",
            opciones,
            key="var_acciones_sel",
            label_visibility="collapsed",
        )

    id_sel     = int(seleccion.split("]")[0].replace("[", "").strip()) if seleccion else None
    nombre_sel = seleccion.split("] ", 1)[1] if seleccion and "] " in seleccion else ""

    # Botones de inicio de acción — solo arman la confirmación en session_state
    with col_btn_d:
        if st.button("🔴 Desactivar", key="btn_var_desactivar", use_container_width=True):
            if id_sel:
                st.session_state[_PENDIENTE_KEY] = {
                    "accion": "desactivar", "id": id_sel, "nombre": nombre_sel,
                }
                st.rerun()

    with col_btn_r:
        if st.button("🟢 Reactivar", key="btn_var_reactivar", use_container_width=True):
            if id_sel:
                st.session_state[_PENDIENTE_KEY] = {
                    "accion": "reactivar", "id": id_sel, "nombre": nombre_sel,
                }
                st.rerun()

    # ── Banner de confirmación inline (si hay acción pendiente) ───────────────
    pendiente = st.session_state.get(_PENDIENTE_KEY)
    if not pendiente:
        return False

    confirmado, cancelado = _render_banner_confirmacion(
        pendiente["accion"], pendiente["nombre"],
    )

    if cancelado:
        del st.session_state[_PENDIENTE_KEY]
        st.rerun()

    if confirmado:
        accion = pendiente["accion"]
        id_op  = pendiente["id"]
        res    = patch_api(f"/catalogos/variedades/dim/{id_op}/{accion}", {})
        del st.session_state[_PENDIENTE_KEY]

        if res.ok:
            verbo_pasado = "desactivada" if accion == "desactivar" else "reactivada"
            st.success(f"✅ Variedad **{pendiente['nombre']}** {verbo_pasado} correctamente.")
            return True
        banner_aviso(_mensaje_error_usuario(res.status_code, res.error, accion))

    return False


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    header_pagina(
        "🍇", "Variedades",
        "Explora el catálogo MDM y la dimensión DWH · Gestión admin disponible en Dim."
    )

    es_admin = tiene_permiso("admin")

    # ── Selector de fuente ──────────────────────────────────────────────────
    fuente_sel = st.radio(
        "Fuente de datos",
        list(_FUENTES.keys()),
        horizontal=True,
        key="var_fuente_sel",
        label_visibility="collapsed",
    )
    cfg = _FUENTES[fuente_sel]

    # Badge de fuente activa
    st.markdown(
        f"""<div style="
            display:inline-flex; align-items:center; gap:8px;
            background:{cfg['badge_color']}15; border:1px solid {cfg['badge_color']}40;
            border-radius:8px;
            padding:8px 14px; margin-bottom:18px;
        ">
            <span style="font-size:0.75rem;font-weight:700;color:{cfg['badge_color']};
                         font-family:'JetBrains Mono',monospace;">{cfg['badge_txt']}</span>
            <span style="font-size:0.75rem;color:#8fa897;">— {cfg['desc']}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Carga de datos ──────────────────────────────────────────────────────
    with st.spinner("Cargando variedades desde el backend…"):
        df_raw = _cargar(cfg["endpoint"])

    if df_raw.empty:
        estado_vacio_html(
            "🍇",
            "Sin datos de variedades",
            "No se pudo cargar el catálogo. Verifica que el backend esté activo.",
        )
        return

    df = df_raw.rename(columns=cfg["renombres"])
    clave = "mdm" if "MDM" in fuente_sel else "dim"
    es_dim = cfg["escribible"]

    # ── KPIs ────────────────────────────────────────────────────────────────
    if es_dim:
        _render_kpis_dim(df)
    else:
        _render_kpis_mdm(df)

    # ── Formulario de creación (solo admin + Dim) ────────────────────────────
    if es_dim and es_admin:
        recarga = _render_formulario_crear(df)
        if recarga:
            st.rerun()

    # ── Filtros ─────────────────────────────────────────────────────────────
    dff = _render_filtro(
        df,
        cfg["col_nombre"],
        cfg["col_breeder"],
        clave,
        mostrar_estado=es_dim,
    )

    # ── Tabla ────────────────────────────────────────────────────────────────
    st.caption(
        f"{len(dff)} registro(s) de {len(df)} totales · Fuente: `{cfg['badge_txt']}`"
    )
    renderizar_tabla_premium(dff, key=f"var_tabla_{clave}", page_size=20)

    # ── Panel de gestión de estado (solo admin + Dim) ────────────────────────
    if es_dim and es_admin:
        st.divider()
        hubo_cambio = _render_acciones_dim(dff)
        if hubo_cambio:
            st.rerun()
    elif es_dim and not es_admin:
        banner_aviso("Las operaciones de creación y desactivación requieren rol **Admin**.")
