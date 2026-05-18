# ============================================================
# DEPRECADO — No ejecutar
# ============================================================
# Este archivo fue reemplazado por:
#   acp_mdm_portal/utils/motor_proyecciones.py
#
# La lógica aquí presente implementaba una versión simplificada
# (kg_base × pct_maduracion × pct_productivas) que NO coincide
# con la fórmula operacional del Excel.
#
# El nuevo motor replica exactamente la fórmula:
#   Kg_N = Σ(Conteo × %Mad_N × Plantas × Peso_kg_N × %Prod_N) × decay_N
#
# Para ejecutar proyecciones, usar el portal:
#   streamlit run acp_mdm_portal/app.py
# ============================================================

raise RuntimeError(
    "SixWek.py está DEPRECADO. "
    "Usa acp_mdm_portal/utils/motor_proyecciones.py en su lugar."
)
