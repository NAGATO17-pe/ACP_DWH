const { useState, useEffect } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "verdeGlass",
  "portalMode": "analyst",
  "sidebarCollapsed": false
}/*EDITMODE-END*/;

const SCREENS_ANALYST = {
  dashboard: Dashboard, geografia: Geografia, homologacion: Homologacion,
  pipeline: Pipeline, etl: ETLAudit, reglas: Reglas,
  personal: Personal, ia: ModelosIA, salud: Salud,
};
const SCREENS_EXEC = {
  executive: ExecutivePortal, ia: ModelosIA, geografia: Geografia, salud: Salud,
};

// ── CP Logo ────────────────────────────────────────────────
const CPLogo = ({ scale=1, dark=false }) => {
  const textColor = dark ? '#ffffff' : '#1a2e1e';
  const sepColor  = dark ? 'rgba(255,255,255,0.25)' : '#c8d4c8';
  const rays = [
    {angle:-54,len:17,color:'#1a8c38',w:3.2},{angle:-36,len:19,color:'#4cb828',w:3.2},
    {angle:-18,len:21,color:'#8cc820',w:3.2},{angle:0,len:22,color:'#f5d00a',w:3.2},
    {angle:18,len:21,color:'#f5a020',w:3.2},{angle:36,len:19,color:'#f07020',w:3.2},
    {angle:54,len:17,color:'#e84818',w:3.2},
  ];
  return (
    <svg width={200*scale} height={52*scale} viewBox="0 0 200 52">
      <g transform="translate(26,46)">
        {rays.map((r,i) => {
          const rad=(r.angle-90)*Math.PI/180;
          return <line key={i} x1={0} y1={0} x2={(Math.cos(rad)*r.len).toFixed(2)} y2={(Math.sin(rad)*r.len).toFixed(2)}
            stroke={r.color} strokeWidth={r.w} strokeLinecap="round"/>;
        })}
      </g>
      <text x={55} y={40} fontSize={32} fontWeight="800" fill={textColor}
        fontFamily="Plus Jakarta Sans,sans-serif" letterSpacing="-1">CP</text>
      <line x1={104} y1={9} x2={104} y2={44} stroke={sepColor} strokeWidth={1.2}/>
      <text x={113} y={26} fontSize={13} fontWeight="700" fill={textColor}
        fontFamily="Plus Jakarta Sans,sans-serif" letterSpacing="0.8">CERRO</text>
      <text x={113} y={42} fontSize={13} fontWeight="700" fill={textColor}
        fontFamily="Plus Jakarta Sans,sans-serif" letterSpacing="0.8">PRIETO</text>
    </svg>
  );
};

// ── Login Screen ───────────────────────────────────────────
const LoginScreen = ({ onLogin, theme: t }) => {
  const [user,setUser]=useState('');
  const [pass,setPass]=useState('');
  const [showPass,setShowPass]=useState(false);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const [focusUser,setFocusUser]=useState(false);
  const [focusPass,setFocusPass]=useState(false);

  const handleLogin = e => {
    e.preventDefault();
    if(!user||!pass){setError('Por favor ingresa usuario y contraseña.');return;}
    setError(''); setLoading(true);
    setTimeout(() => { setLoading(false); onLogin(); if (window.showToast) window.showToast('Sesión iniciada correctamente', 'success'); }, 1200);
  };

  const inp = focused => ({
    width:'100%',padding:'12px 14px 12px 42px',
    border:`1.5px solid ${focused?t.accent:t.cardBorder}`,borderRadius:10,
    background:focused?t.accentLight+'44':t.card,color:t.text,fontSize:14,outline:'none',
    backdropFilter:t.blur,WebkitBackdropFilter:t.blur,transition:'border-color .18s,background .18s',
    boxShadow:focused?`0 0 0 3px ${t.accent}18`:'none',
  });

  return (
    <div style={{position:'fixed',inset:0,display:'flex',alignItems:'center',justifyContent:'center',
      background:t.bodyBg,overflow:'hidden'}}>
      <div style={{position:'fixed',inset:0,backgroundImage:t.orbs,pointerEvents:'none'}}/>
      <div style={{position:'fixed',top:'-20%',right:'-15%',width:600,height:600,borderRadius:'50%',
        background:`radial-gradient(circle, ${t.accent}08 0%, transparent 70%)`,pointerEvents:'none'}}/>
      <div style={{position:'fixed',bottom:'-15%',left:'-10%',width:500,height:500,borderRadius:'50%',
        background:`radial-gradient(circle, ${t.accent}06 0%, transparent 70%)`,pointerEvents:'none'}}/>
      <div className="fade-in" style={{width:420,position:'relative',zIndex:1}}>
        <div style={{background:t.card,border:`1px solid ${t.cardBorder}`,
          backdropFilter:t.blur,WebkitBackdropFilter:t.blur,
          borderRadius:20,boxShadow:t.shadowHov,padding:'44px 40px 36px'}}>
          <div style={{display:'flex',justifyContent:'center',marginBottom:32}}>
            <CPLogo scale={1} dark={t.id==='ejecutivoDark'}/>
          </div>
          <div style={{textAlign:'center',marginBottom:28}}>
            <h1 style={{fontSize:22,fontWeight:800,color:t.text,letterSpacing:'-0.4px',marginBottom:6}}>Bienvenido al Portal MDM</h1>
            <p style={{fontSize:13,color:t.textMuted}}>Accede con tus credenciales corporativas</p>
          </div>
          <form onSubmit={handleLogin}>
            <div style={{position:'relative',marginBottom:14}}>
              <div style={{position:'absolute',left:13,top:'50%',transform:'translateY(-50%)',pointerEvents:'none'}}>
                <Icon name="users" size={16} color={focusUser?t.accent:t.textLight} sw={2}/>
              </div>
              <input type="text" placeholder="Usuario corporativo" value={user}
                onChange={e=>setUser(e.target.value)} onFocus={()=>setFocusUser(true)} onBlur={()=>setFocusUser(false)}
                style={inp(focusUser)} autoComplete="username"/>
            </div>
            <div style={{position:'relative',marginBottom:22}}>
              <div style={{position:'absolute',left:13,top:'50%',transform:'translateY(-50%)',pointerEvents:'none'}}>
                <Icon name="shield" size={16} color={focusPass?t.accent:t.textLight} sw={2}/>
              </div>
              <input type={showPass?'text':'password'} placeholder="Contraseña" value={pass}
                onChange={e=>setPass(e.target.value)} onFocus={()=>setFocusPass(true)} onBlur={()=>setFocusPass(false)}
                style={inp(focusPass)} autoComplete="current-password"/>
              <button type="button" onClick={()=>setShowPass(!showPass)}
                style={{position:'absolute',right:12,top:'50%',transform:'translateY(-50%)',
                  border:'none',background:'transparent',cursor:'pointer',padding:0,display:'flex'}}>
                <Icon name="eye" size={15} color={t.textLight}/>
              </button>
            </div>
            {error&&(
              <div style={{display:'flex',alignItems:'center',gap:7,padding:'8px 12px',
                background:t.errLight,borderRadius:8,marginBottom:14,fontSize:12,color:t.err}}>
                <Icon name="alertC" size={14} color={t.err} sw={2}/>{error}
              </div>
            )}
            <button type="submit" disabled={loading}
              style={{width:'100%',padding:'13px',borderRadius:10,border:'none',
                background:loading?t.accentLight:t.btnPrimary,
                color:loading?t.accentText:t.btnPrimaryText,
                fontSize:14,fontWeight:700,cursor:loading?'default':'pointer',
                transition:'all .18s',display:'flex',alignItems:'center',justifyContent:'center',gap:8,
                boxShadow:loading?'none':`0 4px 16px ${t.accent}40`}}>
              {loading?(<>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={t.accentText}
                  strokeWidth="2.5" strokeLinecap="round" style={{animation:'spin .8s linear infinite'}}>
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
                </svg>Autenticando...
              </>):(<><Icon name="zap" size={15} color={t.btnPrimaryText} sw={2.2}/>Iniciar sesión</>)}
            </button>
          </form>
          <div style={{marginTop:20,padding:'10px 14px',background:t.accentLight,borderRadius:8,textAlign:'center'}}>
            <span style={{fontSize:11,color:t.textMuted}}>Demo: cualquier usuario y contraseña · </span>
            <button onClick={()=>{setUser('cmendoza');setPass('Acp2026!');}}
              style={{fontSize:11,color:t.accentText,fontWeight:600,border:'none',background:'transparent',cursor:'pointer',textDecoration:'underline'}}>
              autocompletar
            </button>
          </div>
        </div>
        <div style={{textAlign:'center',marginTop:20,fontSize:11,color:t.textMuted}}>
          Cerro Prieto ACP · Portal MDM v2.2 · 2026
        </div>
      </div>
    </div>
  );
};

// ── Tweaks Panel ───────────────────────────────────────────
const TweaksPanel = ({ tweaks, setTweaks, visible }) => {
  const t = useTheme();
  if (!visible) return null;
  const set = (key,val) => {
    const next={...tweaks,[key]:val};
    setTweaks(next);
    window.parent.postMessage({type:'__edit_mode_set_keys',edits:next},'*');
  };
  const Row = ({label,children}) => (
    <div style={{marginBottom:14}}>
      <div style={{fontSize:10,fontWeight:700,color:t.textMuted,textTransform:'uppercase',letterSpacing:'0.7px',marginBottom:7}}>{label}</div>
      {children}
    </div>
  );
  return (
    <div style={{position:'fixed',bottom:20,right:20,width:230,zIndex:1000,
      background:t.topbar,border:`1px solid ${t.cardBorder}`,
      backdropFilter:t.blur,WebkitBackdropFilter:t.blur,
      borderRadius:14,boxShadow:t.shadowHov,padding:'16px 16px 12px'}}>
      <div style={{fontSize:12,fontWeight:700,color:t.text,marginBottom:14,display:'flex',alignItems:'center',gap:6}}>
        <Icon name="settings" size={13} color={t.accent} sw={2.2}/>Tweaks
      </div>
      <Row label="Tema">
        {Object.values(THEMES).map(th=>(
          <button key={th.id} onClick={()=>set('theme',th.id)}
            style={{width:'100%',marginBottom:5,padding:'6px 10px',borderRadius:8,
              border:`1.5px solid ${tweaks.theme===th.id?t.accent:t.divider}`,
              background:tweaks.theme===th.id?t.accentLight:'transparent',
              color:tweaks.theme===th.id?t.accentText:t.textMuted,
              fontSize:11,fontWeight:600,cursor:'pointer',textAlign:'left',
              display:'flex',alignItems:'center',gap:7,transition:'all .15s'}}>
            <span style={{width:9,height:9,borderRadius:'50%',background:th.accent,display:'inline-block',flexShrink:0}}/>
            {th.name}
          </button>
        ))}
      </Row>
      <Row label="Portal">
        <div style={{display:'flex',gap:6}}>
          {[['analyst','Analista'],['executive','Ejecutivo']].map(([id,label])=>(
            <button key={id} onClick={()=>set('portalMode',id)}
              style={{flex:1,padding:'6px 0',borderRadius:8,
                border:`1.5px solid ${tweaks.portalMode===id?t.accent:t.divider}`,
                background:tweaks.portalMode===id?t.accentLight:'transparent',
                color:tweaks.portalMode===id?t.accentText:t.textMuted,
                fontSize:11,fontWeight:600,cursor:'pointer',transition:'all .15s'}}>{label}</button>
          ))}
        </div>
      </Row>
      <Row label="Sidebar">
        <div style={{display:'flex',gap:6}}>
          {[[false,'Expandido'],[true,'Compacto']].map(([val,label])=>(
            <button key={label} onClick={()=>set('sidebarCollapsed',val)}
              style={{flex:1,padding:'6px 0',borderRadius:8,
                border:`1.5px solid ${tweaks.sidebarCollapsed===val?t.accent:t.divider}`,
                background:tweaks.sidebarCollapsed===val?t.accentLight:'transparent',
                color:tweaks.sidebarCollapsed===val?t.accentText:t.textMuted,
                fontSize:11,fontWeight:600,cursor:'pointer',transition:'all .15s'}}>{label}</button>
          ))}
        </div>
      </Row>
    </div>
  );
};

// ── App Root ───────────────────────────────────────────────
const App = () => {
  const saved = (() => { try { return JSON.parse(localStorage.getItem('mdm_state2')||'{}'); } catch { return {}; } })();
  const [tweaks, setTweaks] = useState({...TWEAK_DEFAULTS, ...saved.tweaks});
  const [active, setActive] = useState(saved.active || 'dashboard');
  const [tweaksVis, setTweaksVis] = useState(false);
  const [loggedIn, setLoggedIn] = useState(!!saved.loggedIn);
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    window.showToast = (msg, type = 'info') => {
      const id = Date.now() + Math.random();
      setToasts(p => [...p, { id, msg, type }]);
      setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3000);
    };
    return () => { delete window.showToast; };
  }, []);

  const theme = THEMES[tweaks.theme] || THEMES.verdeGlass;
  const isExec = tweaks.portalMode === 'executive';
  const SCREENS = isExec ? SCREENS_EXEC : SCREENS_ANALYST;

  useEffect(() => {
    localStorage.setItem('mdm_state2', JSON.stringify({active,tweaks,loggedIn}));
  }, [active,tweaks,loggedIn]);

  useEffect(() => {
    const handler = e => {
      if(e.data?.type==='__activate_edit_mode') setTweaksVis(true);
      if(e.data?.type==='__deactivate_edit_mode') setTweaksVis(false);
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({type:'__edit_mode_available'},'*');
    return () => window.removeEventListener('message', handler);
  }, []);

  // Fix active screen when switching portal mode
  useEffect(() => {
    if (isExec && !SCREENS_EXEC[active]) setActive('executive');
    if (!isExec && !SCREENS_ANALYST[active]) setActive('dashboard');
  }, [tweaks.portalMode]);

  const logout = () => { setLoggedIn(false); localStorage.removeItem('mdm_state2'); };

  if (!loggedIn) {
    return (
      <ThemeCtx.Provider value={theme}>
        <LoginScreen theme={theme} onLogin={()=>setLoggedIn(true)}/>
      </ThemeCtx.Provider>
    );
  }

  const Screen = SCREENS[active] || (isExec ? ExecutivePortal : Dashboard);

  return (
    <ThemeCtx.Provider value={theme}>
      <FiltersProvider>
        <div style={{position:'fixed',inset:0,background:theme.bodyBg,zIndex:-2}}/>
        <div style={{position:'fixed',inset:0,backgroundImage:theme.orbs,zIndex:-1,pointerEvents:'none'}}/>
        <div style={{display:'flex',height:'100vh',overflow:'hidden'}}>
          <Sidebar active={active} setActive={setActive}
            collapsed={tweaks.sidebarCollapsed} portalMode={tweaks.portalMode}
            setCollapsed={v=>{const n={...tweaks,sidebarCollapsed:v};setTweaks(n);window.parent.postMessage({type:'__edit_mode_set_keys',edits:n},'*');}}/>
          <div style={{flex:1,display:'flex',flexDirection:'column',minWidth:0,overflow:'hidden'}}>
            <TopBar active={active} notifs={3} portalMode={tweaks.portalMode} onLogout={logout}/>
            <main style={{flex:1,overflowY:'auto',padding:'24px',minHeight:0}}>
              <Screen key={active}/>
            </main>
          </div>
        </div>
        <TweaksPanel tweaks={tweaks} setTweaks={setTweaks} visible={tweaksVis}/>
        <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 9999, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {toasts.map(t => (
            <div key={t.id} className="slide-in" style={{
              background: t.type === 'success' ? theme.okLight : (t.type === 'error' ? theme.errLight : theme.card),
              color: t.type === 'success' ? theme.ok : (t.type === 'error' ? theme.err : theme.text),
              border: `1px solid ${t.type === 'success' ? theme.ok : (t.type === 'error' ? theme.err : theme.cardBorder)}`,
              padding: '12px 20px', borderRadius: 8, boxShadow: theme.shadow, fontWeight: 600, fontSize: 13,
              backdropFilter: theme.blur, WebkitBackdropFilter: theme.blur, minWidth: 200,
              display: 'flex', alignItems: 'center', gap: 8
            }}>
              <Icon name={t.type === 'success' ? 'checkC' : (t.type === 'error' ? 'alertC' : 'info')} size={16} />
              {t.msg}
            </div>
          ))}
        </div>
      </FiltersProvider>
    </ThemeCtx.Provider>
  );
};

function mountApp() {
  const el = document.getElementById('root');
  if (!el) { setTimeout(mountApp, 20); return; }
  ReactDOM.createRoot(el).render(<App/>);
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountApp);
} else {
  mountApp();
}
