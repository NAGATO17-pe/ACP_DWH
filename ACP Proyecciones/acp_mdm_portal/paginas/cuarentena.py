import io
import pandas as pd
import streamlit as st
from utils.auth import tiene_permiso
from utils.componentes import badge_html, estado_vacio_html, mostrar_kpis
from utils.formato import header_pagina, renderizar_tabla_premium
from utils.api_client import get_api, mostrar_error_api

def cargar_cuarentena() -> pd.DataFrame:
    from utils.constantes import RENOMBRES_CUARENTENA
    resultado = get_api("/cuarentena?pagina=1&tamano=10000")
    cols_vacias = list(RENOMBRES_CUARENTENA.values())
    if not resultado.ok:
        return pd.DataFrame(columns=cols_vacias)
    data = resultado.data
    if not isinstance(data, dict):
        return pd.DataFrame(columns=cols_vacias)
    datos = data.get("datos") or []
    if not isinstance(datos, list) or not datos:
        return pd.DataFrame(columns=cols_vacias)
    df = pd.DataFrame(datos)
    df.rename(columns=RENOMBRES_CUARENTENA, inplace=True)
    return df

def _exportar_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cuarentena")
    return buffer.getvalue()

def render() -> None:
    header_pagina("🔴", "Cuarentena", "Revisión de registros rechazados · Decide qué hacer con cada uno")
    df_original = cargar_cuarentena()

    total = len(df_original)
    pendientes = int((df_original["Estado"] == "PENDIENTE").sum()) if not df_original.empty else 0
    resueltos = int((df_original["Estado"] == "RESUELTO").sum()) if not df_original.empty else 0

    mostrar_kpis([
        {"label": "📋 Total registros", "value": total},
        {"label": "⏳ Pendientes", "value": pendientes},
        {"label": "✅ Resueltos", "value": resueltos},
    ])

    st.markdown("<hr style='margin:16px 0;'>", unsafe_allow_html=True)

    if df_original.empty:
        estado_vacio_html("✅", "Sin registros coincidentes", "No hay registros en cuarentena.")
        return

    st.markdown("### 📋 Registros en cuarentena")
    columnas_vista = [c for c in ["ID", "Tabla Origen", "Columna Origen", "Valor Raw", "Motivo", "Fecha ingreso", "Estado"] if c in df_original.columns]
    renderizar_tabla_premium(df_original[columnas_vista], key="cuarentena_tabla", page_size=15)

    st.download_button(
        label="📥 Exportar a Excel",
        data=_exportar_excel(df_original[columnas_vista]),
        file_name="cuarentena.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("<hr style='margin:24px 0;'>", unsafe_allow_html=True)

    if tiene_permiso("escribir"):
        st.info(
            "💡 **Atención Analista/Steward:** Esta pantalla es de **solo-lectura** "
            "(Modo Auditoría). Para procesar masivamente y homologar "
            "registros pendientes utilizando los **Catálogos Oficiales**, por favor "
            "dirígete a la sección de **[ Homologación ]** en el menú lateral.", 
            icon="ℹ️"
        )
    else:
        st.info("🔒 Modo Auditoría. Tu rol no tiene permisos de edición.", icon="🛡️")
