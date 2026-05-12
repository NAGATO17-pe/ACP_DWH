const { useState } = React;

const NAV_ANALYST = [
  { id:'dashboard', label:'Dashboard', icon:'home' },
  { id:'geografia', label:'Geografía & Variedades', icon:'map' },
  { id:'homologacion', label:'Homologación', icon:'shuffle' },
  { id:'pipeline', label:'Config. Pipeline', icon:'git' },
  { id:'etl', label:'Auditoría ETL', icon:'file' },
  { id:'reglas', label:'Reglas & Restricciones', icon:'shield' },
  { id:'personal', label:'Auditoría Personal', icon:'users' },
  { id:'ia', label:'Modelos IA', icon:'cpu' },
  null,
  { id:'salud', label:'Salud del Sistema', icon:'activity' },
];
const NAV_EXEC = [
  { id:'executive', label:'Resumen Ejecutivo', icon:'star' },
  { id:'ia', label:'Modelos IA', icon:'cpu' },
  { id:'geografia', label:'Geografía', icon:'map' },
  null,
  { id:'salud', label:'Salud del Sistema', icon:'activity' },
];

const Card = ({ children, style, p='20px', className, onClick }) => {
  const t = useTheme();
  return (
    <div className={className} onClick={onClick} style={{
      background:t.card, border:`1px solid ${t.cardBorder}`,
      backdropFilter:t.blur, WebkitBackdropFilter:t.blur,
      borderRadius:14, boxShadow:t.shadow, padding:p,
      cursor: onClick ? 'pointer' : undefined, ...style,
    }}>{children}</div>
  );
};

const Badge = ({ status }) => {
  const t = useTheme();
  const map = {
    ok:{bg:t.okLight,color:t.ok,label:'OK'},
    warning:{bg:t.warnLight,color:t.warn,label:'Warning'},
    error:{bg:t.errLight,color:t.err,label:'Error'},
    pendiente:{bg:t.warnLight,color:t.warn,label:'Pendiente'},
    aprobado:{bg:t.okLight,color:t.ok,label:'Aprobado'},
    revisando:{bg:t.accentLight,color:t.accentText,label:'Revisando'},
    activo:{bg:t.okLight,color:t.ok,label:'Activo'},
    inactivo:{bg:t.errLight,color:t.err,label:'Inactivo'},
    pendiente_user:{bg:t.warnLight,color:t.warn,label:'Pendiente'},
  };
  const s = map[status]||map.pendiente;
  return (
    <span style={{display:'inline-flex',alignItems:'center',gap:5,padding:'3px 10px',
      borderRadius:20,fontSize:11,fontWeight:600,background:s.bg,color:s.color,whiteSpace:'nowrap'}}>
      <span style={{width:6,height:6,borderRadius:'50%',background:s.color,
        animation:(status==='ok'||status==='activo')?'pulse 2.5s ease infinite':undefined}}/>
      {s.label}
    </span>
  );
};

const StatusDot = ({ status }) => {
  const t = useTheme();
  const c = status==='ok'?t.ok:status==='warning'?t.warn:t.err;
  return <span style={{display:'inline-block',width:8,height:8,borderRadius:'50%',background:c,
    animation:status==='ok'?'pulse 2.5s ease infinite':undefined,flexShrink:0}}/>;
};

const SectionHeader = ({ title, subtitle, action }) => {
  const t = useTheme();
  return (
    <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:24}}>
      <div>
        <h2 style={{fontSize:20,fontWeight:700,color:t.text,letterSpacing:'-0.3px'}}>{title}</h2>
        {subtitle && <p style={{fontSize:13,color:t.textMuted,marginTop:4}}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
};

const Btn = ({ children, onClick, variant='primary', size='md', icon, style, disabled }) => {
  const t = useTheme();
  const [hov, setHov] = useState(false);
  const pad = size==='sm'?'6px 14px':'9px 20px';
  const fs = size==='sm'?12:13;
  const base = variant==='primary'
    ? {background:hov?t.accentHov:t.btnPrimary,color:t.btnPrimaryText,border:'none'}
    : {background:hov?t.accentLight:'transparent',color:t.accentText,border:`1px solid ${t.divider}`};
  return (
    <button onClick={(e) => {
          if (onClick) onClick(e);
          else if (window.showToast) window.showToast(typeof children === 'string' ? `Función "${children}" en desarrollo` : 'Función en desarrollo', 'info');
        }} disabled={disabled}
      onMouseEnter={()=>setHov(true)} onMouseLeave={()=>setHov(false)}
      style={{display:'inline-flex',alignItems:'center',gap:6,padding:pad,borderRadius:8,
        fontSize:fs,fontWeight:600,cursor:disabled?'default':'pointer',transition:'all .18s',...base,...style}}>
      {icon && <Icon name={icon} size={14} color={variant==='primary'?t.btnPrimaryText:t.accentText}/>}
      {children}
    </button>
  );
};

// ── Filter Bar ─────────────────────────────────────────────
const FilterBar = ({ config }) => {
  const t = useTheme();
  const { filters, setFilter, resetFilters, activeCount } = useFilters();

  const selStyle = (active) => ({
    padding:'5px 12px', borderRadius:8, border:`1.5px solid ${active?t.accent:t.divider}`,
    background: active?t.accentLight:'transparent', color:active?t.accentText:t.textMuted,
    fontSize:12, fontWeight:600, cursor:'pointer', transition:'all .15s', whiteSpace:'nowrap',
  });

  return (
    <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:16,flexWrap:'wrap'}}>
      {/* Search */}
      {config.search && (
        <div style={{display:'flex',alignItems:'center',gap:7,background:t.card,
          border:`1px solid ${t.cardBorder}`,borderRadius:8,padding:'5px 10px',
          backdropFilter:t.blur,WebkitBackdropFilter:t.blur,minWidth:200}}>
          <Icon name="search" size={13} color={t.textMuted}/>
          <input value={filters.q} onChange={e=>setFilter('q',e.target.value)}
            placeholder={config.searchPlaceholder||'Buscar...'}
            style={{border:'none',background:'transparent',outline:'none',fontSize:12,color:t.text,width:'100%'}}/>
          {filters.q && (
            <button onClick={()=>setFilter('q','')} style={{border:'none',background:'transparent',cursor:'pointer',display:'flex',padding:0}}>
              <Icon name="x" size={12} color={t.textMuted}/>
            </button>
          )}
        </div>
      )}

      {/* Fundo */}
      {config.fundo && (
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:11,color:t.textMuted,fontWeight:600}}>Fundo:</span>
          <div style={{display:'flex',gap:3}}>
            {[{id:'todos',label:'Todos'},...MOCK.fundos.map(f=>({id:f.id,label:f.name}))].map(op=>(
              <button key={op.id} onClick={()=>setFilter('fundo',op.id)} style={selStyle(filters.fundo===op.id)}>{op.label}</button>
            ))}
          </div>
        </div>
      )}

      {/* Estado */}
      {config.estado && (
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:11,color:t.textMuted,fontWeight:600}}>Estado:</span>
          <div style={{display:'flex',gap:3}}>
            {(config.estadoOpts||['todos','ok','warning','error']).map(op=>(
              <button key={op} onClick={()=>setFilter('estado',op)} style={selStyle(filters.estado===op)}>
                {op==='todos'?'Todos':op.charAt(0).toUpperCase()+op.slice(1)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tabla */}
      {config.tabla && (
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:11,color:t.textMuted,fontWeight:600}}>Tabla:</span>
          <select value={filters.tabla} onChange={e=>setFilter('tabla',e.target.value)}
            style={{padding:'5px 10px',borderRadius:8,border:`1.5px solid ${t.divider}`,
              background:t.card,color:t.text,fontSize:12,fontWeight:600,cursor:'pointer',
              backdropFilter:t.blur,outline:'none'}}>
            {['todas','cosecha_diaria','calibres','variedades','geografia'].map(op=>(
              <option key={op} value={op}>{op==='todas'?'Todas las tablas':op}</option>
            ))}
          </select>
        </div>
      )}

      {/* Tipo (homologacion) */}
      {config.tipo && (
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:11,color:t.textMuted,fontWeight:600}}>Tipo:</span>
          <div style={{display:'flex',gap:3}}>
            {['todos','Variedad','Fundo','Personal'].map(op=>(
              <button key={op} onClick={()=>setFilter('tipo',op)} style={selStyle(filters.tipo===op)}>
                {op==='todos'?'Todos':op}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Rol (personal) */}
      {config.rol && (
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:11,color:t.textMuted,fontWeight:600}}>Rol:</span>
          <select value={filters.rol} onChange={e=>setFilter('rol',e.target.value)}
            style={{padding:'5px 10px',borderRadius:8,border:`1.5px solid ${t.divider}`,
              background:t.card,color:t.text,fontSize:12,fontWeight:600,cursor:'pointer',outline:'none'}}>
            {['todos','Data Scientist','Data Analyst','Data Engineer','Gerente TI'].map(op=>(
              <option key={op} value={op}>{op==='todos'?'Todos los roles':op}</option>
            ))}
          </select>
        </div>
      )}

      {/* Clear */}
      {activeCount > 0 && (
        <button onClick={resetFilters}
          style={{display:'flex',alignItems:'center',gap:5,padding:'5px 12px',borderRadius:8,
            border:`1px solid ${t.err}44`,background:t.errLight,color:t.err,
            fontSize:11,fontWeight:600,cursor:'pointer'}}>
          <Icon name="x" size={12} color={t.err}/>
          Limpiar ({activeCount})
        </button>
      )}

      {/* Count */}
      {config.resultCount !== undefined && (
        <span style={{fontSize:11,color:t.textMuted,marginLeft:'auto'}}>
          {config.resultCount} resultado{config.resultCount!==1?'s':''}
        </span>
      )}
    </div>
  );
};

const Sidebar = ({ active, setActive, collapsed, setCollapsed, portalMode }) => {
  const t = useTheme();
  const NAV = portalMode==='executive' ? NAV_EXEC : NAV_ANALYST;
  return (
    <div style={{width:collapsed?64:240,flexShrink:0,height:'100vh',display:'flex',flexDirection:'column',
      background:t.sidebar,borderRight:`1px solid ${t.sidebarBorder}`,
      backdropFilter:t.blur,WebkitBackdropFilter:t.blur,transition:'width .25s cubic-bezier(.4,0,.2,1)',zIndex:10}}>
      <div style={{padding:collapsed?'20px 16px':'20px 20px',display:'flex',alignItems:'center',
        gap:10,borderBottom:`1px solid ${t.divider}`,cursor:'pointer',flexShrink:0}}
        onClick={()=>setCollapsed(!collapsed)}>
        <div style={{width:32,height:32,borderRadius:8,background:`linear-gradient(135deg, ${t.accent}, ${t.accentHov})`,
          display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
          <Icon name="layers" size={16} color="#fff" sw={2}/>
        </div>
        {!collapsed && (
          <div style={{overflow:'hidden'}}>
            <div style={{fontSize:13,fontWeight:800,color:t.text,letterSpacing:'-0.2px',whiteSpace:'nowrap'}}>Cerro Prieto</div>
            <div style={{fontSize:10,color:t.textMuted,fontWeight:500,letterSpacing:'0.5px',textTransform:'uppercase'}}>
              {portalMode==='executive'?'Portal Ejecutivo':'Portal MDM'}
            </div>
          </div>
        )}
      </div>
      <nav style={{flex:1,overflowY:'auto',padding:'10px 0'}}>
        {NAV.map((item,i) => {
          if (!item) return <div key={i} style={{height:1,background:t.divider,margin:'8px 12px'}}/>;
          const isActive = active===item.id;
          return (
            <button key={item.id} onClick={()=>setActive(item.id)}
              title={collapsed?item.label:undefined}
              style={{width:'100%',display:'flex',alignItems:'center',gap:10,
                padding:collapsed?'10px 20px':'10px 16px 10px 16px',
                background:isActive?t.navActive:'transparent',border:'none',
                borderLeft:`3px solid ${isActive?t.navActiveBorder:'transparent'}`,
                cursor:'pointer',transition:'all .15s',textAlign:'left',
                borderRadius:collapsed?0:'0 8px 8px 0'}}>
              <Icon name={item.icon} size={17} color={isActive?t.accent:t.textMuted} sw={isActive?2.2:1.8}/>
              {!collapsed && (
                <span style={{fontSize:13,fontWeight:isActive?600:500,
                  color:isActive?t.accentText:t.textMuted,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>
                  {item.label}
                </span>
              )}
            </button>
          );
        })}
      </nav>
      <div style={{padding:'12px 16px',borderTop:`1px solid ${t.divider}`,
        display:'flex',alignItems:'center',gap:10,flexShrink:0}}>
        <div style={{width:32,height:32,borderRadius:'50%',background:t.accentLight,
          display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,
          fontSize:11,fontWeight:700,color:t.accentText}}>
          {MOCK.user.initials}
        </div>
        {!collapsed && (
          <div style={{flex:1,minWidth:0}}>
            <div style={{fontSize:12,fontWeight:600,color:t.text,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{MOCK.user.name}</div>
            <div style={{fontSize:11,color:t.textMuted}}>{MOCK.user.role}</div>
          </div>
        )}
      </div>
    </div>
  );
};

const TopBar = ({ active, notifs=3, portalMode, onLogout }) => {
  const t = useTheme();
  const labels = {
    dashboard:'Dashboard',executive:'Resumen Ejecutivo',
    geografia:'Geografía & Variedades',homologacion:'Homologación de Datos',
    pipeline:'Configuración de Pipeline',etl:'Auditoría ETL',
    reglas:'Reglas & Restricciones',personal:'Auditoría de Personal',
    ia:'Modelos de IA',salud:'Salud del Sistema',
  };
  const portalBadge = portalMode==='executive'
    ? {label:'Portal Ejecutivo',color:t.warn,bg:t.warnLight}
    : {label:'Portal Analista',color:t.accentText,bg:t.accentLight};
  return (
    <div style={{height:60,display:'flex',alignItems:'center',justifyContent:'space-between',
      padding:'0 24px',background:t.topbar,borderBottom:`1px solid ${t.topbarBorder}`,
      backdropFilter:t.blur,WebkitBackdropFilter:t.blur,flexShrink:0,zIndex:9}}>
      <div style={{display:'flex',alignItems:'center',gap:12}}>
        <div>
          <div style={{fontSize:15,fontWeight:700,color:t.text}}>{labels[active]||'Portal MDM'}</div>
          <div style={{fontSize:11,color:t.textMuted}}>Cerro Prieto ACP · {new Date().toLocaleDateString('es-PE',{weekday:'long',day:'numeric',month:'long',year:'numeric'})}</div>
        </div>
        <span style={{padding:'3px 10px',borderRadius:20,fontSize:10,fontWeight:700,
          background:portalBadge.bg,color:portalBadge.color,letterSpacing:'0.3px'}}>
          {portalBadge.label}
        </span>
      </div>
      <div style={{display:'flex',alignItems:'center',gap:12}}>
        <div style={{display:'flex',alignItems:'center',gap:8,background:t.card,
          border:`1px solid ${t.cardBorder}`,borderRadius:8,padding:'6px 12px'}}>
          <Icon name="search" size={14} color={t.textMuted}/>
          <input placeholder="Buscar..." style={{border:'none',background:'transparent',outline:'none',fontSize:12,color:t.text,width:140}}/>
        </div>
        <div style={{position:'relative',cursor:'pointer'}}>
          <Icon name="bell" size={18} color={t.textMuted}/>
          {notifs>0 && <span style={{position:'absolute',top:-4,right:-4,width:14,height:14,
            borderRadius:'50%',background:t.err,color:'#fff',fontSize:8,fontWeight:700,
            display:'flex',alignItems:'center',justifyContent:'center'}}>{notifs}</span>}
        </div>
        <div style={{width:1,height:24,background:t.divider}}/>
        <button onClick={onLogout} style={{display:'flex',alignItems:'center',gap:5,
          padding:'4px 8px',borderRadius:6,border:'none',background:'transparent',
          cursor:'pointer',fontSize:11,color:t.textMuted}}>
          <Icon name="logout" size={13} color={t.textMuted}/>
          Salir
        </button>
      </div>
    </div>
  );
};

Object.assign(window, { Card, Badge, StatusDot, SectionHeader, Btn, FilterBar, Sidebar, TopBar });
