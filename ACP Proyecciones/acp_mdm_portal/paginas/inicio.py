import os
import re
import pandas as pd
import streamlit as st
from datetime import datetime

from utils.auth import tiene_permiso
from utils.componentes import banner_aviso, estado_vacio_html, health_status_panel, seccion_tabla_con_guardar
from utils.formato import EMERALD_ACCENT, GOLD_ACCENT, SLATE_400, header_pagina, crear_panel_metricas_premium
from utils.api_client import get_api, mostrar_error_api, post_api, stream_api, delete_api, obtener_url_backend

# ── Constantes de fases ETL ──────────────────────────────────────────────────
_RE_PASO = re.compile(r"^\[(\d+)/(\d+)\]\s+(.+)$")

# Nombres operacionales: sin metáforas de IA. Colores de la paleta del sistema.
FASES_ETL = {
    "config": {"nombre": "Configuración",        "color": "#4d6b54", "rango": (1, 2),  "icono": "⚙️"},
    "bronce": {"nombre": "Carga Raw",             "color": "#e8a020", "rango": (3, 3),  "icono": "📥"},
    "silver": {"nombre": "Transformación Silver", "color": "#8fa897", "rango": (4, 20), "icono": "⚗️"},
    "gold":   {"nombre": "Capa Gold",             "color": "#2db87a", "rango": (21, 99),"icono": "✅"},
}

def _detectar_fase(paso_num: int) -> str:
    for clave, fase in FASES_ETL.items():
        lo, hi = fase["rango"]
        if lo <= paso_num <= hi:
            return clave
    return "silver"


def _generar_monitor_canvas(
    id_corrida: str,
    token: str,
    phase_init: str = "raw",
    altura: int = 420,
    backend_url: str = "",
) -> str:
    """
    Retorna un documento HTML completo con la red neuronal canvas animada.
    Se conecta directamente al backend (SSE via fetch) para no bloquear Streamlit
    ni causar parpadeo al recargarse el iframe.
    """
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  :root {{
    --primary: #3b82f6;
    --accent: #00ff96;
    --bg: #020617;
    --glass: rgba(15,23,42,0.85);
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  
  /* Hacemos el body transparente para que herede el color nativo de Streamlit */
  body {{
    background: #F1F5F4; /* mismo tono del app background para que el iframe no tenga franja blanca */
    color:#fff;
    font-family:'Orbitron',sans-serif;
    overflow:hidden;
    display:flex;
    height:100vh;
    width:100vw;
    padding: 12px;
  }}
  
  /* Contenedor principal — fondo oscuro propio para que funcione el blending aditivo neon */
  .network-container {{
    flex: 1;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at center, #0B1120 0%, #02040A 100%);
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35), 0 0 0 1px rgba(27,107,90,0.25);
    overflow: hidden;
    position: relative;
  }}
  
  canvas {{ display:block; width:100%; height:100%; }}
</style>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>

<div class="network-container">
  <canvas id="c"></canvas>
</div>

<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');

let W, H, neurons = [], synapses = [], particles = [];
const COLORS = {{ 
    raw: '#0ea5e9',      // Bright Sky Blue
    bronze: '#f97316',   // Neon Copper/Orange
    transformer: '#a8a2db', // Muted purple for engine
    silver: '#a8b1ff',   // Electric Indigo/Silver
    gold: '#facc15',     // Sun Gold
    accent: '#06b6d4'
}};

let PHASE = "{phase_init}";
let currentStep = 0;

function resize() {{
  W = canvas.width  = canvas.offsetWidth;
  H = canvas.height = canvas.offsetHeight;
  initNet();
}}

function injectParticles(amount) {{
    for(let i=0;i<amount;i++) particles.push(new Particle());
}}

function initNet() {{
  neurons = []; synapses = [];
  
  // RAW - Origin Servers (Left edge)
  for(let i=0; i<4; i++) neurons.push({{x: W*0.08, y: H*(0.3 + i*0.13) + (Math.random()-0.5)*20, role:'raw', active:0}});
  
  // BRONZE - Landing Hubs (Mid-Left)
  for(let i=0; i<5; i++) neurons.push({{x: W*0.28 + (Math.random()-0.5)*40, y: H*0.5 + (Math.random()-0.5)*250, role:'bronze', active:0}});
  
  // TRANSFORMER - Spark Engine Core (Center Cluster)
  for(let i=0; i<18; i++) neurons.push({{x: W*0.5 + (Math.random()-0.5)*120, y: H*0.5 + (Math.random()-0.5)*300, role:'transformer', active:0}});
  
  // SILVER - Data Marts (Mid-Right)
  for(let i=0; i<5; i++) neurons.push({{x: W*0.72 + (Math.random()-0.5)*40, y: H*0.5 + (Math.random()-0.5)*250, role:'silver', active:0}});
  
  // GOLD - BI Serving Layer (Right edge)
  for(let i=0; i<3; i++) neurons.push({{x: W*0.92, y: H*(0.35 + i*0.1) + (Math.random()-0.5)*20, role:'gold', active:0}});

  // Generación guiada de Sinapsis (flujo horizontal)
  neurons.forEach((n1,i) => neurons.forEach((n2,j) => {{
    if(i===j) return;
    const ok =
      (n1.role==='raw'         && n2.role==='bronze')       ||
      (n1.role==='bronze'      && n2.role==='transformer')  ||
      (n1.role==='transformer' && n2.role==='transformer')  ||
      (n1.role==='transformer' && n2.role==='silver')       ||
      (n1.role==='silver'      && n2.role==='gold');
      
    const distY = Math.abs(n1.y - n2.y);
    // Evitamos cruces verticales caóticos (max 60% alto)
    if(ok && distY < H*0.6 && Math.random()<0.25)
      synapses.push({{from:n1,to:n2,cp:{{x:(n1.x+n2.x)/2+(Math.random()-0.5)*80, y:(n1.y+n2.y)/2+(Math.random()-0.5)*80}}}});
  }}));
  
  if (PHASE !== 'raw') {{
      injectParticles(PHASE === 'gold' ? 250 : PHASE === 'silver' ? 150 : 80);
      setTimeout(() => particles.forEach(p => p.state = 'seek'), 500);
  }} else {{
      injectParticles(50); // Ambientales iniciales para que no se vea vacío
  }}
}}

class Particle {{
  constructor() {{ this.reset(); }}
  reset() {{
    this.role = 'raw';
    // Nacimiento desde el conector del marco izquierdo (Data sources origin)
    this.x = -20;
    this.y = H*0.25 + Math.random()*H*0.5;
    // Viaje impulsado hacia la derecha buscando los hubs raw/bronze
    this.vx = 0.5 + Math.random(); 
    this.vy = (Math.random()-.5)*0.5;
    this.color = COLORS.raw; 
    this.size = Math.random()*2+1.5;
    this.hub=null; this.target=null; this.synapse=null; this.progress=0; this.life=1;
    this.state='float';
  }}
  update() {{
    if(this.state==='float') {{
      this.vx+=(W*0.08-this.x)*0.0008+(Math.random()-.5)*0.3;
      this.vy+=(H*0.8 -this.y)*0.0008+(Math.random()-.5)*0.3;
      // Sólo inician el viaje si pasamos el raw (Config)
      if(PHASE !== 'raw' && Math.random()<0.005) this.state='seek';
    }} else if(this.state==='seek') {{
      const hubs=neurons.filter(n=>n.role==='bronze');
      if(!this.hub) this.hub=hubs[Math.floor(Math.random()*hubs.length)];
      this.vx+=(this.hub.x-this.x)*0.025; this.vy+=(this.hub.y-this.y)*0.025;
      if(Math.hypot(this.hub.x-this.x,this.hub.y-this.y)<12){{
        this.state='orbit'; this.role='bronze'; this.color=COLORS.bronze;
      }}
    }} else if(this.state==='orbit') {{
      this.vx+=(this.hub.x-this.x)*0.02; this.vy+=(this.hub.y-this.y)*0.02;
      // Viajan hacia adelante dependiendo de la fase actual
      let canTravel = (this.role==='bronze' && (PHASE==='silver'||PHASE==='gold')) ||
                      (this.role==='silver' && PHASE==='gold');
      if(canTravel && Math.random()<0.015) this.state='travel';
    }} else if(this.state==='travel') {{
      if(!this.target) {{
        const opts=synapses.filter(s=>s.from===this.hub);
        if(opts.length>0) {{
          this.synapse=opts[Math.floor(Math.random()*opts.length)];
          this.target=this.synapse.to; this.progress=0;
        }} else {{ this.state='orbit'; }}
      }} else {{
        this.progress+=0.010+Math.random()*0.008; // Ligeramente más lento
        const p0=this.hub,p1=this.synapse.cp,p2=this.target;
        const t=this.progress;
        this.x=(1-t)**2*p0.x+2*(1-t)*t*p1.x+t**2*p2.x;
        this.y=(1-t)**2*p0.y+2*(1-t)*t*p1.y+t**2*p2.y;
        if(this.progress>=1) {{
          this.hub=this.target; this.target=null; this.synapse=null; this.progress=0;
          this.hub.active=1.0;
          const r=this.hub.role;
          if(r==='transformer') this.color='rgba(255,255,255,0.8)';
          if(r==='silver') {{ this.state='orbit'; this.role='silver'; this.color=COLORS.silver; }}
          if(r==='gold') {{ this.state='consume'; this.role='gold'; this.color=COLORS.gold; }}
          else this.state='orbit';
        }}
      }}
    }} else if(this.state==='consume') {{
      this.vx+=1.0; this.vy+=(Math.random()-.5)*1;
      this.life-=0.015;
      if(this.life<=0) this.reset();
    }}
    this.vx*=0.94; this.vy*=0.94;
    if(this.state!=='travel'){{ this.x+=this.vx; this.y+=this.vy; }}
  }}
  draw() {{
    ctx.save();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = this.life * (this.state==='travel'?1:0.75);
    
    // Renderizado por Gradiente Radial (Bokeh/Neon Effect Premium)
    const renderSize = this.size * 2.5;
    const rg = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, renderSize);
    rg.addColorStop(0, '#ffffff'); // Núcleo blanco caliente
    rg.addColorStop(0.3, this.color); // Color eléctrico de la fase
    rg.addColorStop(1, 'transparent'); // Difuminación
    
    ctx.fillStyle = rg;
    ctx.beginPath();
    ctx.arc(this.x, this.y, renderSize, 0, Math.PI*2);
    ctx.fill();
    ctx.restore();
  }}
}}

// Funciones para sincronizar el Stream

function injectParticles(amount) {{
    let injected = 0;
    // Suavizamos lanzando 4 partículas cada 30ms en lugar de todas a la vez
    const interval = setInterval(() => {{
        for(let i=0; i<4 && injected<amount; i++) {{
            particles.push(new Particle());
            injected++;
        }}
        if(injected >= amount) clearInterval(interval);
    }}, 30);
}}

async function startWebStream() {{
    if(!'{id_corrida}') return;
    try {{
        const res = await fetch("{backend_url}/api/v1/etl/corridas/{id_corrida}/eventos", {{
            headers: {{ 
                "Authorization": "Bearer {token}",
                "Accept": "text/event-stream"
            }}
        }});
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        while (true) {{
            const {{value, done}} = await reader.read();
            if (done) break;
            const textData = decoder.decode(value);
            const lines = textData.split("\\n");
            
            for(let line of lines) {{
                if(line.startsWith("data:")) {{
                    const payload = line.substring(5).trim();
                    if(payload === "[DONE]") return;
                    processLog(payload);
                }}
            }}
        }}
    }} catch(e) {{
        console.error("Stream closed", e);
    }}
}}

function processLog(msg) {{
    const match = msg.match(/^\\[(\\d+)\\/(\\d+)\\]/);
    if(match) {{
        const step = parseInt(match[1]);
        if(step > currentStep) {{
            currentStep = step;
            // Actualizamos la fase y lanzamos oleadas de forma gradual
            if(step >= 1 && step <= 2 && PHASE !== 'raw') {{
                PHASE = 'raw';
                injectParticles(60);
            }} else if (step === 3 && PHASE !== 'bronze') {{
                PHASE = 'bronze';
                injectParticles(150); // Datos fluyen suavemente
            }} else if (step >= 4 && step <= 20 && PHASE !== 'silver') {{
                PHASE = 'silver';
                injectParticles(180); 
            }} else if (step >= 21 && PHASE !== 'gold') {{
                PHASE = 'gold';
                injectParticles(80); 
            }}
        }}
    }}
}}

function draw() {{
  // 1. Fondo principal ultra-oscuro para contraste de neon
  ctx.globalCompositeOperation = 'source-over';
  ctx.fillStyle='rgba(2, 4, 10, 0.25)'; // Trail sutil y oscuro
  ctx.fillRect(0,0,W,H);

  // Gradiente radial de fondo muy sutil
  const grd = ctx.createRadialGradient(W/2, H/2, 0, W/2, H/2, W);
  grd.addColorStop(0, 'rgba(59,130,246,0.03)');
  grd.addColorStop(1, 'transparent');
  ctx.fillStyle = grd;
  ctx.fillRect(0,0,W,H);

  // Activamos additive blending para luces neón puras
  ctx.globalCompositeOperation = 'lighter';

  // 2. Dibujar Sinapsis (Conexiones)
  synapses.forEach(s=>{{
    ctx.beginPath();
    ctx.moveTo(s.from.x,s.from.y);
    ctx.quadraticCurveTo(s.cp.x,s.cp.y,s.to.x,s.to.y);
    const a = 0.03 + s.from.active*0.15 + s.to.active*0.15;
    const sc = s.from.role==='bronze'?'#cd7f32': s.from.role==='silver'?'#e2e8f0':
               s.from.role==='gold'?'#ffd700':'#3b82f6';
    ctx.strokeStyle=`rgba(${{sc.replace('#','').match(/../g).map(h=>parseInt(h,16)).join(',')}}, ${{a}})`;
    ctx.lineWidth=0.8 + s.from.active*1;
    ctx.stroke();
  }});

  // 3. Dibujar Nodos (Hubs)
  neurons.forEach(n=>{{
    const roleColor = COLORS[n.role]||'#3b82f6';
    
    // Anillo de pulso exterior electromagnético
    if (n.active > 0.05) {{
        ctx.beginPath();
        ctx.arc(n.x, n.y, 4 + n.active*14, 0, Math.PI*2);
        ctx.strokeStyle = roleColor;
        ctx.globalAlpha = n.active * 0.5;
        ctx.lineWidth = 1 + n.active;
        ctx.stroke();
        ctx.globalAlpha = 1.0;
    }}

    // Núcleo sólido del nodo
    ctx.beginPath();
    ctx.arc(n.x,n.y,2 + n.active*2,0,Math.PI*2);
    ctx.fillStyle = n.active>0.1? roleColor:'rgba(100,140,200,0.3)';
    
    if(n.active>0.1){{ ctx.shadowBlur=n.active*25; ctx.shadowColor=roleColor; }}
    ctx.fill();
    ctx.shadowBlur=0;
    
    n.active*=0.88; // Decaimiento suave
  }});

  ctx.globalCompositeOperation = 'source-over';

  // 4. Dibujar Partículas (dibujadas ahora desde su método draw de clase)
  particles.forEach(p => p.update());
  particles.forEach(p => p.draw());

  requestAnimationFrame(draw);
}}



def _generar_monitor_etl_html(fase_actual: str, paso_actual: int, total_pasos: int) -> str:
    """
    Genera el panel SVG del monitor de ejecución ETL.
    4 nodos en flujo horizontal (Config → Raw → Silver → Gold) conectados a un hub DWH central.
    Paleta del sistema: verde-tierra, ámbar, verde-cosecha.
    """
    color = FASES_ETL.get(fase_actual, FASES_ETL["silver"])["color"]
    nombre = FASES_ETL.get(fase_actual, FASES_ETL["silver"])["nombre"]
    icono  = FASES_ETL.get(fase_actual, FASES_ETL["silver"])["icono"]
    pct = min(100, int((paso_actual / max(total_pasos, 1)) * 100))

    # Nodos en flujo horizontal: izquierda → derecha
    nodos = {
        "config": (38,  105),
        "bronce": (105, 58),
        "silver": (105, 152),
        "gold":   (202, 105),
    }
    colores_nodos = {k: v["color"] for k, v in FASES_ETL.items()}
    cx, cy = 155, 105  # Hub DWH desplazado a la derecha

    lineas_svg = ""
    for clave, (nx, ny) in nodos.items():
        opacidad = "0.7" if clave == fase_actual else "0.15"
        grosor   = "1.5" if clave == fase_actual else "1"
        dash     = "" if clave == fase_actual else 'stroke-dasharray="4,4"'
        lineas_svg += (
            f'<line x1="{nx}" y1="{ny}" x2="{cx}" y2="{cy}" '
            f'stroke="{colores_nodos[clave]}" stroke-width="{grosor}" '
            f'opacity="{opacidad}" {dash}/>'
        )

    nodos_svg = ""
    for clave, (nx, ny) in nodos.items():
        nc = colores_nodos[clave]
        es_activo = clave == fase_actual
        r = "13" if es_activo else "9"
        op = "1" if es_activo else "0.28"
        label = FASES_ETL[clave]["icono"]

        nodos_svg += f'<circle cx="{nx}" cy="{ny}" r="{r}" fill="{nc}" opacity="{op}">'
        if es_activo:
            nodos_svg += (
                f'<animate attributeName="r" values="{r};{int(r)+3};{r}" '
                f'dur="2.4s" repeatCount="indefinite"/>'
            )
        nodos_svg += "</circle>"
        nodos_svg += (
            f'<text x="{nx}" y="{ny + 4}" text-anchor="middle" '
            f'font-size="10" fill="white" opacity="{op}">{label}</text>'
        )

    # Partículas: fluyen del nodo activo al hub DWH
    particulas_svg = ""
    if fase_actual in nodos:
        sx, sy = nodos[fase_actual]
        for delay in ("0s", "0.8s", "1.6s"):
            particulas_svg += f"""
<circle r="3" fill="{color}" opacity="0.85">
  <animate attributeName="cx" values="{sx};{cx}" dur="2s" begin="{delay}" repeatCount="indefinite"/>
  <animate attributeName="cy" values="{sy};{cy}" dur="2s" begin="{delay}" repeatCount="indefinite"/>
  <animate attributeName="opacity" values="0;0.85;0.85;0" dur="2s" begin="{delay}" repeatCount="indefinite"/>
  <animate attributeName="r" values="3;1.5;0.5" dur="2s" begin="{delay}" repeatCount="indefinite"/>
</circle>"""

    # Anillo de pulso del hub
    hub_pulse = (
        f'<circle cx="{cx}" cy="{cy}" r="26" fill="{color}" opacity="0.08">'
        f'<animate attributeName="r" values="26;31;26" dur="3s" repeatCount="indefinite"/>'
        f'</circle>'
    )

    svg = f"""<svg viewBox="0 0 240 210" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;">
  {lineas_svg}
  {hub_pulse}
  <circle cx="{cx}" cy="{cy}" r="20" fill="{color}" opacity="0.18"/>
  <circle cx="{cx}" cy="{cy}" r="14" fill="{color}" opacity="0.65"/>
  <text x="{cx}" y="{cy+1}" text-anchor="middle" font-size="7.5"
        fill="white" font-weight="700" font-family="Inter,sans-serif">DWH</text>
  <text x="{cx}" y="{cy+11}" text-anchor="middle" font-size="6"
        fill="white" opacity="0.65" font-family="Inter,sans-serif">{pct}%</text>
  {nodos_svg}
  {particulas_svg}
</svg>"""

    return f"""
<div style="
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    background:rgba(26,46,30,0.35); border:1px solid rgba(255,255,255,0.07);
    border-radius:14px; padding:12px 10px 8px 10px; height:100%;
">
  <div style="width:100%; flex:1; min-height:160px;">{svg}</div>
  <div style="
      margin-top:6px; font-size:0.72rem; font-weight:700;
      font-family:'JetBrains Mono',monospace; letter-spacing:0.5px;
      color:{color}; opacity:0.9; text-align:center;
  ">{icono} {nombre.upper()}</div>
  <div style="
      font-size:0.65rem; color:rgba(255,255,255,0.3);
      font-family:'Inter',sans-serif; margin-top:2px;
  ">Paso {paso_actual} de {total_pasos}</div>
</div>"""


def _generar_stepper_html(pasos: list[dict], paso_activo_idx: int) -> str:
    """Genera el HTML del stepper vertical con transparencia para pasos completados."""
    if not pasos:
        return '<div class="stepper-panel"><p style="color:#94A3B8;font-size:0.85rem;padding:16px;">Esperando pasos del runner...</p></div>'

    items_html = ""
    for i, paso in enumerate(pasos):
        if i < paso_activo_idx:
            clase = "step-item step-done"
        elif i == paso_activo_idx:
            clase = "step-item step-active"
        else:
            clase = "step-item step-pending"

        if paso.get("error"):
            clase = "step-item step-error"

        icono_fase = FASES_ETL.get(paso.get("fase", ""), {}).get("icono", "▪️")
        items_html += f'''
<div class="{clase}">
<div class="step-dot"></div>
<div>
<div class="step-label">{icono_fase} [{paso["num"]:02d}/{paso["total"]}] {paso["desc"]}</div>
<div class="step-meta">{paso.get("hora", "")}</div>
</div>
</div>'''

    return f'<div class="stepper-panel">{items_html}</div>'


def _cargar_resumen_ultima_carga() -> tuple[pd.DataFrame, str | None]:
    """Consulta directa al backend — sin caché. Retorna (df, error_msg)."""
    resultado = get_api("/etl/corridas")
    if resultado.ok and isinstance(resultado.data, list):
        corridas = resultado.data
        if corridas:
            return pd.DataFrame(corridas), None
        return pd.DataFrame(), None   # Backend OK pero sin corridas aún
    # Error real de conectividad — lo devolvemos para mostrarlo al usuario
    return pd.DataFrame(), resultado.error or "No se pudo conectar al backend."

def render():
    # Limpiar estado fantasma: en_ejecucion=True sin ID de corrida activa
    if st.session_state.get("etl_en_ejecucion") and not st.session_state.get("etl_id_corrida"):
        st.session_state["etl_en_ejecucion"] = False

    header_pagina("🏠", "Inicio", "Estado del pipeline · Data Warehouse ACP")
    conectado = health_status_panel()

    df_estado, error_carga = _cargar_resumen_ultima_carga()

    # —— Mostrar error de conectividad si el backend no respondio ————————————
    if error_carga:
        banner_aviso(
            f"<b>Backend no disponible.</b> {error_carga} "
            f"Verifica que el servidor FastAPI esté corriendo en <code>{obtener_url_backend()}</code>."
        )

    total_ok = 0
    total_rechaz = 0
    ultima_carga = "Sin datos"
    tablas_con_error = 0

    if not df_estado.empty and "estado" in df_estado.columns:
        if "fecha_inicio" in df_estado.columns:
            val = df_estado.iloc[0]["fecha_inicio"]
            if val is None or (hasattr(val, '__class__') and str(val) in ('NaT', 'nan', 'None')):
                ultima_carga = "Sin datos"
            else:
                try:
                    ts = pd.to_datetime(val)
                    ultima_carga = "Sin datos" if pd.isna(ts) else ts.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    ultima_carga = str(val)[:16]
        else:
            ultima_carga = "Sin datos"
        
        tablas_con_error = int((df_estado["estado"] == "ERROR").sum())
        total_ok = int(df_estado["filas_insertadas"].sum()) if "filas_insertadas" in df_estado.columns else 0
        total_rechaz = int(df_estado["filas_rechazadas"].sum()) if "filas_rechazadas" in df_estado.columns else 0

        # Mapeo reverso para que la tabla de historial se vea bien
        df_estado = df_estado.rename(columns=RENOMBRES_LOG_ETL)
        # Data Engineer: Proceso siempre = ETL_Pipeline y Archivo duplica Tabla → eliminar
        df_estado = df_estado.drop(columns=["Proceso", "Archivo"], errors="ignore")
        # Truncar timestamps a HH:MM:SS (misma fecha en la mayoría de corridas)
        for col_ts in ["Inicio", "Fin"]:
            if col_ts in df_estado.columns:
                try:
                    df_estado[col_ts] = pd.to_datetime(df_estado[col_ts]).dt.strftime("%m-%d %H:%M")
                except Exception:
                    pass
        # Mover Estado al frente para escaneo rápido
        cols_order = ["ID", "Tabla", "Estado", "Filas OK", "Rechaz.", "Seg.", "Inicio", "Error"]
        df_estado = df_estado[[c for c in cols_order if c in df_estado.columns]]

    # Usar panel de métricas premium compacto (Zenith)
    crear_panel_metricas_premium(
        metricas=[
            {"label": "Última carga",  "value": ultima_carga,           "color": GOLD_ACCENT},
            {"label": "Filas OK",      "value": f"{total_ok:,}",        "color": EMERALD_ACCENT},
            {"label": "Rechazadas",    "value": f"{total_rechaz:,}",    "color": "#EF4444" if total_rechaz > 0 else SLATE_400},
            {"label": "Con error",     "value": str(tablas_con_error),  "color": "#EF4444" if tablas_con_error > 0 else EMERALD_ACCENT},
        ]
    )

    st.markdown("### ⚡ Centro de Comando ETL")
    with st.container(border=True):

        c_up, c_run = st.columns([1.6, 1], gap="large")

        with c_up:
            archivo_subido = st.file_uploader(
                "📂 1. Seleccionar reporte Excel",
                type=["xlsx", "xls"],
                help="El archivo se copiará al directorio de entrada del ETL antes de lanzar el proceso.",
            )
            if archivo_subido is not None:
                _default_etl_dir = os.path.normpath(
                    os.path.join(os.path.dirname(__file__), "..", "..", "ETL", "data", "entrada")
                )
                destino_dir = os.getenv("ETL_INPUT_DIR", _default_etl_dir)
                os.makedirs(destino_dir, exist_ok=True)
                destino_path = os.path.join(destino_dir, archivo_subido.name)
                with open(destino_path, "wb") as f:
                    f.write(archivo_subido.getvalue())
                st.success(f"✅ Archivo guardado en `data/entrada/{archivo_subido.name}`")
                st.caption("💡 El ETL infiere la tabla destino por el nombre del archivo o su subcarpeta.")
                st.session_state["etl_archivo_listo"] = True
            else:
                st.session_state.setdefault("etl_archivo_listo", False)

        with c_run:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if tiene_permiso("ejecutar_etl"):
                en_ejecucion = st.session_state.get("etl_en_ejecucion", False)
                label_btn = "🔄 Pipeline corriendo..." if en_ejecucion else "🚀 2. Ejecutar Pipeline ETL"
                if st.button(label_btn, width="stretch", type="primary", disabled=en_ejecucion,
                             key="btn_ejecutar_etl"):
                    st.session_state["etl_en_ejecucion"] = True
                    st.session_state.pop("etl_log", None)
                    st.session_state.pop("etl_estado_final", None)
                    st.rerun()
            else:
                banner_aviso("🔒 Sin permiso para ejecutar el pipeline.")

    # ── Monitor de Ejecución ETL en vivo ──────────────────────────────────────
    if st.session_state.get("etl_en_ejecucion"):
        st.markdown("---")
        st.markdown("### ⚡ Monitor de Ejecución ETL")

        with st.container(border=True):
            col_info, col_cancel = st.columns([4, 1])
            with col_info:
                st.caption("🟡  Pipeline activo — datos fluyendo hacia el DWH.")
            with col_cancel:
                if st.button("❌ Cancelar", key="btn_cancelar_etl"):
                    id_act = st.session_state.get("etl_id_corrida")
                    if id_act:
                        delete_api(f"/etl/corridas/{id_act}")
                    st.session_state["etl_en_ejecucion"] = False
                    banner_aviso("Cancelación solicitada al runner.")
                    st.rerun()

            progreso         = st.progress(0, text="Conectando con el runner...")
            monitor_slot     = st.empty()
            log_expander_box = st.empty()

            log_acum     = ""
            estado_final = "OK"
            pasos_lista  = []
            fase_actual  = "config"
            paso_num     = 0
            total_pasos  = 22

            resultado = post_api("/etl/corridas", {"comentario": "Portal Streamlit - Ejecución manual"})
            if not resultado.ok or not isinstance(resultado.data, dict):
                mostrar_error_api(resultado, "No se pudo encolar el pipeline.")
                st.session_state["etl_en_ejecucion"] = False
                st.rerun()

            datos      = resultado.data
            id_corrida = datos["id_corrida"]
            st.session_state["etl_id_corrida"] = id_corrida
            log_acum += f"[✓] Corrida encolada — ID: {id_corrida}\n"

            # Layout monitor: nodos SVG (izq) + stepper (der)
            col_viz, col_steps = monitor_slot.columns([2, 3], gap="medium")

            for linea in stream_api(id_corrida):
                log_acum += linea + "\n"

                match = _RE_PASO.match(linea.strip())
                if match:
                    paso_num    = int(match.group(1))
                    total_pasos = int(match.group(2))
                    descripcion = match.group(3).strip()
                    fase_actual = _detectar_fase(paso_num)
                    hora_actual = datetime.now().strftime("%H:%M:%S")

                    pasos_lista.append({
                        "num": paso_num, "total": total_pasos,
                        "desc": descripcion, "fase": fase_actual,
                        "hora": hora_actual, "error": False,
                    })

                    pct = min(99, int((paso_num / max(total_pasos, 1)) * 100))
                    progreso.progress(pct, text=f"Paso {paso_num}/{total_pasos} — {descripcion[:55]}")

                    # Actualizar monitor SVG + stepper en cada paso
                    col_viz, col_steps = monitor_slot.columns([2, 3], gap="medium")
                    with col_viz:
                        st.markdown(
                            _generar_monitor_etl_html(fase_actual, paso_num, total_pasos),
                            unsafe_allow_html=True,
                        )
                    with col_steps:
                        st.markdown(
                            _generar_stepper_html(pasos_lista, len(pasos_lista) - 1),
                            unsafe_allow_html=True,
                        )

                linea_lower = linea.lower().strip()
                if "[FIN]" in linea and "éxito" in linea_lower:
                    estado_final = "OK"
                elif "error" in linea_lower and paso_num > 0:
                    estado_final = "ERROR"
                    if pasos_lista:
                        pasos_lista[-1]["error"] = True
                elif "[TIMEOUT]" in linea:
                    estado_final = "TIMEOUT"

                with log_expander_box.container():
                    with st.expander("🔧 Log técnico", expanded=False):
                        st.code(log_acum[-3000:], language="bash")

            progreso.progress(100, text="✅ Pipeline finalizado.")
            st.session_state["etl_en_ejecucion"] = False
            st.session_state["etl_log"]          = log_acum
            st.session_state["etl_estado_final"] = estado_final
            st.session_state["etl_pasos_lista"]  = pasos_lista
            st.session_state["etl_fase_actual"]  = fase_actual
            st.session_state["etl_paso_num"]     = paso_num
            st.session_state["etl_total_pasos"]  = total_pasos
            token_jwt = st.session_state.get("jwt_token", "")
            
            # Renderizar estado inicial del monitor canvas UNA VEZ
            with st.expander("👁️ Ocultar / Mostrar Animación Neural", expanded=True):
                components.html(
                    _generar_monitor_canvas(id_corrida, token_jwt, backend_url=URL_BACKEND),
                    height=420,
                    scrolling=False,
                )

            # Bucle de streaming SSE con parsing inteligente
            try:
                for linea in stream_api(id_corrida):
                    log_acum += linea + "\n"

                    # Detectar paso [XX/YY]
                    match = _RE_PASO.match(linea.strip())
                    if match:
                        paso_num    = int(match.group(1))
                        total_pasos = int(match.group(2))
                        descripcion = match.group(3).strip()
                        fase_actual = _detectar_fase(paso_num)
                        hora_actual = datetime.now().strftime("%H:%M:%S")

                        pasos_lista.append({
                            "num": paso_num,
                            "total": total_pasos,
                            "desc": descripcion,
                            "fase": fase_actual,
                            "hora": hora_actual,
                            "error": False,
                        })

                        # Ya no re-renderizamos el monitor visual acá para evitar parpadeos
                        # El Canvas gestionará su propia UI leyendo los eventos SSE en paralelo.

                        # Progreso real basado en pasos del pipeline
                        pct = min(99, int((paso_num / max(total_pasos, 1)) * 100))
                        progreso.progress(pct, text=f"Paso {paso_num}/{total_pasos} — {descripcion[:50]}")

                    # Detectar errores
                    linea_lower = linea.lower().strip()
                    if "[FIN]" in linea and "éxito" in linea_lower:
                        estado_final = "OK"
                    elif "error" in linea_lower and paso_num > 0:
                        estado_final = "ERROR"
                        if pasos_lista:
                            pasos_lista[-1]["error"] = True
                    elif "[TIMEOUT]" in linea:
                        estado_final = "TIMEOUT"

                    # Actualizar log técnico (desplegable)
                    with log_expander_box.container():
                        with st.expander("🔧 Log técnico", expanded=False):
                            st.code(log_acum[-3000:], language="bash")

                progreso.progress(100, text="✅ Pipeline finalizado.")

            except Exception as exc:
                estado_final = "ERROR"
                log_acum += f"\n[ERROR INESPERADO EN STREAMING] {exc}\n"

            finally:
                # Garantiza reset de estado sin importar qué ocurrió (incluso cierre de pestaña)
                st.session_state["etl_en_ejecucion"] = False
                st.session_state["etl_log"]          = log_acum
                st.session_state["etl_estado_final"] = estado_final
                st.session_state["etl_pasos_lista"]  = pasos_lista
                st.session_state["etl_fase_actual"]  = fase_actual
                st.session_state["etl_paso_num"]     = paso_num
                st.session_state["etl_total_pasos"]  = total_pasos

            st.rerun()

    # ── Resultado post-ejecución ─────────────────────────────────────────────
    estado_final_guardado = st.session_state.get("etl_estado_final")
    log_guardado          = st.session_state.get("etl_log", "")
    pasos_guardados       = st.session_state.get("etl_pasos_lista", [])
    fase_guardada         = st.session_state.get("etl_fase_actual", "config")
    paso_guardado         = st.session_state.get("etl_paso_num", 0)
    total_guardado        = st.session_state.get("etl_total_pasos", 22)

    if estado_final_guardado:
        st.markdown("---")
        if estado_final_guardado == "OK":
            st.success("✅ Pipeline completado exitosamente.", icon="🎉")
            st.balloons()
        elif estado_final_guardado == "ERROR":
            st.error("❌ El pipeline terminó con errores. Revisa el log.", icon="🚨")
        else:
            banner_aviso(f"Pipeline finalizó con estado: <b>{estado_final_guardado}</b>")

        if pasos_guardados:
            st.markdown("#### Resumen de ejecución")
            col_viz, col_steps = st.columns([2, 3], gap="medium")
            with col_viz:
                st.markdown(
                    _generar_monitor_etl_html(fase_guardada, paso_guardado, total_guardado),
                    unsafe_allow_html=True,
                )
            with col_steps:
                st.markdown(
                    _generar_stepper_html(pasos_guardados, len(pasos_guardados)),
                    unsafe_allow_html=True,
                )

        if log_guardado:
            with st.expander("🔧 Ver log técnico crudo", expanded=False):
                st.code(log_guardado, language="bash")
            st.download_button(
                label="⬇️ Descargar log",
                data=log_guardado,
                file_name=f"log_etl_{st.session_state.get('etl_id_corrida', 'corrida')[:8]}.txt",
                mime="text/plain",
                key="btn_descargar_log",
            )
    
    st.divider()

    if not conectado or df_estado.empty:
        estado_vacio_html(
            "📋", "Sin corridas recientes",
            "No se encontraron corridas ETL. Ejecuta el pipeline para ver el historial aquí.",
        )
    else:
        seccion_tabla_con_guardar(
            df_estado,
            key="inicio_estado",
            titulo="📋 Historial de Corridas (v3 API)",
            page_size=10,
            caption="Última actualización reciente.",
            mostrar_boton_guardar=False,
        )
