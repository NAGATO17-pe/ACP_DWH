"""
paginas/homologacion.py — Página de Homologación del portal MDM ACP
=====================================================================
Muestra sugerencias automáticas de homologación pendientes y el historial
de decisiones tomadas. Sin dependencia de streamlit_lottie.
"""

import html as html_lib

import pandas as pd
import streamlit as st

from utils.auth import tiene_permiso
from utils.api_client import get_api, patch_api, post_api
from utils.componentes import estado_vacio_html, seccion_tabla_con_guardar
from utils.constantes import PAGE_SIZE_DEFAULT
from utils.formato import crear_paginacion_ui, header_pagina


# ── Carga vía API ─────────────────────────────────────────────────────────────

def cargar_sugerencias_pendientes() -> pd.DataFrame:
    resultado = get_api("/cuarentena?pagina=1&tamano=10000&estado=PENDIENTE")
    if not resultado.ok:
        st.error("Error al cargar sugerencias pendientes. Si el problema persiste, inicia sesión nuevamente.")
        st.stop()
        
    if isinstance(resultado.data, dict):
        datos = resultado.data.get("datos", [])
        if datos:
            df = pd.DataFrame(datos)
            df = df.rename(columns={
                "tabla_origen": "Tabla", "columna_origen": "Campo",
                "valor_raw": "Texto crudo",
                "fecha_ingreso": "Fecha",
            }, errors="ignore")
            if "Valor canónico sugerido" not in df.columns:
                df["Valor canónico sugerido"] = ""
            if "Score" not in df.columns:
                df["Score"] = 0.0
            return df
    return pd.DataFrame()


def cargar_historial_homologacion() -> pd.DataFrame:
    resultado = get_api("/cuarentena?pagina=1&tamano=10000&estado=RESUELTO")
    if not resultado.ok:
        st.error("Error al cargar historial. Verifica tu conexión de red.")
        st.stop()
        
    if isinstance(resultado.data, dict):
        datos = resultado.data.get("datos", [])
        if datos:
            df = pd.DataFrame(datos)
            df = df.rename(columns={
                "tabla_origen": "Tabla", "columna_origen": "Campo",
                "valor_raw": "Texto crudo",
                "motivo": "Valor canónico", # fallback
                "fecha_ingreso": "Fecha aprobación",
            }, errors="ignore")
            if "Aprobado por" not in df.columns:
                df["Aprobado por"] = "Sistema"
            if "Score" not in df.columns:
                df["Score"] = 1.0
            return df
    return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def _cargar_geografia_completa() -> list[dict]:
    """Cache único del catálogo de geografía — TTL 5 min. Evita 6 llamadas duplicadas."""
    res = get_api("/catalogos/geografia?tamano=10000")
    if not res.ok or not isinstance(res.data, dict):
        return []
    return res.data.get("datos") or []


def obtener_opciones_maestras(campo: str) -> list[str]:
    from utils.constantes import CAMPOS_GEOGRAFIA
    campo_lower = campo.lower()
    opciones: set = set()

    if "variedad" in campo_lower:
        res = get_api("/catalogos/variedades?tamano=10000")
        if res.ok and isinstance(res.data, dict):
            opciones = {d.get("nombre_canonico") for d in res.data.get("datos", []) if d.get("nombre_canonico")}

    elif any(x in campo_lower for x in ["personal", "nombre", "responsable", "trabajador"]):
        res = get_api("/catalogos/personal?tamano=10000")
        if res.ok and isinstance(res.data, dict):
            opciones = {d.get("nombre_completo") for d in res.data.get("datos", []) if d.get("nombre_completo")}

    else:
        # Una sola llamada cacheada para todos los campos de geografía
        clave_geo = next(
            (llave for patron, llave in CAMPOS_GEOGRAFIA.items() if patron in campo_lower),
            None,
        )
        if clave_geo:
            datos_geo = _cargar_geografia_completa()
            opciones = {d.get(clave_geo) for d in datos_geo if d.get(clave_geo)}

    return sorted(opciones - {None})


# ── Render ────────────────────────────────────────────────────────────────────

def render() -> None:
    header_pagina(
        "🔗", "Homologación",
        "Sugerencias automáticas pendientes · aprueba, corrige o rechaza",
    )

    # ── Tab 1: Pendientes ─────────────────────────────────────────────────────
    df = cargar_sugerencias_pendientes()

    if df.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            estado_vacio_html(
                icono="🎉",
                titulo="No hay sugerencias pendientes.",
                subtitulo="El motor de homologación no encontró anomalías recientes.",
            )
    else:
        # ── KPIs rápidos ──────────────────────────────────────────────────
        total     = len(df)
        alta_conf = len(df[df["Score"] >= 0.85]) if "Score" in df.columns else 0
        baja_conf = total - alta_conf

        c1, c2, c3 = st.columns(3)
        c1.metric("📋 Total pendientes",       total)
        c2.metric("🟢 Alta confianza (≥0.85)", alta_conf)
        c3.metric("🟡 Baja confianza (<0.85)", baja_conf)

        # ── HERRAMIENTA: Re-Inyección MDM ────────────────────────────────────
        if tiene_permiso("escribir"):
            conteo_resp = get_api("/reinyeccion/candidatos")
            candidatos = 0
            if conteo_resp.ok and isinstance(conteo_resp.data, dict):
                candidatos = conteo_resp.data.get("candidatos", 0)

            with st.expander(
                f"🔄 Herramienta de Re-Inyección MDM  ―  "
                f"{candidatos} registro(s) RESUELTO(S) listos para reprocesar",
                expanded=candidatos > 0,
            ):
                st.markdown(
                    """
                    **¿Qué hace esta herramienta?**  
                    Toma los registros que ya **aprobaste y homologaste** en la tabla de abajo
                    y los devuelve a estado `CARGADO` en la capa Bronce.
                    Así la próxima vez que ejecutes el Pipeline, el motor ETL los volverá a procesar
                    automáticamente con las nuevas reglas MDM, insertándolos al Data Warehouse.
                    **No necesitas volver a subir ningún archivo Excel.**
                    """
                )
                if candidatos == 0:
                    st.info("ℹ️ No hay registros RESUELTOS pendientes de reinyección en este momento.", icon="🟢")
                else:
                    st.warning(
                        f"⚠️ ¡Atención! Esta acción modificará `{candidatos}` filas en la capa Bronce. "
                        f"Asegúrate de haber aprobado las correcciones antes de continuar.",
                        icon="🟡",
                    )
                    if st.button(
                        f"🔄 Re-encolar {candidatos} registro(s) al Pipeline",
                        key="btn_reinyectar",
                        type="primary",
                        use_container_width=True,
                    ):
                        with st.spinner("⏳ Reinyectando en Bronce..."):
                            res = post_api("/reinyeccion/ejecutar", payload={})
                        if res.ok and isinstance(res.data, dict):
                            n = res.data.get("reinyectados", 0)
                            msg = html_lib.escape(str(res.data.get("mensaje", "")))
                            detalle = res.data.get("detalle", [])
                            st.toast(f"✅ {n} registro(s) reactivados en Bronce.", icon="🎉")
                            st.success(msg)
                            for linea in detalle:
                                st.caption(html_lib.escape(str(linea)))
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            err = html_lib.escape(str(res.error or "Error desconocido"))
                            st.error(f"❌ Fallo en la reinyección: {err}")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Filtros ───────────────────────────────────────────────────────
        f1, f2 = st.columns(2)
        with f1:
            tabla_sel = st.selectbox(
                "Filtrar por tabla",
                ["Todas"] + sorted(df["Tabla"].unique().tolist()),
                key="pend_tabla",
            )
        with f2:
            campo_sel = st.selectbox(
                "Filtrar por campo",
                ["Todos"] + sorted(df["Campo"].unique().tolist()),
                key="pend_campo",
            )

        df_filtrado = df.copy()
        if tabla_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado["Tabla"] == tabla_sel]
        if campo_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado["Campo"] == campo_sel]

        st.markdown(f"**{len(df_filtrado)}** sugerencias coinciden con los filtros.")
        st.markdown("---")

        # ── Preparación de Tabla con Reglas Inteligentes ──────────────────
        df_edit = df_filtrado.copy()
        df_edit.insert(0, "Seleccionar", False)
        df_edit["Corrección"] = df_edit["Valor canónico sugerido"]

        # Auto-resolución para confianza altísima
        if "Score" in df_edit.columns:
            high_conf = df_edit["Score"] >= 0.95
            if high_conf.any():
                df_edit.loc[high_conf, "Seleccionar"] = True

        # Configuración Dinámica de Columna de Corrección (Master Data)
        opciones_combo = []
        if campo_sel != "Todos":
            opciones_combo = obtener_opciones_maestras(campo_sel)

        if campo_sel == "Todos":
            st.info("💡 **Paso 1:** Filtra por un 'Campo' específico (arriba a la derecha) para poder corregir los registros con los valores Oficiales del Data Warehouse.", icon="🔍")
            col_correccion = st.column_config.TextColumn(
                "Corrección ✍️", 
                help="Filtra por campo arriba para activar las opciones maestras."
            )
        elif opciones_combo:
            col_correccion = st.column_config.SelectboxColumn(
                f"Corrección Maestro ({len(opciones_combo)} disp.) ✍️", 
                help="Selecciona un valor válido del catálogo oficial.",
                options=opciones_combo, 
                width="large",
                required=True
            )
            df_edit.loc[~df_edit["Corrección"].isin(opciones_combo), "Corrección"] = None
        else:
            col_correccion = st.column_config.TextColumn(
                "Corrección Libre ✍️", 
                help="No existen catálogos oficiales todavía para este campo.", 
                width="large"
            )

        count = len(df_edit)

        # Leemos el state para saber la página exacta antes de renderizar la tabla
        page = st.session_state.get('pg_pendientes_edit', 1)
        start_idx = (page - 1) * PAGE_SIZE_DEFAULT
        end_idx = start_idx + PAGE_SIZE_DEFAULT
        df_page = df_edit.iloc[start_idx:end_idx].copy()

        st.markdown("<br>", unsafe_allow_html=True)
        # ── Editor o solo lectura según permiso ─────────────────────────────────────────
        if tiene_permiso("escribir"):
            st.caption("Revisa los valores, ajusta el combo si es necesario, asegúrate que el check esté marcado y haz click en los botones inferiores.")

            # Columnas ocultas por UX (Limpieza total de ruido)
            escondidas = ["id_registro", "Valor canónico sugerido", "nombre_archivo", "estado", "motivo", "id_registro_origen", "Fecha"]
            if tabla_sel != "Todas": escondidas.append("Tabla")
            if campo_sel != "Todos": escondidas.append("Campo")

            disabled_cols = ["Tabla", "Campo", "Texto crudo", "Score", "Fecha", "Valor canónico sugerido"]
            if campo_sel == "Todos":
                disabled_cols.append("Corrección") 

            edited = st.data_editor(
                df_page,
                hide_index=True,
                width='stretch',
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn(
                        "✔", help="Seleccionar para guardar/rechazar", width="small"
                    ),
                    "Corrección": col_correccion,
                    "Score": st.column_config.ProgressColumn(
                        "Score 🎯", min_value=0.0, max_value=1.0, format="%.2f"
                    ),
                    "Texto crudo":            st.column_config.TextColumn("Dato Basura ⚠️", width="large"),
                    "Tabla":                  st.column_config.TextColumn("Tabla",        width="medium"),
                    "Campo":                  st.column_config.TextColumn("Campo",        width="medium"),
                    "Fecha":                  st.column_config.TextColumn("Fecha",        width="small"),
                },
                column_order=[c for c in df_page.columns if c not in escondidas],
                disabled=disabled_cols,
                key="editor_pendientes",
            )

            # ── PANEL DE CONTROL INFERIOR ─────────────────────────────────────────
            st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid #4ade8055;'>", unsafe_allow_html=True)
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("💾 Guardar Seleccionados", key="btn_aplicar", type="primary", use_container_width=True):
                    seleccionados = edited[edited["Seleccionar"] == True]
                    if len(seleccionados) == 0:
                        st.toast("Bloqueado: Selecciona al menos un registro en la tabla.", icon="⚠️")
                    else:
                        exitos = 0
                        errores = 0
                        for _, row in seleccionados.iterrows():
                            if pd.isna(row["Corrección"]) or str(row["Corrección"]).strip() == "":
                                st.toast(f"Fila omitida: La corrección está vacía para el crudo '{row['Texto crudo']}'", icon="⚠️")
                                errores += 1
                                continue

                            # Normalizamos el nombre de tabla: 'Bronce.Peladas' -> 'peladas'
                            tabla_raw = str(row.get("Tabla", ""))
                            tabla_api = tabla_raw.split(".")[-1].lower()

                            res = patch_api(
                                f"/cuarentena/{tabla_api}/{row['id_registro']}/resolver",
                                {"valor_canonico": row["Corrección"], "comentario": "Resuelto UX"}
                            )
                            if res.ok: exitos += 1
                            else:
                                errores += 1
                                st.toast(f"❌ Error al guardar '{row['Texto crudo']}': {res.error}", icon="❌")

                        if exitos > 0:
                            st.toast(f"✅ ¡{exitos} registros insertados en DWH!", icon="🎉")
                            st.cache_data.clear()
                            st.rerun()

            with b2:
                if st.button("🗑️ Rechazar Seleccionados", key="btn_rechazar", use_container_width=True):
                    seleccionados = edited[edited["Seleccionar"] == True]
                    if len(seleccionados) == 0:
                        st.toast("Bloqueado: Selecciona al menos un registro en la tabla.", icon="⚠️")
                    else:
                        exitos = 0
                        for _, row in seleccionados.iterrows():
                            tabla_raw = str(row.get("Tabla", ""))
                            tabla_api = tabla_raw.split(".")[-1].lower()
                            if patch_api(
                                f"/cuarentena/{tabla_api}/{row['id_registro']}/rechazar",
                                {"motivo": "Rechazado desde UX Homologación"}
                            ).ok: exitos += 1
                        if exitos > 0:
                            st.toast(f"🗑️ {exitos} registros purgados del sistema.", icon="✅")
                            st.cache_data.clear()
                            st.rerun()

            crear_paginacion_ui(count, PAGE_SIZE_DEFAULT, "pendientes_edit")

        else:
            st.info("🔒 Vista de solo lectura. Tu rol no puede aprobar ni rechazar sugerencias.", icon="⚠️")
            st.dataframe(df_page, hide_index=True, width='stretch')
            crear_paginacion_ui(count, PAGE_SIZE_DEFAULT, "pendientes_edit")
