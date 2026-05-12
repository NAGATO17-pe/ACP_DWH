const { useState } = React;

/* ─────────────────── GEOGRAFÍA ─────────────────── */
const Geografia = () => {
  const t = useTheme();
  const [openFundo, setOpenFundo] = useState('f1');
  const [openSector, setOpenSector] = useState(null);
  const [selected, setSelected] = useState({ type:'fundo', id:'f1' });
  const selFundo = MOCK.fundos.find(f => selected.type==='fundo' && f.id===selected.id);
  const selSector = MOCK.fundos.flatMap(f=>f.sectores).find(s => selected.type==='sector' && s.id===selected.id);
  return (
    <div className="fade-in">
      <SectionHeader title="Geografía & Variedades"
        subtitle="Jerarquía: Fundo → Sector → Módulo → Turno → Válvula → Cama"
        action={<Btn icon="plus" size="sm">Agregar Fundo</Btn>}/>
      <div style={{display:'grid',gridTemplateColumns:'280px 1fr',gap:16,height:'calc(100vh - 190px)'}}>
        <Card p="0" style={{overflowY:'auto'}}>
          <div style={{padding:'12px 16px',borderBottom:`1px solid ${t.divider}`,fontSize:11,
            fontWeight:700,color:t.textMuted,letterSpacing:'0.8px',textTransform:'uppercase'}}>
            Estructura Geográfica
          </div>
          {MOCK.fundos.map(fundo => {
            const fundoOpen = openFundo===fundo.id;
            const isSel = selected.type==='fundo' && selected.id===fundo.id;
            return (
              <div key={fundo.id}>
                <div onClick={()=>{setOpenFundo(fundoOpen?null:fundo.id);setSelected({type:'fundo',id:fundo.id});}}
                  style={{display:'flex',alignItems:'center',gap:8,padding:'10px 14px',
                    background:isSel?t.navActive:'transparent',borderLeft:`3px solid ${isSel?t.accent:'transparent'}`,
                    cursor:'pointer',transition:'background .15s'}}>
                  <Icon name={fundoOpen?'chevD':'chevR'} size={13} color={t.textMuted}/>
                  <Icon name="map" size={14} color={isSel?t.accent:t.textMuted} sw={2}/>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontSize:12,fontWeight:600,color:isSel?t.accentText:t.text,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{fundo.name}</div>
                    <div style={{fontSize:10,color:t.textMuted}}>{fundo.region} · {fundo.ha} ha</div>
                  </div>
                  <StatusDot status={fundo.active?'ok':'error'}/>
                </div>
                {fundoOpen && fundo.sectores.map(sec => {
                  const isSecSel = selected.type==='sector' && selected.id===sec.id;
                  const secOpen = openSector===sec.id;
                  return (
                    <div key={sec.id}>
                      <div onClick={()=>{setOpenSector(secOpen?null:sec.id);setSelected({type:'sector',id:sec.id});}}
                        style={{display:'flex',alignItems:'center',gap:8,padding:'8px 14px 8px 34px',
                          background:isSecSel?t.navActive:'transparent',borderLeft:`3px solid ${isSecSel?t.accent:'transparent'}`,
                          cursor:'pointer',transition:'background .15s'}}>
                        <Icon name={secOpen?'chevD':'chevR'} size={11} color={t.textLight}/>
                        <div style={{flex:1,minWidth:0}}>
                          <div style={{fontSize:11,fontWeight:600,color:isSecSel?t.accentText:t.textMuted}}>{sec.name}</div>
                          <div style={{fontSize:10,color:t.textLight}}>{sec.variedad} · {sec.camas} camas</div>
                        </div>
                      </div>
                      {secOpen && (
                        <div style={{paddingLeft:52,paddingBottom:4}}>
                          {['Módulos','Turnos','Válvulas','Camas'].map((l,i)=>(
                            <div key={l} style={{display:'flex',justifyContent:'space-between',padding:'5px 14px 5px 0',
                              borderBottom:`1px solid ${t.divider}`,fontSize:10,color:t.textMuted}}>
                              <span>{l}</span>
                              <span style={{fontWeight:700,color:t.text,fontFamily:"'DM Mono',monospace"}}>
                                {[sec.modulos,sec.turnos,sec.valvulas,sec.camas][i]}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </Card>
        <div style={{display:'flex',flexDirection:'column',gap:14,overflowY:'auto'}}>
          {selFundo && (
            <>
              <Card>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:16}}>
                  <div>
                    <div style={{display:'flex',alignItems:'center',gap:10}}>
                      <h3 style={{fontSize:18,fontWeight:800,color:t.text}}>Fundo {selFundo.name}</h3>
                      <Badge status={selFundo.active?'activo':'inactivo'}/>
                    </div>
                    <p style={{fontSize:12,color:t.textMuted,marginTop:3}}>{selFundo.region} · {selFundo.ha} ha totales</p>
                  </div>
                  <Btn size="sm" variant="secondary" icon="edit">Editar</Btn>
                </div>
                <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12}}>
                  {[{l:'Sectores',v:selFundo.sectores.length},{l:'Total camas',v:selFundo.camas.toLocaleString()},{l:'Hectáreas',v:`${selFundo.ha} ha`},{l:'Variedades',v:selFundo.variedades.length}].map(s=>(
                    <div key={s.l} style={{background:t.accentLight,borderRadius:10,padding:'12px 14px'}}>
                      <div style={{fontSize:20,fontWeight:800,color:t.text}}>{s.v}</div>
                      <div style={{fontSize:11,color:t.textMuted,marginTop:2}}>{s.l}</div>
                    </div>
                  ))}
                </div>
                <div style={{marginTop:14,display:'flex',gap:8,flexWrap:'wrap'}}>
                  {selFundo.variedades.map(v=>(
                    <span key={v} style={{padding:'4px 12px',borderRadius:20,fontSize:11,fontWeight:600,background:t.tag,color:t.tagText}}>{v}</span>
                  ))}
                </div>
              </Card>
              <Card>
                <div style={{fontSize:13,fontWeight:700,color:t.text,marginBottom:14}}>Sectores del Fundo</div>
                <table style={{width:'100%',borderCollapse:'collapse'}}>
                  <thead>
                    <tr style={{borderBottom:`2px solid ${t.divider}`}}>
                      {['Sector','Variedad','Módulos','Turnos','Válvulas','Camas','Hectáreas'].map(h=>(
                        <th key={h} style={{padding:'6px 10px',textAlign:'left',fontSize:11,color:t.textMuted,fontWeight:600}}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {selFundo.sectores.map(s=>(
                      <tr key={s.id} onClick={()=>{setSelected({type:'sector',id:s.id});setOpenSector(s.id);}}
                        style={{borderBottom:`1px solid ${t.divider}`,cursor:'pointer',transition:'background .12s'}}
                        onMouseEnter={e=>e.currentTarget.style.background=t.rowHov}
                        onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                        {[s.name,s.variedad,s.modulos,s.turnos,s.valvulas,s.camas.toLocaleString(),`${s.ha} ha`].map((v,i)=>(
                          <td key={i} style={{padding:'9px 10px',fontSize:12,color:i===0?t.accentText:t.text,
                            fontWeight:i===0?600:400,fontFamily:i>1?"'DM Mono',monospace":'inherit'}}>{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </>
          )}
          {selSector && (
            <Card>
              <div style={{display:'flex',justifyContent:'space-between',marginBottom:14}}>
                <div>
                  <h3 style={{fontSize:16,fontWeight:700,color:t.text}}>{selSector.name}</h3>
                  <p style={{fontSize:12,color:t.textMuted}}>Variedad: <strong>{selSector.variedad}</strong></p>
                </div>
                <Btn size="sm" variant="secondary" icon="edit">Editar</Btn>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:10}}>
                {[['Módulos',selSector.modulos],['Turnos',selSector.turnos],['Válvulas',selSector.valvulas],['Camas',selSector.camas],['Hectáreas',`${selSector.ha} ha`]].map(([l,v])=>(
                  <div key={l} style={{background:t.accentLight,borderRadius:8,padding:'10px 12px'}}>
                    <div style={{fontSize:18,fontWeight:800,color:t.text}}>{v}</div>
                    <div style={{fontSize:10,color:t.textMuted}}>{l}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─────────────────── HOMOLOGACIÓN ─────────────────── */
const Homologacion = () => {
  const t = useTheme();
  const { filters } = useFilters();
  const [items, setItems] = useState(MOCK.duplicates);
  const action = (id, newEstado) => {
    setItems(prev => prev.map(d => d.id===id?{...d,estado:newEstado}:d));
    if (window.showToast) window.showToast(`Estado actualizado a ${newEstado}`, 'success');
  };

  const filtered = items.filter(d => {
    if (filters.tipo!=='todos' && d.tipo!==filters.tipo) return false;
    if (filters.estado!=='todos' && d.estado!==filters.estado) return false;
    if (filters.q && !`${d.v1} ${d.v2} ${d.tipo} ${d.campo}`.toLowerCase().includes(filters.q.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="fade-in">
      <SectionHeader title="Homologación de Datos"
        subtitle="Detección y resolución de duplicados en tablas maestras"
        action={<div style={{display:'flex',gap:8}}>
          <Btn size="sm" variant="secondary" icon="refresh">Re-escanear</Btn>
          <Btn size="sm" icon="download">Exportar</Btn>
        </div>}/>
      <div style={{display:'flex',gap:12,marginBottom:16}}>
        {[
          {l:'Pendientes',v:items.filter(d=>d.estado==='pendiente').length,c:t.warn,bg:t.warnLight},
          {l:'Revisando',v:items.filter(d=>d.estado==='revisando').length,c:t.accentText,bg:t.accentLight},
          {l:'Aprobados',v:items.filter(d=>d.estado==='aprobado').length,c:t.ok,bg:t.okLight},
          {l:'Total',v:items.length,c:t.text,bg:t.card},
        ].map(s=>(
          <Card key={s.l} p="12px 16px" style={{flex:1}}>
            <div style={{fontSize:22,fontWeight:800,color:s.c}}>{s.v}</div>
            <div style={{fontSize:11,color:t.textMuted,marginTop:2}}>{s.l}</div>
          </Card>
        ))}
      </div>
      <FilterBar config={{
        search:true, searchPlaceholder:'Buscar por valor, campo...',
        tipo:true,
        estado:true, estadoOpts:['todos','pendiente','revisando','aprobado'],
        resultCount:filtered.length,
      }}/>
      <Card p="0">
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead>
            <tr style={{borderBottom:`2px solid ${t.divider}`}}>
              {['Tipo','Campo','Valor A','Valor B','Confianza','Fuente','Estado','Acciones'].map(h=>(
                <th key={h} style={{padding:'11px 14px',textAlign:'left',fontSize:11,color:t.textMuted,fontWeight:700,background:t.card}}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length===0 && (
              <tr><td colSpan={8} style={{padding:'32px',textAlign:'center',color:t.textMuted,fontSize:13}}>
                No se encontraron registros con los filtros aplicados
              </td></tr>
            )}
            {filtered.map(d=>(
              <tr key={d.id} style={{borderBottom:`1px solid ${t.divider}`,transition:'background .12s'}}
                onMouseEnter={e=>e.currentTarget.style.background=t.rowHov}
                onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                <td style={{padding:'10px 14px'}}>
                  <span style={{padding:'3px 10px',borderRadius:20,fontSize:11,fontWeight:600,background:t.accentLight,color:t.accentText}}>{d.tipo}</span>
                </td>
                <td style={{padding:'10px 14px',fontSize:12,color:t.textMuted,fontWeight:500}}>{d.campo}</td>
                <td style={{padding:'10px 14px',fontSize:12,color:t.text,fontFamily:"'DM Mono',monospace"}}>{d.v1}</td>
                <td style={{padding:'10px 14px',fontSize:12,color:t.text,fontFamily:"'DM Mono',monospace"}}>{d.v2}</td>
                <td style={{padding:'10px 14px'}}>
                  <div style={{display:'flex',alignItems:'center',gap:6}}>
                    <div style={{width:60,height:6,background:t.divider,borderRadius:3,overflow:'hidden'}}>
                      <div style={{width:`${d.conf}%`,height:'100%',borderRadius:3,
                        background:d.conf>=95?t.ok:d.conf>=85?t.accent:t.warn}}/>
                    </div>
                    <span style={{fontSize:11,fontWeight:700,color:t.text,fontFamily:"'DM Mono',monospace"}}>{d.conf}%</span>
                  </div>
                </td>
                <td style={{padding:'10px 14px',fontSize:11,color:t.textMuted}}>{d.src}</td>
                <td style={{padding:'10px 14px'}}><Badge status={d.estado}/></td>
                <td style={{padding:'10px 14px'}}>
                  {d.estado==='pendiente'&&<div style={{display:'flex',gap:6}}>
                    <button onClick={()=>action(d.id,'aprobado')} style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.ok}`,background:t.okLight,color:t.ok,fontSize:11,fontWeight:600,cursor:'pointer'}}>Fusionar</button>
                    <button onClick={()=>action(d.id,'revisando')} style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.divider}`,background:'transparent',color:t.textMuted,fontSize:11,fontWeight:600,cursor:'pointer'}}>Revisar</button>
                  </div>}
                  {d.estado==='aprobado'&&<span style={{fontSize:11,color:t.textLight}}>✓ Resuelto</span>}
                  {d.estado==='revisando'&&<button onClick={()=>action(d.id,'aprobado')} style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.accent}`,background:t.accentLight,color:t.accentText,fontSize:11,fontWeight:600,cursor:'pointer'}}>Confirmar</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

/* ─────────────────── ETL AUDIT ─────────────────── */
const ETLAudit = () => {
  const t = useTheme();
  const { filters } = useFilters();
  const [sel, setSel] = useState(null);

  const filtered = MOCK.etlRuns.filter(r => {
    if (filters.tabla!=='todas' && r.tabla!==filters.tabla) return false;
    if (filters.estado!=='todos') {
      if (filters.estado==='ok' && r.estado!=='ok') return false;
      if (filters.estado==='warning' && r.estado!=='warning') return false;
      if (filters.estado==='error' && r.estado!=='error') return false;
    }
    if (filters.q && !r.id.toLowerCase().includes(filters.q.toLowerCase()) && !r.tabla.includes(filters.q.toLowerCase())) return false;
    return true;
  });

  const stats = {
    ok: MOCK.etlRuns.filter(r=>r.estado==='ok').length,
    warns: MOCK.etlRuns.reduce((s,r)=>s+r.warns,0),
    errs: MOCK.etlRuns.reduce((s,r)=>s+r.errs,0),
    avgRegs: Math.round(MOCK.etlRuns.reduce((s,r)=>s+r.regs,0)/MOCK.etlRuns.length),
  };

  return (
    <div className="fade-in">
      <SectionHeader title="Auditoría ETL"
        subtitle="Historial de ejecuciones y métricas del pipeline"
        action={<div style={{display:'flex',gap:8}}>
          <Btn size="sm" variant="secondary" icon="filter">Filtrar</Btn>
          <Btn size="sm" icon="refresh">Ejecutar ahora</Btn>
        </div>}/>
      <div style={{display:'flex',gap:12,marginBottom:16}}>
        {[
          {l:'Runs exitosas',v:stats.ok,c:t.ok,bg:t.okLight},
          {l:'Promedio registros',v:`${(stats.avgRegs/1e6).toFixed(2)}M`,c:t.accent,bg:t.accentLight},
          {l:'Total errores',v:stats.errs,c:t.err,bg:t.errLight},
          {l:'Total alertas',v:stats.warns,c:t.warn,bg:t.warnLight},
        ].map(s=>(
          <Card key={s.l} p="12px 16px" style={{flex:1}}>
            <div style={{fontSize:22,fontWeight:800,color:s.c}}>{s.v}</div>
            <div style={{fontSize:11,color:t.textMuted,marginTop:2}}>{s.l}</div>
          </Card>
        ))}
      </div>
      <FilterBar config={{
        search:true, searchPlaceholder:'Buscar por Run ID o tabla...',
        tabla:true,
        estado:true, estadoOpts:['todos','ok','warning','error'],
        resultCount:filtered.length,
      }}/>
      <Card p="0">
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead>
            <tr style={{borderBottom:`2px solid ${t.divider}`}}>
              {['Run ID','Fecha','Tabla','Duración','Registros','Errores','Alertas','Estado'].map(h=>(
                <th key={h} style={{padding:'11px 14px',textAlign:'left',fontSize:11,color:t.textMuted,fontWeight:700,background:t.card}}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length===0&&<tr><td colSpan={8} style={{padding:'32px',textAlign:'center',color:t.textMuted,fontSize:13}}>No hay resultados con los filtros aplicados</td></tr>}
            {filtered.map(r=>(
              <tr key={r.id} onClick={()=>setSel(sel===r.id?null:r.id)}
                style={{borderBottom:`1px solid ${t.divider}`,cursor:'pointer',
                  background:sel===r.id?t.accentLight:'transparent',transition:'background .12s'}}
                onMouseEnter={e=>{if(sel!==r.id)e.currentTarget.style.background=t.rowHov;}}
                onMouseLeave={e=>{if(sel!==r.id)e.currentTarget.style.background='transparent';}}>
                <td style={{padding:'10px 14px',fontSize:12,fontWeight:700,color:t.accentText,fontFamily:"'DM Mono',monospace"}}>{r.id}</td>
                <td style={{padding:'10px 14px',fontSize:12,color:t.text}}>{r.fecha}</td>
                <td style={{padding:'10px 14px'}}>
                  <span style={{padding:'2px 8px',borderRadius:4,fontSize:11,background:t.tag,color:t.tagText,fontFamily:"'DM Mono',monospace"}}>{r.tabla}</span>
                </td>
                <td style={{padding:'10px 14px',fontSize:12,color:t.text,fontFamily:"'DM Mono',monospace"}}>{r.dur}</td>
                <td style={{padding:'10px 14px',fontSize:12,fontWeight:600,color:t.text,fontFamily:"'DM Mono',monospace"}}>{(r.regs/1e6).toFixed(3)}M</td>
                <td style={{padding:'10px 14px'}}><span style={{color:r.errs>0?t.err:t.textLight,fontWeight:600,fontSize:12}}>{r.errs}</span></td>
                <td style={{padding:'10px 14px'}}><span style={{color:r.warns>10?t.warn:t.textMuted,fontSize:12}}>{r.warns}</span></td>
                <td style={{padding:'10px 14px'}}><Badge status={r.estado}/></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

/* ─────────────────── REGLAS ─────────────────── */
const Reglas = () => {
  const t = useTheme();
  const [rules, setRules] = useState(MOCK.reglas);
  const toggle = (id) => {
    setRules(prev=>prev.map(r=>r.id===id?{...r,activa:!r.activa}:r));
    if (window.showToast) window.showToast(`Estado de regla actualizado`, 'success');
  };
  return (
    <div className="fade-in">
      <SectionHeader title="Reglas & Restricciones"
        subtitle="Validaciones aplicadas sobre las tablas maestras del DW"
        action={<Btn size="sm" icon="plus">Nueva regla</Btn>}/>
      <div style={{display:'flex',gap:12,marginBottom:20}}>
        {[{l:'Reglas activas',v:rules.filter(r=>r.activa).length,c:t.ok},{l:'Inactivas',v:rules.filter(r=>!r.activa).length,c:t.textMuted},{l:'Violaciones',v:rules.reduce((s,r)=>s+r.violaciones,0),c:t.err}].map(s=>(
          <Card key={s.l} p="14px 18px" style={{flex:1}}>
            <div style={{fontSize:22,fontWeight:800,color:s.c}}>{s.v}</div>
            <div style={{fontSize:11,color:t.textMuted,marginTop:2}}>{s.l}</div>
          </Card>
        ))}
      </div>
      <Card p="0">
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead>
            <tr style={{borderBottom:`2px solid ${t.divider}`}}>
              {['ID','Regla','Tabla','Tipo','Violaciones','Estado','Acciones'].map(h=>(
                <th key={h} style={{padding:'11px 14px',textAlign:'left',fontSize:11,color:t.textMuted,fontWeight:700,background:t.card}}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rules.map(r=>(
              <tr key={r.id} style={{borderBottom:`1px solid ${t.divider}`,transition:'background .12s'}}
                onMouseEnter={e=>e.currentTarget.style.background=t.rowHov}
                onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                <td style={{padding:'10px 14px',fontSize:11,fontFamily:"'DM Mono',monospace",color:t.textMuted}}>{r.id}</td>
                <td style={{padding:'10px 14px',fontSize:12,color:t.text,fontWeight:500}}>{r.nombre}</td>
                <td style={{padding:'10px 14px'}}><span style={{padding:'2px 8px',borderRadius:4,fontSize:11,background:t.tag,color:t.tagText,fontFamily:"'DM Mono',monospace"}}>{r.tabla}</span></td>
                <td style={{padding:'10px 14px',fontSize:11,color:t.textMuted}}>{r.tipo}</td>
                <td style={{padding:'10px 14px'}}><span style={{fontSize:13,fontWeight:700,color:r.violaciones>0?t.err:t.textLight}}>{r.violaciones}</span></td>
                <td style={{padding:'10px 14px'}}><Badge status={r.activa?'activo':'inactivo'}/></td>
                <td style={{padding:'10px 14px'}}>
                  <div style={{display:'flex',gap:6}}>
                    <button onClick={()=>toggle(r.id)} style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.divider}`,background:'transparent',color:r.activa?t.err:t.ok,fontSize:11,fontWeight:600,cursor:'pointer'}}>{r.activa?'Pausar':'Activar'}</button>
                    <button style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.divider}`,background:'transparent',color:t.textMuted,fontSize:11,fontWeight:600,cursor:'pointer'}}>Editar</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

/* ─────────────────── PERSONAL ─────────────────── */
const Personal = () => {
  const t = useTheme();
  const { filters } = useFilters();
  const [sel, setSel] = useState(null);

  const filtered = MOCK.personal.filter(p => {
    if (filters.estado!=='todos' && p.estado!==filters.estado) return false;
    if (filters.rol!=='todos' && p.rol!==filters.rol) return false;
    if (filters.q && !p.nombre.toLowerCase().includes(filters.q.toLowerCase()) && !p.rol.toLowerCase().includes(filters.q.toLowerCase())) return false;
    return true;
  });

  const selUser = sel ? MOCK.personal.find(p=>p.id===sel) : null;

  return (
    <div className="fade-in">
      <SectionHeader title="Auditoría de Personal"
        subtitle="Accesos, actividad y seguimiento por usuario"
        action={<Btn size="sm" icon="plus">Agregar usuario</Btn>}/>
      <div style={{display:'flex',gap:12,marginBottom:16}}>
        {[
          {l:'Activos',v:MOCK.personal.filter(p=>p.estado==='activo').length,c:t.ok},
          {l:'Inactivos',v:MOCK.personal.filter(p=>p.estado==='inactivo').length,c:t.err},
          {l:'Pendientes',v:MOCK.personal.filter(p=>p.estado==='pendiente').length,c:t.warn},
          {l:'Total',v:MOCK.personal.length,c:t.text},
        ].map(s=>(
          <Card key={s.l} p="12px 16px" style={{flex:1}}>
            <div style={{fontSize:22,fontWeight:800,color:s.c}}>{s.v}</div>
            <div style={{fontSize:11,color:t.textMuted,marginTop:2}}>{s.l}</div>
          </Card>
        ))}
      </div>
      <FilterBar config={{
        search:true, searchPlaceholder:'Buscar por nombre o rol...',
        rol:true,
        estado:true, estadoOpts:['todos','activo','inactivo','pendiente'],
        resultCount:filtered.length,
      }}/>
      <div style={{display:'grid',gridTemplateColumns:sel?'1fr 300px':'1fr',gap:16}}>
        <Card p="0">
          <table style={{width:'100%',borderCollapse:'collapse'}}>
            <thead>
              <tr style={{borderBottom:`2px solid ${t.divider}`}}>
                {['Usuario','Rol','Estado','Último acceso','Módulos','Actividad','Acciones'].map(h=>(
                  <th key={h} style={{padding:'11px 14px',textAlign:'left',fontSize:11,color:t.textMuted,fontWeight:700,background:t.card}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length===0&&<tr><td colSpan={7} style={{padding:'32px',textAlign:'center',color:t.textMuted,fontSize:13}}>Sin resultados</td></tr>}
              {filtered.map(p=>(
                <tr key={p.id} onClick={()=>setSel(sel===p.id?null:p.id)}
                  style={{borderBottom:`1px solid ${t.divider}`,cursor:'pointer',
                    background:sel===p.id?t.accentLight:'transparent',transition:'background .12s'}}
                  onMouseEnter={e=>{if(sel!==p.id)e.currentTarget.style.background=t.rowHov;}}
                  onMouseLeave={e=>{if(sel!==p.id)e.currentTarget.style.background='transparent';}}>
                  <td style={{padding:'10px 14px'}}>
                    <div style={{display:'flex',alignItems:'center',gap:8}}>
                      <div style={{width:28,height:28,borderRadius:'50%',background:t.accentLight,
                        display:'flex',alignItems:'center',justifyContent:'center',fontSize:10,fontWeight:700,color:t.accentText,flexShrink:0}}>
                        {p.nombre.split(' ').map(n=>n[0]).join('').slice(0,2)}
                      </div>
                      <span style={{fontSize:12,fontWeight:600,color:t.text}}>{p.nombre}</span>
                    </div>
                  </td>
                  <td style={{padding:'10px 14px',fontSize:11,color:t.textMuted}}>{p.rol}</td>
                  <td style={{padding:'10px 14px'}}><Badge status={p.estado==='pendiente'?'pendiente_user':p.estado}/></td>
                  <td style={{padding:'10px 14px',fontSize:11,color:t.textMuted}}>{p.acceso}</td>
                  <td style={{padding:'10px 14px'}}>
                    <div style={{display:'flex',gap:4,flexWrap:'wrap'}}>
                      {p.modulos.slice(0,2).map(m=><span key={m} style={{padding:'2px 6px',borderRadius:4,fontSize:10,background:t.tag,color:t.tagText}}>{m}</span>)}
                      {p.modulos.length>2&&<span style={{fontSize:10,color:t.textLight}}>+{p.modulos.length-2}</span>}
                    </div>
                  </td>
                  <td style={{padding:'10px 14px'}}>
                    <span style={{fontSize:11,fontWeight:600,color:p.actividad==='Alta'?t.ok:p.actividad==='Media'?t.accent:p.actividad==='Baja'?t.warn:t.textLight}}>{p.actividad}</span>
                  </td>
                  <td style={{padding:'10px 14px'}}>
                    <div style={{display:'flex',gap:6}}>
                      <button style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.divider}`,background:'transparent',color:t.textMuted,fontSize:11,fontWeight:600,cursor:'pointer'}}>Ver log</button>
                      {p.estado==='pendiente'&&<button style={{padding:'4px 10px',borderRadius:6,border:`1px solid ${t.ok}`,background:t.okLight,color:t.ok,fontSize:11,fontWeight:600,cursor:'pointer'}}>Activar</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        {selUser&&(
          <Card className="slide-in">
            <div style={{display:'flex',justifyContent:'space-between',marginBottom:16}}>
              <h3 style={{fontSize:14,fontWeight:700,color:t.text}}>Detalle</h3>
              <button onClick={()=>setSel(null)} style={{border:'none',background:'transparent',cursor:'pointer'}}><Icon name="x" size={16} color={t.textMuted}/></button>
            </div>
            <div style={{display:'flex',flexDirection:'column',alignItems:'center',marginBottom:16}}>
              <div style={{width:52,height:52,borderRadius:'50%',background:t.accentLight,
                display:'flex',alignItems:'center',justifyContent:'center',fontSize:18,fontWeight:800,color:t.accentText}}>
                {selUser.nombre.split(' ').map(n=>n[0]).join('').slice(0,2)}
              </div>
              <div style={{fontSize:14,fontWeight:700,color:t.text,marginTop:8}}>{selUser.nombre}</div>
              <div style={{fontSize:12,color:t.textMuted}}>{selUser.rol}</div>
              <div style={{marginTop:8}}><Badge status={selUser.estado==='pendiente'?'pendiente_user':selUser.estado}/></div>
            </div>
            {[['Último acceso',selUser.acceso],['Acciones totales',selUser.acc],['Actividad',selUser.actividad]].map(([l,v])=>(
              <div key={l} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:`1px solid ${t.divider}`,fontSize:12}}>
                <span style={{color:t.textMuted}}>{l}</span>
                <span style={{fontWeight:600,color:t.text}}>{v}</span>
              </div>
            ))}
            <div style={{marginTop:12}}>
              <div style={{fontSize:11,color:t.textMuted,fontWeight:600,marginBottom:8}}>Módulos con acceso</div>
              <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
                {selUser.modulos.length>0
                  ?selUser.modulos.map(m=><span key={m} style={{padding:'4px 10px',borderRadius:20,fontSize:11,background:t.tag,color:t.tagText,fontWeight:600}}>{m}</span>)
                  :<span style={{fontSize:11,color:t.textLight}}>Sin accesos asignados</span>
                }
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

/* ─────────────────── MODELOS IA ─────────────────── */
const ModelosIA = () => {
  const t = useTheme();
  const models=[
    {id:'m1',name:'Proyección de Cosecha',tipo:'Regresión',estado:'ok',last:'Hace 6h',acc:'94.2%',vars:'Fundo, Semana, Variedad, Temp, HR',desc:'Predice TM de arándano por fundo/semana para las próximas 8 semanas de exportación.'},
    {id:'m2',name:'Calibres de Fruta',tipo:'Clasificación',estado:'warning',last:'Hace 18h',acc:'91.7%',vars:'Cama, Variedad, Semana fenológica, Riego',desc:'Predice distribución de calibres (mm) para optimizar empaque y precios de exportación.'},
    {id:'m3',name:'Detección de Anomalías ETL',tipo:'Anomaly Detection',estado:'ok',last:'Hace 1h',acc:'98.1%',vars:'Registros por run, Tiempo, Errores, Tabla',desc:'Detecta corridas ETL anómalas antes de que impacten el DW. Umbral: 3σ.'},
  ];
  const [sel,setSel]=useState('m1');
  const selModel=models.find(m=>m.id===sel);
  return (
    <div className="fade-in">
      <SectionHeader title="Modelos de Inteligencia Artificial"
        subtitle="Proyecciones y predicciones integradas al pipeline"
        action={<Btn size="sm" icon="cpu">Ejecutar modelo</Btn>}/>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:14,marginBottom:20}}>
        {models.map(m=>(
          <Card key={m.id} style={{cursor:'pointer',border:`1px solid ${sel===m.id?t.accent:t.cardBorder}`,
            boxShadow:sel===m.id?`0 0 0 2px ${t.accent}33, ${t.shadow}`:t.shadow,transition:'all .18s'}}
            onClick={()=>setSel(m.id)}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:10}}>
              <span style={{padding:'3px 10px',borderRadius:20,fontSize:10,fontWeight:600,background:t.accentLight,color:t.accentText}}>{m.tipo}</span>
              <Badge status={m.estado}/>
            </div>
            <div style={{fontSize:14,fontWeight:700,color:t.text,marginBottom:4}}>{m.name}</div>
            <div style={{display:'flex',justifyContent:'space-between',marginTop:12}}>
              <div><div style={{fontSize:10,color:t.textMuted}}>Precisión</div><div style={{fontSize:18,fontWeight:800,color:m.estado==='ok'?t.ok:t.warn}}>{m.acc}</div></div>
              <div style={{textAlign:'right'}}><div style={{fontSize:10,color:t.textMuted}}>Última ejecución</div><div style={{fontSize:11,fontWeight:600,color:t.text}}>{m.last}</div></div>
            </div>
          </Card>
        ))}
      </div>
      {selModel&&(
        <Card className="fade-in">
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:16}}>
            <div>
              <h3 style={{fontSize:16,fontWeight:700,color:t.text}}>{selModel.name}</h3>
              <p style={{fontSize:12,color:t.textMuted,marginTop:4}}>{selModel.desc}</p>
            </div>
            <div style={{display:'flex',gap:8}}>
              <Btn size="sm" variant="secondary" icon="eye">Ver resultados</Btn>
              <Btn size="sm" icon="zap">Ejecutar ahora</Btn>
            </div>
          </div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:16}}>
            {[['Tipo',selModel.tipo],['Precisión',selModel.acc],['Estado',selModel.estado.toUpperCase()],['Variables',selModel.vars.split(',').length]].map(([l,v])=>(
              <div key={l} style={{background:t.accentLight,borderRadius:10,padding:'12px 14px'}}>
                <div style={{fontSize:11,color:t.textMuted,marginBottom:4}}>{l}</div>
                <div style={{fontSize:l==='Precisión'?20:14,fontWeight:l==='Precisión'?800:600,color:t.text}}>{v}</div>
              </div>
            ))}
          </div>
          <div style={{fontSize:11,fontWeight:600,color:t.textMuted,marginBottom:8,textTransform:'uppercase',letterSpacing:'0.6px'}}>Variables de entrada</div>
          <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
            {selModel.vars.split(',').map(v=>(
              <span key={v} style={{padding:'4px 12px',borderRadius:20,fontSize:11,fontWeight:600,background:t.tag,color:t.tagText}}>{v.trim()}</span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};

/* ─────────────────── PIPELINE ─────────────────── */
const Pipeline = () => {
  const t = useTheme();
  const stages=[
    {id:1,name:'Extracción',src:'Oracle ERP',dest:'Staging DB',status:'ok',freq:'Cada 4h',last:'14:32'},
    {id:2,name:'Transformación',src:'Staging DB',dest:'Transform Layer',status:'ok',freq:'Post-extracción',last:'14:36'},
    {id:3,name:'Homologación',src:'Transform Layer',dest:'Master Tables',status:'warning',freq:'Post-transform',last:'14:37'},
    {id:4,name:'Carga DW',src:'Master Tables',dest:'Data Warehouse',status:'ok',freq:'Post-homologación',last:'14:40'},
    {id:5,name:'Modelos IA',src:'Data Warehouse',dest:'Results DB',status:'ok',freq:'Cada 6h',last:'08:00'},
  ];
  return (
    <div className="fade-in">
      <SectionHeader title="Configuración de Pipeline"
        subtitle="Etapas del flujo ETL y parámetros de ejecución"
        action={<div style={{display:'flex',gap:8}}><Btn size="sm" variant="secondary" icon="settings">Configurar</Btn><Btn size="sm" icon="zap">Ejecutar pipeline</Btn></div>}/>
      <div style={{display:'flex',alignItems:'center',gap:0,marginBottom:24,overflowX:'auto',paddingBottom:4}}>
        {stages.map((s,i)=>(
          <React.Fragment key={s.id}>
            <Card p="14px 16px" style={{minWidth:160,flexShrink:0}}>
              <div style={{display:'flex',justifyContent:'space-between',marginBottom:8}}>
                <span style={{fontSize:10,color:t.textMuted,fontWeight:600}}>PASO {s.id}</span>
                <StatusDot status={s.status}/>
              </div>
              <div style={{fontSize:13,fontWeight:700,color:t.text}}>{s.name}</div>
              <div style={{fontSize:10,color:t.textMuted,marginTop:4}}>{s.src}</div>
              <div style={{fontSize:10,color:t.accent,marginTop:2,fontWeight:500}}>→ {s.dest}</div>
              <div style={{marginTop:8,paddingTop:8,borderTop:`1px solid ${t.divider}`,fontSize:10,color:t.textLight}}>{s.freq} · {s.last}</div>
            </Card>
            {i<stages.length-1&&(
              <div style={{width:32,height:2,background:t.accent,flexShrink:0,position:'relative'}}>
                <div style={{position:'absolute',right:-4,top:-4,width:10,height:10,background:t.accent,clipPath:'polygon(0 0, 100% 50%, 0 100%)'}}/>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
        <Card>
          <div style={{fontSize:13,fontWeight:700,color:t.text,marginBottom:14}}>Parámetros Globales</div>
          {[['Frecuencia base','Cada 4 horas'],['Timeout por etapa','15 minutos'],['Reintentos automáticos','3'],['Notificaciones','Email + Portal'],['Modo producción','Activo'],['Ventana de mantenimiento','02:00–03:00']].map(([k,v])=>(
            <div key={k} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:`1px solid ${t.divider}`,fontSize:12}}>
              <span style={{color:t.textMuted}}>{k}</span><span style={{fontWeight:600,color:t.text}}>{v}</span>
            </div>
          ))}
        </Card>
        <Card>
          <div style={{fontSize:13,fontWeight:700,color:t.text,marginBottom:14}}>Estado actual</div>
          <div style={{display:'flex',flexDirection:'column',gap:10}}>
            {stages.map(s=>(
              <div key={s.id} style={{display:'flex',alignItems:'center',gap:10}}>
                <StatusDot status={s.status}/>
                <span style={{fontSize:12,fontWeight:600,color:t.text,flex:1}}>{s.name}</span>
                <span style={{fontSize:11,color:t.textMuted}}>{s.last}</span>
                <Badge status={s.status}/>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

/* ─────────────────── SALUD ─────────────────── */
const Salud = () => {
  const t = useTheme();
  return (
    <div className="fade-in">
      <SectionHeader title="Salud del Sistema" subtitle="Estado en tiempo real de componentes críticos"
        action={<Btn size="sm" variant="secondary" icon="refresh">Actualizar</Btn>}/>
      <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:14}}>
        {MOCK.health.map(h=>(
          <Card key={h.key}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:14}}>
              <div style={{display:'flex',alignItems:'center',gap:10}}>
                <div style={{width:36,height:36,borderRadius:10,background:h.status==='ok'?t.okLight:h.status==='warning'?t.warnLight:t.errLight,display:'flex',alignItems:'center',justifyContent:'center'}}>
                  <Icon name={h.key==='db'?'db':h.key==='etl'?'refresh':'cpu'} size={16} color={h.status==='ok'?t.ok:h.status==='warning'?t.warn:t.err} sw={2}/>
                </div>
                <div>
                  <div style={{fontSize:14,fontWeight:700,color:t.text}}>{h.name}</div>
                  <div style={{fontSize:11,color:t.textMuted}}>{h.detail}</div>
                </div>
              </div>
              <Badge status={h.status}/>
            </div>
            <div style={{display:'flex',gap:16}}>
              <div style={{flex:1,background:t.accentLight,borderRadius:8,padding:'10px 12px'}}>
                <div style={{fontSize:10,color:t.textMuted}}>Último chequeo</div>
                <div style={{fontSize:13,fontWeight:700,color:t.text,marginTop:2}}>{h.check}</div>
              </div>
              <div style={{flex:1,background:t.accentLight,borderRadius:8,padding:'10px 12px'}}>
                <div style={{fontSize:10,color:t.textMuted}}>Estado</div>
                <div style={{fontSize:13,fontWeight:700,color:h.status==='ok'?t.ok:h.status==='warning'?t.warn:t.err,marginTop:2,textTransform:'capitalize'}}>{h.status}</div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

Object.assign(window, { Geografia, Homologacion, ETLAudit, Reglas, Personal, ModelosIA, Pipeline, Salud });
