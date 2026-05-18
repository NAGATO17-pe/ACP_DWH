import io

import pandas as pd
import streamlit as st

from utils.api_client import get_api
from utils.auth import tiene_permiso
from utils.componentes import banner_aviso, estado_vacio_html
from utils.formato import (
    GOLD_ACCENT,
    EMERALD_ACCENT,
    crear_panel_metricas_premium,
    header_pagina,
    renderizar_tabla_premium,
)

_RENOMBRES = {
    "tabla_origen":    "Tabla Origen",
    "id_registro":     "ID",
    "columna_origen":  "Columna Origen",
    "valor_raw":       "Valor Raw",
    "nombre_archivo":  "Archivo",
    "fecha_ingreso":   "Fecha ingreso",
    "estado":          "Estado",
    "motivo":          "Motivo",
}
_COLS_VISTA = ["ID", "Tabla Origen", "Columna Origen", "Valor Raw", "Motivo", "Fecha ingreso", "Estado"]


@st.cache_data(ttl=60, show_spinner=False)
def _cargar_cuarentena() -> pd.DataFrame:
    resultado = get_api("/cuarentena?pagina=1&tamano=10000")
    if resultado.ok and isinstance(resultado.data, dict):
        datos = resultado.data.get("datos", [])
        if datos:
            df = pd.DataFrame(datos)
            df.rename(columns=_RENOMBRES, inplace=True)
            return df
    return pd.DataFrame(columns=list(_RENOMBRES.values()))


def _exportar_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cuarentena")
    return buffer.getvalue()


def render() -> None:
    header_pagina(
        "🔴", "Cuarentena",
        "Registros rechazados por el pipeline · Solo lectura, auditoría.",
    )

    with st.spinner("Cargando registros de cuarentena…"):
        df = _cargar_cuarentena()

    total      = len(df)
    pendientes = int((df["Estado"] == "PENDIENTE").sum()) if not df.empty else 0
    resueltos  = int((df["Estado"] == "RESUELTO").sum())  if not df.empty else 0
    en_revision = total - pendientes - resueltos

    crear_panel_metricas_premium([
        {"label": "Total registros", "value": str(total),       "color": GOLD_ACCENT},
        {"label": "Pendientes",      "value": str(pendientes),  "color": "#EF4444" if pendientes else "#4d6b54"},
        {"label": "En revisión",     "value": str(en_revision), "color": GOLD_ACCENT if en_revision else "#4d6b54"},
        {"label": "Resueltos",       "value": str(resueltos),   "color": EMERALD_ACCENT},
    ])

    if df.empty:
        estado_vacio_html(
            "✅", "Sin registros en cuarentena",
            "El pipeline no ha rechazado ningún registro. Todo limpio.",
        )
        return

    columnas_vista = [c for c in _COLS_VISTA if c in df.columns]
    st.caption(f"{total} registro(s) · Última carga hace menos de 60 s")
    renderizar_tabla_premium(df[columnas_vista], key="cuarentena_tabla", page_size=15)

    st.download_button(
        label="📥 Exportar a Excel",
        data=_exportar_excel(df[columnas_vista]),
        file_name="cuarentena.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.divider()

    if tiene_permiso("escribir"):
        banner_aviso(
            "Esta vista es de <b>solo lectura</b> (Modo Auditoría). "
            "Para homologar registros pendientes, ve a "
            "<b>Homologación</b> en el menú lateral."
        )
    else:
        banner_aviso("Modo Auditoría. Tu rol no tiene permisos de edición.")
