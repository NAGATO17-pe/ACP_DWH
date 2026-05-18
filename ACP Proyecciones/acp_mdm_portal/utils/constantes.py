"""
utils/constantes.py — Fuente única de verdad para constantes del Portal MDM ACP.
=================================================================================
Importar desde aquí en lugar de definir localmente por módulo.
"""

from __future__ import annotations

# ── Fases del pipeline ETL ────────────────────────────────────────────────────

FASES_ETL: dict[str, dict] = {
    "config": {"nombre": "Configuración",  "color": "#64748B", "js_role": "raw",    "rango": (1, 2),  "icono": "⚙️"},
    "bronce": {"nombre": "Bronze Core",    "color": "#cd7f32", "js_role": "bronze", "rango": (3, 3),  "icono": "🥉"},
    "silver": {"nombre": "Silver Cortex",  "color": "#e2e8f0", "js_role": "silver", "rango": (4, 20), "icono": "🔷"},
    "gold":   {"nombre": "Golden Synapse", "color": "#ffd700", "js_role": "gold",   "rango": (21, 99),"icono": "🏆"},
}

# ── Paletas de estado ─────────────────────────────────────────────────────────

ESTADO_ICONOS: dict[str, str] = {
    "OK":      "✅",
    "ERROR":   "❌",
    "RUNNING": "🔄",
    "SKIPPED": "⏭️",
}

ESTADO_COLORES: dict[str, str] = {
    "OK":      "OK",
    "ERROR":   "❌ Falló",
    "RUNNING": "EN_REVISIÓN",
    "SKIPPED": "PENDIENTE",
}

LOCK_ESTADOS: dict[str, tuple[str, str, str]] = {
    "libre":    ("🟢", "#10B981", "Sin corridas activas. Listo para ejecutar."),
    "ocupado":  ("🟡", "#F59E0B", "Una corrida está en ejecución actualmente."),
    "vencido":  ("🔴", "#EF4444", "El lock lleva demasiado tiempo activo. Posible corrida colgada."),
    "error":    ("🔴", "#EF4444", "No se pudo leer el estado del lock."),
    "no_listo": ("⚪", "#6B7280", "Control-plane o BD no disponibles."),
}

# ── Roles y navegación ────────────────────────────────────────────────────────

ROL_BADGES: dict[str, str] = {
    "admin":        "🔑 Admin",
    "analista_mdm": "📊 Analista MDM",
    "operador_etl": "⚙️ Operador ETL",
    "viewer":       "👁️ Viewer",
}

# ── Paginación y límites ──────────────────────────────────────────────────────

PAGE_SIZE_DEFAULT              = 15
LIMITE_HISTORIAL_DEFAULT       = 200
OPCIONES_LIMITE_HISTORIAL      = [50, 100, 200, 500]
AUTOREFRESH_OPCIONES           = [0, 15, 30, 60, 120]   # segundos

# ── Renombres de columnas ─────────────────────────────────────────────────────

RENOMBRES_LOG_ETL: dict[str, str] = {
    "id_log":             "ID",
    "nombre_proceso":     "Proceso",
    "tabla_destino":      "Tabla",
    "nombre_archivo":     "Archivo",
    "fecha_inicio":       "Inicio",
    "fecha_fin":          "Fin",
    "estado":             "Estado",
    "filas_insertadas":   "Filas OK",
    "filas_rechazadas":   "Rechaz.",
    "duracion_segundos":  "Seg.",
    "mensaje_error":      "Error",
}

RENOMBRES_CUARENTENA: dict[str, str] = {
    "tabla_origen":   "Tabla Origen",
    "id_registro":    "ID",
    "columna_origen": "Columna Origen",
    "valor_raw":      "Valor Raw",
    "nombre_archivo": "Archivo",
    "fecha_ingreso":  "Fecha ingreso",
    "estado":         "Estado",
    "motivo":         "Motivo",
}

# ── Campos de geografía para homologación ─────────────────────────────────────
# Mapa: patrón en nombre de campo → clave de columna en el catálogo de geografía

CAMPOS_GEOGRAFIA: dict[str, str] = {
    "fundo":   "fundo",
    "sector":  "sector",
    "modulo":  "modulo",
    "módulo":  "modulo",
    "turno":   "turno",
    "valvula": "valvula",
    "válvula": "valvula",
    "cama":    "cama",
}
