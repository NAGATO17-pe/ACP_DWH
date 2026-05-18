"""
utils/formato.py — Sistema de diseño visual del Portal MDM ACP (Enterprise)
=============================================================================
CSS Premium + Componentes de renderizado HTML.

Cambios v4 Midnight Premium Edition:
  - Estética Dark Mode (OLED) profunda basada en Slate 900/950.
  - Glassmorphism Oscuro: backdrop-filter blur sobre fondos Slate translúcidos.
  - Acentos Gold (Amber) y Emerald para estados operativos.
  - Sidebar Midnight con navegación resaltada en Gold.
  - Tipografía Outfit + Inter integrada vía Google Fonts.
"""

import math

import streamlit as st

# ── Midnight Premium Palette ──
SLATE_950      = "#020617"
SLATE_900      = "#0F172A"
SLATE_800      = "#1E293B"
SLATE_400      = "#94A3B8"
SLATE_50       = "#F8FAFC"
GOLD_ACCENT    = "#F59E0B"
EMERALD_ACCENT = "#10B981"
SURFACE_GLASS  = "rgba(30, 41, 59, 0.65)"

CSS_PORTAL = f"""
<style>
/* ── Google Fonts (Zenith Premium) ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

/* ── Design Tokens ── */
:root {{
    --slate-950: {SLATE_950};
    --slate-900: {SLATE_900};
    --slate-800: {SLATE_800};
    --slate-400: {SLATE_400};
    --slate-50:  {SLATE_50};
    --gold-accent: {GOLD_ACCENT};
    --emerald-accent: {EMERALD_ACCENT};

    --glass-bg: {SURFACE_GLASS};
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);

    --radius-sm: 10px;
    --radius-md: 14px;
    --radius-lg: 18px;
    --radius-xl: 24px;
}}

/* ── Typography ── */
html, body, [class*="css"] {{
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}

h1, h2, h3, h4 {{
    font-family: 'Outfit', 'Inter', system-ui, sans-serif;
}}

/* ── Micro-animations (Zenith) ── */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes slideUp {{
    from {{ opacity: 0; transform: translateY(14px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes shimmer {{
    0%   {{ background-position: -200% 0; }}
    100% {{ background-position: 200% 0; }}
}}
@keyframes softPulse {{
    0%, 100% {{ opacity: 1; }}
    50%      {{ opacity: 0.7; }}
}}
@keyframes auroraFloat {{
    0%   {{ transform: translate(0, 0) scale(1); }}
    33%  {{ transform: translate(30px, -20px) scale(1.05); }}
    66%  {{ transform: translate(-20px, 15px) scale(0.95); }}
    100% {{ transform: translate(0, 0) scale(1); }}
}}
@keyframes cardShimmer {{
    0%   {{ left: -100%; }}
    100% {{ left: 200%; }}
}}

/* Smooth transitions — solo elementos del design system, no widgets Streamlit */
.kpi-card, .glass-card, .nav-item, .step-item, .badge,
.stButton > button, .sidebar-nav-item {{
    transition: background-color 0.25s ease, border-color 0.25s ease,
                box-shadow 0.25s ease, transform 0.2s ease, opacity 0.25s ease;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   APP BACKGROUND — Aurora UI (Zenith Premium)
   ══════════════════════════════════════════════════════════════════════════════ */
.stApp {{
    background: {SLATE_950} !important;
    background-attachment: fixed !important;
}}
.stApp::before {{
    content: '';
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background:
        radial-gradient(600px circle at 15% 15%, rgba(245, 158, 11, 0.06) 0%, transparent 60%),
        radial-gradient(500px circle at 85% 80%, rgba(16, 185, 129, 0.05) 0%, transparent 60%),
        radial-gradient(400px circle at 50% 50%, rgba(59, 130, 246, 0.03) 0%, transparent 50%);
    animation: auroraFloat 25s ease-in-out infinite;
}}
/* Digital grain texture */
.stApp::after {{
    content: '';
    position: fixed;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    opacity: 0.015;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}}

/* ══════════════════════════════════════════════════════════════════════════════
   SIDEBAR — Midnight Premium
   ══════════════════════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {{
    background-color: transparent !important;
    border-right: none !important;
}}
section[data-testid="stSidebar"] > div:first-child {{
    background: {SLATE_950} !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
    box-shadow: 10px 0 30px rgba(0,0,0,0.5) !important;
}}

/* Sidebar text */
section[data-testid="stSidebar"] *:not(span[style]) {{
    color: {SLATE_400} !important;
}}

.sidebar-logo {{
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 18px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 8px;
}}
.sidebar-logo h2 {{
    font-family: 'Outfit', sans-serif;
    color: {GOLD_ACCENT} !important;
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: 0.5px;
}}

.sidebar-section {{
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: rgba(255,255,255,0.3) !important;
    padding: 18px 14px 6px 14px;
    font-weight: 700;
}}

/* Radio Nav */
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{
    display: none !important;
}}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {{
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 2px;
    background: transparent;
    cursor: pointer;
    border-left: 2px solid transparent;
    transition: all 0.2s ease;
}}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {{
    background: rgba(255,255,255,0.03) !important;
    color: {SLATE_50} !important;
}}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[aria-checked="true"] {{
    background: rgba(245, 158, 11, 0.08) !important;
    border-left-color: {GOLD_ACCENT} !important;
}}
section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label[aria-checked="true"] p {{
    color: {GOLD_ACCENT} !important;
    font-weight: 600 !important;
}}
section[data-testid="stSidebar"] .stRadio p {{
    font-size: 0.85rem;
    font-weight: 500;
}}

.sidebar-footer {{
    text-align: center;
    padding: 20px 12px;
    border-top: 1px solid rgba(255,255,255,0.05);
    font-size: 0.65rem;
    color: rgba(255,255,255,0.2) !important;
}}

/* ── Logout button (Midnight) ── */
section[data-testid="stSidebar"] .stButton > button {{
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: {SLATE_400} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}}
section[data-testid="stSidebar"] .stButton > button:hover {{
    background: rgba(239, 68, 68, 0.1) !important;
    border-color: rgba(239, 68, 68, 0.3) !important;
    color: #EF4444 !important;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   PAGE HEADER — Glass effect with Gold accent
   ══════════════════════════════════════════════════════════════════════════════ */
.page-header {{
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.05);
    border-left: 4px solid {GOLD_ACCENT};
    padding: 16px 24px;
    border-radius: 14px;
    margin-bottom: 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    animation: slideUp 0.4s ease;
}}
.page-header h1 {{
    font-family: 'Outfit', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: {SLATE_50};
}}
.page-header p {{
    font-size: 0.85rem;
    color: {SLATE_400};
}}

/* ══════════════════════════════════════════════════════════════════════════════
   DATAFRAMES — Midnight Dark Treatment
   ══════════════════════════════════════════════════════════════════════════════ */
div[data-testid="stDataFrame"] {{
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.05);
    background: rgba(15, 23, 42, 0.5) !important;
}}
div[data-testid="stDataFrame"] thead th {{
    background: {SLATE_950} !important;
    color: {SLATE_400} !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(255,255,255,0.05) !important;
}}
div[data-testid="stDataFrame"] tbody td {{
    color: {SLATE_50} !important;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   KPI CARDS — Glassmorphism Midnight
   ══════════════════════════════════════════════════════════════════════════════ */
.kpi-container {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
    animation: slideUp 0.5s ease;
}}
.kpi-card {{
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    gap: 18px;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    overflow: hidden;
    max-width: 380px;
}}
.kpi-card:hover {{
    transform: translateY(-6px) scale(1.02);
    background: rgba(30, 41, 59, 0.6);
    border-color: rgba(255,255,255,0.15);
    box-shadow: 0 15px 45px rgba(0,0,0,0.4);
}}
.kpi-icon-wrapper {{
    position: relative;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.kpi-icon-bg {{
    position: absolute;
    inset: 0;
    background: var(--accent-color, #94A3B8);
    opacity: 0.1;
    border-radius: 12px;
    transition: all 0.3s ease;
}}
.kpi-card:hover .kpi-icon-bg {{
    opacity: 0.2;
    transform: rotate(45deg);
}}
.kpi-icon {{
    font-size: 1.8rem;
    z-index: 1;
    filter: drop-shadow(0 0 8px var(--accent-color, transparent));
}}
.kpi-title {{
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: {SLATE_400};
    margin-bottom: 4px;
    font-weight: 700;
}}
.kpi-value {{
    font-family: 'JetBrains Mono', 'Outfit', monospace;
    font-size: 1.7rem;
    font-weight: 700;
    color: {SLATE_50};
    line-height: 1;
    letter-spacing: -0.5px;
}}
/* Shimmer sweep on KPI cards */
.kpi-card::after {{
    content: '';
    position: absolute;
    top: 0; bottom: 0;
    width: 60%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.03), transparent);
    animation: cardShimmer 12s ease-in-out infinite;
    pointer-events: none;
}}
.kpi-glass-reflect {{
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 50%;
    background: linear-gradient(to bottom, rgba(255,255,255,0.03), transparent);
    pointer-events: none;
}}
.kpi-card.info    {{ --accent-color: {GOLD_ACCENT}; border-bottom: 2px solid rgba(245, 158, 11, 0.2); }}
.kpi-card.success {{ --accent-color: {EMERALD_ACCENT}; border-bottom: 2px solid rgba(16, 185, 129, 0.2); }}
.kpi-card.danger  {{ --accent-color: #EF4444; border-bottom: 2px solid rgba(239, 68, 68, 0.2); }}

.kpi-card.info .kpi-value    {{ color: {GOLD_ACCENT}; text-shadow: 0 0 20px rgba(245, 158, 11, 0.2); }}
.kpi-card.success .kpi-value {{ color: {EMERALD_ACCENT}; text-shadow: 0 0 20px rgba(16, 185, 129, 0.2); }}
.kpi-card.danger .kpi-value  {{ color: #EF4444; text-shadow: 0 0 20px rgba(239, 68, 68, 0.2); }}

/* ══════════════════════════════════════════════════════════════════════════════
   DECISION PANEL (cuarentena)
   ══════════════════════════════════════════════════════════════════════════════ */
.decision-panel {{
    background: var(--glass-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--glass-border);
    border-left: 4px solid var(--teal-light);
    border-radius: var(--radius-md);
    padding: 20px 24px;
    margin-top: 12px;
    box-shadow: var(--shadow-sm);
    animation: fadeIn 0.3s ease;
}}
.decision-panel h4 {{ color: var(--teal-primary); margin: 0 0 12px 0; font-size: 1.02rem; }}
.decision-info {{
    background: rgba(248, 250, 252, 0.8);
    border-radius: var(--radius-sm);
    padding: 12px 16px;
    margin-bottom: 14px;
    border: 1px solid rgba(0,0,0,0.05);
    font-size: 0.86rem;
    color: var(--slate-700);
}}

/* ══════════════════════════════════════════════════════════════════════════════
   BUTTONS — Midnight Premium
   ══════════════════════════════════════════════════════════════════════════════ */
.stButton > button {{
    border-radius: 12px;
    font-weight: 600;
    font-size: 0.86rem;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(30, 41, 59, 0.5) !important;
    color: {SLATE_50} !important;
    backdrop-filter: blur(8px);
    letter-spacing: 0.2px;
    transition: all 0.3s ease;
}}
.stButton > button:hover {{
    background: rgba(245, 158, 11, 0.15) !important;
    border-color: rgba(245, 158, 11, 0.3) !important;
    color: {GOLD_ACCENT} !important;
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
}}

/* ══════════════════════════════════════════════════════════════════════════════
   BANNER — Midnight
   ══════════════════════════════════════════════════════════════════════════════ */
.banner-aviso {{
    background: rgba(245, 158, 11, 0.06);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(245, 158, 11, 0.15);
    border-left: 4px solid {GOLD_ACCENT};
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 0.86rem;
    color: {SLATE_400};
    margin-bottom: 20px;
    animation: fadeIn 0.3s ease;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   TABLE PREMIUM — Midnight Glass
   ══════════════════════════════════════════════════════════════════════════════ */
.tabla-premium-wrapper {{
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    background: {SURFACE_GLASS};
    backdrop-filter: blur(12px);
}}
.tabla-premium thead tr {{
    background: {SLATE_950};
}}
.tabla-premium thead th {{
    color: {GOLD_ACCENT};
    font-family: 'Outfit', sans-serif;
    font-size: 0.7rem;
    letter-spacing: 1px;
    padding: 14px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}}
.tabla-premium tbody td {{
    color: {SLATE_50};
    padding: 12px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}}
.tabla-premium tbody tr:hover {{
    background: rgba(255,255,255,0.02) !important;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   PAGINATION
   ══════════════════════════════════════════════════════════════════════════════ */
.pagi-info-box {{ padding: 8px 0; }}
.pagi-info {{
    font-size: 0.84rem;
    color: var(--slate-500);
    font-weight: 500;
}}
.paginacion-bar {{
    text-align: center;
    padding: 8px 0;
    margin-bottom: 8px;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   METRIC CARDS (native Streamlit)
   ══════════════════════════════════════════════════════════════════════════════ */
div[data-testid="stMetric"] {{
    background: var(--glass-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    box-shadow: var(--shadow-sm);
    animation: fadeIn 0.4s ease;
}}
div[data-testid="stMetric"]:hover {{
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}}

/* ══════════════════════════════════════════════════════════════════════════════
   EXPANDERS
   ══════════════════════════════════════════════════════════════════════════════ */
details[data-testid="stExpander"] {{
    background: var(--glass-bg) !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    border-radius: var(--radius-md) !important;
    box-shadow: var(--shadow-xs);
}}
details[data-testid="stExpander"] summary {{
    font-weight: 600;
    font-size: 0.92rem;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   TABS — Midnight
   ══════════════════════════════════════════════════════════════════════════════ */
button[data-baseweb="tab"] {{
    color: {SLATE_400} !important;
    border-bottom: 2px solid transparent !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {GOLD_ACCENT} !important;
    border-bottom: 2px solid {GOLD_ACCENT} !important;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   CONTAINERS & FORMS (Glass treatment)
   ══════════════════════════════════════════════════════════════════════════════ */
div[data-testid="stForm"],
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"] > div > div > div > div[data-testid="stForm"] {{
    background: var(--glass-bg) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--glass-border) !important;
    border-radius: var(--radius-lg) !important;
}}

/* ══════════════════════════════════════════════════════════════════════════════
   SCROLLBARS — Visible en Windows
   ══════════════════════════════════════════════════════════════════════════════ */
* {{
    scrollbar-width: thin;
    scrollbar-color: rgba(148, 163, 184, 0.45) transparent;
}}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-track {{ background: transparent; }}
::-webkit-scrollbar-thumb {{
    background: rgba(148, 163, 184, 0.45);
    border-radius: 10px;
}}
::-webkit-scrollbar-thumb:hover {{ background: rgba(245, 158, 11, 0.6); }}
/* Scrollbar lateral del stepper (neural-monitor) */
.stepper-panel::-webkit-scrollbar {{ width: 5px; }}
.stepper-panel::-webkit-scrollbar-thumb {{ background: rgba(100,116,139,0.2); }}

/* ══════════════════════════════════════════════════════════════════════════════
   RESPONSIVE
   ══════════════════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {{
    .page-header {{ padding: 18px 20px; }}
    .page-header h1 {{ font-size: 1.25rem; }}
    .kpi-container {{ gap: 10px; }}
    .kpi-card {{ min-width: 140px; padding: 16px 18px; }}
    .kpi-value {{ font-size: 1.35rem; }}
    .tabla-premium {{ font-size: 0.78rem; }}
    .tabla-premium thead th {{ padding: 10px 12px; font-size: 0.72rem; }}
    .tabla-premium tbody td {{ padding: 8px 12px; }}
}}

/* ══════════════════════════════════════════════════════════════════════════════
   NEURAL MONITOR — Data Flow Visualization
   ══════════════════════════════════════════════════════════════════════════════ */
.neural-wrapper {{
    display: flex;
    align-items: stretch;
    gap: 20px;
    animation: fadeIn 0.4s ease;
}}
.neural-viz {{
    flex: 0 0 260px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(145deg, #FAFBFC, #F1F5F4);
    border-radius: var(--radius-lg);
    border: 1px solid #EEF2F6;
    padding: 16px;
    position: relative;
    overflow: hidden;
}}
.neural-viz svg {{
    width: 100%;
    height: auto;
    max-height: 200px;
}}
/* Phase label below the SVG */
.neural-phase-label {{
    position: absolute;
    bottom: 10px;
    left: 0; right: 0;
    text-align: center;
    font-family: 'Outfit', 'Inter', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
}}

/* ── Vertical Stepper ── */
.stepper-panel {{
    flex: 1;
    max-height: 280px;
    overflow-y: auto;
    padding: 4px 0;
}}
.step-item {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 8px 12px;
    border-radius: 8px;
    transition: opacity 0.4s ease, background 0.2s ease;
    position: relative;
}}
.step-item + .step-item::before {{
    content: '';
    position: absolute;
    left: 22px;
    top: -5px;
    width: 2px;
    height: 12px;
    background: #E2E8F0;
}}
.step-item.step-done {{
    opacity: 0.38;
}}
.step-item.step-active {{
    opacity: 1;
    background: rgba(27,107,90,0.04);
    border-radius: 8px;
}}
.step-item.step-pending {{
    opacity: 0.25;
}}
.step-dot {{
    width: 16px;
    height: 16px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 2px;
    border: 2px solid #CBD5E1;
    background: #FFFFFF;
    transition: all 0.3s ease;
}}
.step-done .step-dot {{
    background: #10B981;
    border-color: #10B981;
}}
.step-active .step-dot {{
    border-color: var(--teal-primary);
    background: var(--teal-primary);
    box-shadow: 0 0 0 4px rgba(27,107,90,0.15);
    animation: softPulse 1.5s ease-in-out infinite;
}}
.step-error .step-dot {{
    background: #EF4444;
    border-color: #EF4444;
}}
.step-label {{
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--slate-700);
    line-height: 1.35;
}}
.step-active .step-label {{
    font-weight: 600;
    color: var(--teal-primary);
}}
.step-meta {{
    font-size: 0.68rem;
    color: var(--slate-500);
    margin-top: 1px;
}}

</style>
"""

def obtener_css() -> str:
    return CSS_PORTAL

def aplicar_css():
    st.markdown(obtener_css(), unsafe_allow_html=True)

def header_pagina(icono: str, titulo: str, descripcion: str = ""):
    st.markdown(f"""
        <div class="page-header">
            <div style="display:flex; flex-direction:column; min-width:0;">
                <h1 style="margin:0;">{icono} {titulo}</h1>
                {'<p style="margin:2px 0 0 0;">' + descripcion + '</p>' if descripcion else ''}
            </div>
        </div>
    """, unsafe_allow_html=True)


# ── Funciones de color (legacy — usados por pandas .style) ────────────────────

def colorear_estado(val):
    colores = {
        "✅ OK":          "background-color:rgba(46,139,87,0.15); color:#2E8B57; font-weight:600",
        "⚠️ Con errores": "background-color:rgba(230,126,34,0.15); color:#E67E22; font-weight:600",
        "❌ Falló":       "background-color:rgba(192,57,43,0.15); color:#C0392B; font-weight:600",
        "Pendiente":      "background-color:rgba(57,73,171,0.15); color:#3949AB; font-weight:600",
    }
    return colores.get(val, "")

def colorear_severidad(val):
    colores = {
        "CRÍTICO": "background-color:rgba(192,57,43,0.15); color:#C0392B; font-weight:bold",
        "ALTO":    "background-color:rgba(230,126,34,0.15); color:#E67E22; font-weight:bold",
        "MEDIO":   "background-color:rgba(46,139,87,0.15); color:#2E8B57; font-weight:bold",
    }
    return colores.get(val, "")

def score_a_color(score: float) -> str:
    if score is None:
        return "⚪"
    try:
        s = float(score)
        if s >= 0.85:
            return "🟢"
        elif s >= 0.70:
            return "🟡"
    except (ValueError, TypeError):
        pass
    return "🔴"

def crear_tarjeta_kpi(titulo: str, valor: str, icono: str, tipo: str = "") -> str:
    """Renderiza una tarjeta KPI HTML Ultra Premium."""
    clase_tipo = f" {tipo}" if tipo else ""
    return f"""<div class="kpi-card{clase_tipo}">
    <div class="kpi-icon-wrapper">
        <div class="kpi-icon-bg"></div>
        <div class="kpi-icon">{icono}</div>
    </div>
    <div class="kpi-content">
        <div class="kpi-title">{titulo}</div>
        <div class="kpi-value">{valor}</div>
    </div>
    <div class="kpi-glass-reflect"></div>
</div>"""

def crear_panel_metricas_premium(metricas: list[dict], pct_progreso: float = None, texto_progreso: str = "", labels_progreso: dict = None) -> None:
    """
    Genera un panel unificado de métricas Zenith Premium (Minimalista).
    Soporta barra de progreso y métricas horizontales en una sola línea colapsada.
    """
    def _stat_html(label, value, color="#F8FAFC"):
        return f'<div style="text-align:center;"><div style="font-family:\'JetBrains Mono\',monospace; font-size:1.3rem; font-weight:700; color:{color}; line-height:1;">{value}</div><div style="font-size:0.55rem; text-transform:uppercase; letter-spacing:1.5px; color:#64748B; font-weight:600; margin-top:4px;">{label}</div></div>'

    stats_html = []
    for i, m in enumerate(metricas):
        stats_html.append(_stat_html(m["label"], m["value"], m.get("color", "#F8FAFC")))
        if i < len(metricas) - 1:
            stats_html.append('<div style="width:1px; height:32px; background:rgba(255,255,255,0.06);"></div>')

    progreso_html = ""
    if pct_progreso is not None:
        l_ok = labels_progreso.get("ok", "OK") if labels_progreso else "OK"
        l_err = labels_progreso.get("error", "Error") if labels_progreso else "Error"
        progreso_html = f'<div style="margin-top:20px;"><div style="display:flex; justify-content:space-between; margin-bottom:6px;"><span style="font-size:0.6rem; color:#94A3B8; text-transform:uppercase; letter-spacing:1.5px; font-weight:700;">{texto_progreso}</span><span style="font-family:\'JetBrains Mono\',monospace; font-size:0.75rem; color:#F8FAFC; font-weight:600;">{pct_progreso}%</span></div><div style="height:6px; background:rgba(255,255,255,0.04); border-radius:99px; overflow:hidden;"><div style="height:100%; width:{pct_progreso}%; border-radius:99px; background:linear-gradient(90deg, #10B981, #34D399); transition:width 0.6s ease;"></div></div><div style="display:flex; justify-content:space-between; margin-top:6px; font-size:0.6rem; color:#94A3B8;"><span>✅ {l_ok}</span><span>❌ {l_err}</span></div></div>'

    html = f'<div style="background:rgba(30, 41, 59, 0.35); backdrop-filter:blur(16px); border:1px solid rgba(255,255,255,0.05); border-radius:20px; padding:24px 32px; margin-bottom:24px; box-shadow:0 8px 30px rgba(0,0,0,0.2);"><div style="display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap;">{"".join(stats_html)}</div>{progreso_html}</div>'
    st.markdown(html, unsafe_allow_html=True)



# ── Componente de Paginación Premium (local — para DataFrames en memoria) ─────

def crear_paginacion_ui(count: int, page_size: int, key: str) -> tuple[int, int]:
    """
    Renderiza controles de paginación local y retorna (start_idx, end_idx).
    Para paginación SQL usar seccion_tabla_sql_paginada() de componentes.py.
    """
    total_pages = max(1, math.ceil(count / page_size)) if count > 0 else 1

    st_key = f"pagi_{key}"
    if st_key not in st.session_state:
        st.session_state[st_key] = 1
    st.session_state[st_key] = max(1, min(st.session_state[st_key], total_pages))

    current = st.session_state[st_key]
    start_idx = (current - 1) * page_size
    end_idx = min(start_idx + page_size, count)

    if total_pages <= 1 and count > 0:
        st.markdown(f"""
            <div class="paginacion-bar">
                <span class="pagi-info">{start_idx + 1} a {end_idx} de {count}</span>
            </div>
        """, unsafe_allow_html=True)
        return 0, count

    if count == 0:
        return 0, 0

    col_info, col_nav = st.columns([1, 2])

    with col_info:
        st.markdown(f"""
            <div class="pagi-info-box">
                <span class="pagi-info">{start_idx + 1} a {end_idx} de {count}</span>
            </div>
        """, unsafe_allow_html=True)

    with col_nav:
        b1, b2, b3, b4, b5 = st.columns([1, 1, 3, 1, 1])
        with b1:
            if st.button("⏮", key=f"btn_first_{key}", disabled=current <= 1, width='stretch', help="Primera página"):
                st.session_state[st_key] = 1
                st.rerun()
        with b2:
            if st.button("◀", key=f"btn_prev_{key}", disabled=current <= 1, width='stretch', help="Anterior"):
                st.session_state[st_key] -= 1
                st.rerun()
        with b3:
            st.markdown(f"""
                <div style="text-align:center; padding:6px 0; font-size:0.9rem; font-weight:600; color:var(--text-color);">
                    Pág {current} de {total_pages}
                </div>
            """, unsafe_allow_html=True)
        with b4:
            if st.button("▶", key=f"btn_next_{key}", disabled=current >= total_pages, width='stretch', help="Siguiente"):
                st.session_state[st_key] += 1
                st.rerun()
        with b5:
            if st.button("⏭", key=f"btn_last_{key}", disabled=current >= total_pages, width='stretch', help="Última página"):
                st.session_state[st_key] = total_pages
                st.rerun()

    return start_idx, end_idx


# ── Generador de vista interactiva (nativa) ──────────────────────────────────

def _configurar_columnas_dataframe(cols: list, columnas_check: list | None) -> dict:
    """Configura las columnas de casillas de verificación si se proveen."""
    config = {}
    if columnas_check:
        for c in columnas_check:
            if c in cols:
                config[c] = st.column_config.CheckboxColumn(c, disabled=True)
    return config

def renderizar_tabla_premium(df, key: str, page_size: int = 15,
                              columnas_check: list = None,
                              columnas_ocultas: list = None):
    """
    Tabla interactiva nativa con paginación LOCAL externa.
    """
    if df is None or df.empty:
        st.info("No hay datos para mostrar.")
        return

    if columnas_ocultas:
        df = df.drop(columns=[c for c in columnas_ocultas if c in df.columns], errors='ignore')

    count = len(df)
    start, end = crear_paginacion_ui(count, page_size, key)
    df_slice = df.iloc[start:end]

    config = _configurar_columnas_dataframe(df_slice.columns, columnas_check)

    st.dataframe(
        df_slice,
        width='stretch',
        hide_index=True,
        column_config=config,
    )


def renderizar_tabla_premium_raw(df, columnas_check=None, columnas_ocultas=None):
    """
    Tabla interactiva nativa SIN paginación propia.
    (Diseñada para SQL Server paginado).
    """
    if df is None or df.empty:
        st.info("No hay datos para mostrar.")
        return

    if columnas_ocultas:
        df = df.drop(columns=[c for c in columnas_ocultas if c in df.columns], errors='ignore')

    config = _configurar_columnas_dataframe(df.columns, columnas_check)

    st.dataframe(
        df,
        width='stretch',
        hide_index=True,
        column_config=config,
    )
