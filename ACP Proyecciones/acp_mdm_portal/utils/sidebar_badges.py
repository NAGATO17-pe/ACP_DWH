"""
utils/sidebar_badges.py
========================
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
