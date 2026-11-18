// Compact successor to tooling.pulse's injected chip / tooling/studio.js.
// Reuses Live's existing patch seam; no second socket, global tap or cell writer.
(() => {
  if (window.EnchantInspector) return;
  const source = () => document.getElementById('enchant-inspector-source');
  if (!source()) return;
  // Like the original Studio shell, keep tools outside Live's replaceable root.
  const host = document.createElement('div');host.id='enchant-inspector';document.body.append(host);
  const root = host.attachShadow({mode: 'open'});
  const paths = {
    logo: '<path d="M5 5h14M5 12h10M5 19h14M5 5v14"/>',
    pick: '<path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><rect x="6" y="6" width="12" height="12" rx="2"/>',
    paint: '<path d="m14 3 7 7-9 9-7-7zM5 12l-2 2 7 7 2-2M15 4l-5 5"/>',
    server: '<rect x="4" y="4" width="16" height="6" rx="2"/><rect x="4" y="14" width="16" height="6" rx="2"/><path d="M7 7h.1M7 17h.1M14 7h3M14 17h3"/>',
    tools: '<path d="m4 7 5 5-5 5M12 17h8"/>',
    close: '<path d="m7 7 10 10M17 7 7 17"/>',
    updates: '<path d="M3 18h3l3-12 5 15 3-10h4"/>',
    refresh: '<path d="M20 10a8 8 0 1 0-2 8M20 4v6h-6"/>'
    ,spacing: '<path d="M3 7v10M21 7v10M5 12h14M8 9l-3 3 3 3M16 9l3 3-3 3"/>'
    ,corner: '<path d="M5 19V9a4 4 0 0 1 4-4h10"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name]}</svg>`;
  root.innerHTML = `<link rel="stylesheet" href="/__enchant/inspector.css">
    <section class="panel" id="dev-panel" hidden aria-label="Dev tools"><div class="head"><b id="title">Updates</b>
    <div class="tabs"><button data-tab="updates" aria-selected="true">Updates</button><button data-tab="tools" aria-selected="false">Tools</button><button data-tab="element" aria-selected="false">Loom</button><button data-tab="server" aria-selected="false">Server</button></div></div><div class="body"></div></section>
    <nav class="dock" aria-label="Dev tools">
    <button class="tool brand" data-action="open" aria-label="Open dev tools" title="Open dev tools" aria-expanded="false" aria-controls="dev-panel">${icon('logo')}</button>
    <div class="spark" role="button" tabindex="0" data-action="updates" title="Page updates" aria-label="Page updates"></div><div class="rule"></div>
    <button class="tool" data-action="paint" aria-label="Highlight updates" title="Highlight updates" aria-pressed="false">${icon('paint')}</button>
    <button class="tool" data-action="pick" aria-label="Pick an element" title="Pick an element" aria-pressed="false">${icon('pick')}</button>
    <button class="tool" data-action="tools" aria-label="Tool activity" title="Tool activity">${icon('tools')}</button>
    <button class="tool" data-action="server" aria-label="Server activity" title="Server activity">${icon('server')}</button></nav>`;
  const $ = s => root.querySelector(s);
  const panel = $('.panel'), body = $('.body'), toggle = $('.brand');
  const history = [], boxes = new Set(), timers = new Set();
  let open = false, tab = 'updates', paint = false, picking = false, selected = null;
  let selectedRun = null;
  let copyStatus = '';
  const sampling = () => tab==='server'||tab==='tools';
  const runId = () => {const n=Number(source()?.dataset.toolRun);return Number.isSafeInteger(n)&&n>0?n:null;};
  let sample = null, error = false, poll = null, flight = null, generation = 0;
  let disposed = false, suspended = false;
  let queries = 0, pending = 0, peakFlights = 0, lastAt = 0;
  let draw = null, draws = 0, paintCredits = 16, paintLookups = 0;
  const overlay = document.createElement('div');
  overlay.id = 'enchant-inspector-overlays';
  overlay.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147482900';
  document.body.append(overlay);
  const pickBox = document.createElement('div');
  pickBox.style.cssText = 'position:fixed;pointer-events:none;border:1.5px solid #368e76;background:#368e7610;border-radius:3px;display:none';
  overlay.append(pickBox);
  const text = (parent, tag, value) => {const n=document.createElement(tag);n.textContent=String(value);parent.append(n);return n;};
  const mb = n => Number.isFinite(n) ? `${Math.round(n/1048576)} MB` : '—';
  const bytes = n => n<1024?`${n} B`:`${(n/1024).toFixed(1)} KiB`;
  const stateName = p => ({ready:'Ready',running:'Working',blocked:'Stopped',stale:'Out of date',unavailable:'Unavailable',refused:'Unavailable'}[p.status] || (p.demand ? 'Waiting' : 'Not used'));
  function bars(parent, big) {
    parent.replaceChildren();
    const max = Math.max(1, ...history.map(f=>f.ops||0));
    history.forEach(f=>{const bar=document.createElement(big&&f.run?'button':'i');if(big&&f.run){bar.dataset.run=String(f.run);bar.setAttribute('aria-label','Explain update');} bar.style.height=`${f.ops===null?(big?35:12):2+(f.ops/max)*(big?48:13)}px`;
      if(f.ops===null)bar.style.background='#a9b8aa';bar.title=f.ops===null?'Whole page updated':`${f.ops} changes`;if(big&&f.run)bar.title+=' · Explain';parent.append(bar);});
  }
  function showPanel(visible) {
    open=visible;
    panel.hidden=!visible;
    const label=visible?'Close dev tools':'Open dev tools';
    toggle.setAttribute('aria-expanded',String(visible));
    toggle.setAttribute('aria-label',label);
    toggle.title=label;
    toggle.innerHTML=icon(visible?'close':'logo');
  }
  function activate(next) {
    if (disposed) return;
    stopSampling();if(tab!==next)copyStatus='';tab=next;if(!open)showPanel(true);
    root.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===tab)));
    $('#title').textContent={updates:'Updates',element:'Loom',server:'Server',tools:'Tools'}[tab];
    render(); if(sampling()) refresh();
  }
  function stopSampling() {
    generation++;clearTimeout(poll);poll=null;
    if(flight) flight.abort();
  }
  function close() {
    const returnFocus=panel.contains(root.activeElement);
    if(open)showPanel(false);
    if(returnFocus)toggle.focus();
    stopSampling();setPicking(false);selected=null;pickBox.style.display='none';
  }
  async function refresh() {
    if(disposed||suspended||!open||!sampling()||document.hidden||!source()||!host.isConnected||flight)return;
    const current=generation, controller=new AbortController();flight=controller;
    queries++;pending++;peakFlights=Math.max(peakFlights,pending);
    const deadline=setTimeout(()=>controller.abort(),5000);
    try {
      const r=await fetch('/__enchant/snapshot.json',{credentials:'same-origin',cache:'no-store',signal:controller.signal});
      if(!r.ok)throw Error('unavailable');
      const next=await r.json();
      if(current!==generation||!open||disposed)return;
      if(next.schema!=='enchant.observatory.v1')throw Error('schema');
      sample=next;lastAt=Date.now();error=false;
    } catch(e) {if(current===generation&&!disposed)error=true;}
    finally {
      pending--;clearTimeout(deadline);if(flight===controller)flight=null;
      if(!disposed&&!suspended&&open&&sampling()&&!document.hidden) {
        render();clearTimeout(poll);poll=setTimeout(refresh,2000);
      }
    }
  }
  function render() {
    if(!open||disposed||suspended)return;
    const focused=root.activeElement;
    const key=body.contains(focused) && (focused.dataset.run ?? focused.dataset.action);
    renderPanel();
    if(key) {
      const replacement=[...body.querySelectorAll('button[data-run],button[data-action]')]
        .find(button=>(button.dataset.run ?? button.dataset.action)===key);
      replacement?.focus({preventScroll:true});
    }
  }
  function renderPanel() {
    body.replaceChildren();
    if(tab==='updates') {
      const chart=text(body,'div','');chart.className='history';bars(chart,true);
      const caption=text(body,'div','');caption.className='frame-caption';
      text(caption,'span',`${history.length} updates`);
      const last=history[history.length-1];text(caption,'span',last?(last.ops===null?'Full view':`${last.ops} changes`):'');
      return;
    }
    if(tab==='element') {renderSelection();return;}
    if(tab==='tools') {renderTools();return;}
    if(!sample) {
      const empty=text(body,'div',error?'Unavailable':'…');empty.className='empty';
    } else {
      const owners=sample.work||[], jobs=owners.flatMap(o=>o.jobs||[]), results=sample.projections||[];
      const running=owners.length&&owners.every(o=>o.available&&Number.isInteger(o.running))
        ? owners.reduce((total,o)=>total+o.running,0) : '—';
      const stats=text(body,'div','');stats.className='stats';
      [[running,'Jobs running',owners.length?'Registered work owners':'No work owners registered'],
       [results.length?`${results.filter(p=>p.status==='ready').length}/${results.length}`:'—','Results ready','Registered projections'],
       [mb(sample.runtime?.vm?.memory),'VM memory','Whole Erlang VM']].forEach(([v,label,detail])=>{
         const cell=text(stats,'div','');cell.className='stat';cell.title=detail;text(cell,'strong',v);text(cell,'small',label);
       });
      results.slice(0,8).forEach(p=>{
        const row=text(body,'div','');row.className='line';
        const label=text(row,'span','');const dot=text(label,'i','');dot.className=`dot ${['ready','running','blocked'].includes(p.status)?p.status:''}`;
        label.append(document.createTextNode(String(p.name).replace(/^:/,'')));
        text(row,'small',stateName(p));
      });
      jobs.slice(0,6).forEach(j=>{const row=text(body,'div','');row.className='line';text(row,'span',j.title);text(row,'small',j.status==='running'?'Working':j.status==='done'?'Done':j.status);});
      if(sample.versions) {
        const versions=text(body,'div','');versions.className='versions';
        text(versions,'code',`BL ${sample.versions.bl}`);
        text(versions,'code',`OTP ${sample.versions.otp}`);
        if(sample.versions.sdk)text(versions,'code',`SDK ${sample.versions.sdk.slice(0,12)}`).title=sample.versions.sdk;
      }
    }
    const footer=text(body,'div','');footer.className='footer';
    text(footer,'span',error?'Sample unavailable':lastAt?`Updated ${new Date(lastAt).toLocaleTimeString()}`:'');
    const actions=text(footer,'span','');
    if(sample)text(actions,'button',copyStatus||'Copy report').dataset.action='copy-report';
    text(actions,'button','Refresh').dataset.action='refresh';
  }
  function sourcePosition(row) {
    const location=row?.location;
    return location?.line ? `${location.path}:${location.line}` : location?.path;
  }
  const toolName = kind => ({editor:'Editor',check:'Check',index:'Index',render:'Page','quick-check':'Quick check',outline:'Outline'}[kind]||'Tool');
  function report() {
    return {
      schema:'enchant.inspector.report.v1',
      versions:sample.versions,
      memoryBytes:sample.runtime?.vm?.memory,
      omittedRuns:sample.activity?.dropped||0,
      tools:(sample.activity?.recent||[]).filter(r=>r.tool!=='render').slice(0,16).map(r=>({
        tool:r.tool, state:r.state, cause:r.cause, origin:r.origin,
        elapsedMs:r['elapsed-ms'], waitMs:r['wait-ms'],
        counts:r.counts, cache:r.cache, summary:r.summary
      }))
    };
  }
  async function copy(value) {
    try {await navigator.clipboard.writeText(value);copyStatus='Copied';}
    catch {copyStatus='Copy unavailable';}
    render();
  }
  function sourceTarget(href) {
    if(!href)return null;
    try {
      const url=new URL(href,window.location.origin);
      return url.origin===window.location.origin?url:null;
    } catch {return null;}
  }
  function renderTools() {
    const tape=sample?.activity;
    if(!tape?.available){text(body,'div',error?'Unavailable':sample?'Not enabled':'…').className='empty';return;}
    const rows=[...(tape.running||[]),...(tape.recent||[])];
    if(!rows.length){text(body,'div','No tool runs yet').className='empty';return;}
    const chosen=rows.find(r=>r.id===selectedRun);
    if(selectedRun&&!chosen&&!flight&&sample){text(body,'small','Run no longer retained');selectedRun=null;}
    if(chosen) {
      const head=text(body,'div','');head.className='selection';text(head,'b',toolName(chosen.tool));
      const back=text(head,'button','All runs');back.dataset.action='all-runs';
      const receipt=sourceTarget(chosen['receipt-url']);
      if(receipt?.pathname.startsWith('/__enchant/receipts/')) {
        const link=text(head,'a','Receipt');link.href=receipt.href;
      }
      const location=sourcePosition(chosen);
      const subject=text(body,'div','');subject.className='selection';
      const target=sourceTarget(chosen.link);
      if(location&&target) {
        const link=text(subject,'a',location);link.href=target.href;
      } else if(location) {
        const pathButton=text(subject,'button',location);pathButton.title='Copy source path';
        pathButton.dataset.action='copy-source';
      } else text(subject,'small',chosen.subject).className='subject';
      if(chosen.origin)text(subject,'small',chosen.origin);
      const facts=text(body,'div','');facts.className='run-facts';
      const counts=chosen.counts||{};
      [[counts.computed||0,'Built'],[counts.reused||0,'Reused'],[`${chosen.wait_ms??chosen['wait-ms']??0} ms`,'Wait']].forEach(([v,label])=>{
        const cell=text(facts,'div','');text(cell,'strong',v);text(cell,'small',label);
      });
      text(body,'div',({'first-use':'First request','same-source':'Same source','source-changed':'Source changed','definitions-changed':'Definitions changed',requested:'Requested again'}[chosen.cause]||'Requested')).className='reason';
      if(chosen.changed?.length) {
        const providers=text(body,'div','');providers.className='function-names';
        chosen.changed.forEach(name=>text(providers,'code',name));
      }
      if(chosen['elapsed-ms']!=null) {
        const wait=chosen['wait-ms']||0;
        const timing=text(body,'div','');timing.className='line';
        text(timing,'span',`${Math.max(0,chosen['elapsed-ms']-wait)} ms outside wait`).title='Wall time minus recorded admission wait';
        text(timing,'small',`${chosen['elapsed-ms']} ms elapsed`);
      }
      if(chosen.cache) {
        const cache=text(body,'div','');cache.className='line';
        text(cache,'span',`${bytes(chosen.cache['kept-bytes'])} kept`);
        text(cache,'small',`${chosen.cache.evictions} evicted`);
      }
      if(chosen.summary) {
        const result=chosen.summary;
        text(body,'small',result.repeated!=null?`${result.repeated} repeated definitions`:
          `${result.definitions} definitions · ${result.imports} imports`);
      }
      if(chosen.tool==='check')text(body,'small','Rules run each time');
      if(counts.unstable)text(body,'small','Definitions changed during work');
      if(counts.declined)text(body,'small','Answer not kept');
      if(chosen.state==='failed'||chosen.state==='interrupted')text(body,'small',chosen.state==='failed'?'Run failed':'Caller stopped');
      if(counts.evaluated) {
        text(body,'small',`${counts.evaluated} function evaluations`);
        const names=text(body,'div','');names.className='function-names';
        (chosen.items||[]).forEach(name=>text(names,'code',name));
      }
      const children=rows.filter(r=>r.parent===chosen.id);
      children.forEach(r=>runRow(r,true));
      if(chosen.parent&&rows.some(r=>r.id===chosen.parent)) {
        const parent=text(body,'button','↑ Parent run');parent.className='parent-run';parent.dataset.run=chosen.parent;
      }
    } else {const tools=rows.filter(r=>r.tool!=='render');if(!tools.length)text(body,'div','No tool runs yet').className='empty';tools.slice(0,32).forEach(r=>runRow(r,false));}
    if(tape.dropped)text(body,'small','Some runs omitted');
    function runRow(r,child) {
      const row=text(body,'button','');row.className='run-row'+(child?' child':'');row.dataset.run=r.id;row.dataset.runId=r.id;row.dataset.tool=r.tool;row.dataset.cause=r.cause;
      const label=text(row,'span','');text(label,'i','').className='dot '+(r.state==='working'||r.state==='waiting'?'running':r.state==='failed'?'blocked':'ready');
      label.append(document.createTextNode(toolName(r.tool)+(r.origin==='CLI'?' · CLI':'')));
      const state=r.state==='waiting'?'Waiting':r.state==='working'?'Working':r.state==='failed'?'Failed':r.state==='interrupted'?'Stopped':(r.counts?.reused&&!r.counts?.computed)?'Reused':'Done';
      text(row,'small',`${state} · ${r['elapsed-ms']} ms`);row.title=r.subject;
    }
  }
  function colorKey(value) {
    if(/^#[0-9a-f]{3}$/i.test(value))return '#'+[...value.slice(1)].map(c=>c+c).join('').toLowerCase();
    if(/^#[0-9a-f]{6}$/i.test(value))return value.toLowerCase();
    const m=value.match(/^rgb\(\s*(\d+)[, ]+\s*(\d+)[, ]+\s*(\d+)\s*\)$/);
    return m?'#'+m.slice(1).map(v=>Number(v).toString(16).padStart(2,'0')).join(''):value;
  }
  function tokenName(category,value) {
    let scale={};try {scale=JSON.parse(source()?.dataset.loomScale||'{}');}catch{}
    return Object.entries(scale[category]||{}).find(([,v])=>colorKey(String(v))===colorKey(value))?.[0];
  }
  function renderSelection() {
    if(!selected?.isConnected) {
      const empty=text(body,'div','');empty.className='empty';empty.innerHTML=icon('pick');empty.title='Pick an element';return;
    }
    const s=getComputedStyle(selected),r=selected.getBoundingClientRect();
    const name=selected.closest('[data-tr],[data-component],[data-key]');
    const heading=text(body,'div','');heading.className='selection';
    text(heading,'b',name?.getAttribute('data-tr')||name?.getAttribute('data-component')||name?.getAttribute('data-key')||selected.tagName.toLowerCase());
    text(heading,'small',`${Math.round(r.width)} × ${Math.round(r.height)}`);
    const box=text(body,'div','');box.className='box';box.title='Outside spacing';
    text(box,'small',[s.marginTop,s.marginRight,s.marginBottom,s.marginLeft].map(v=>parseFloat(v)||0).join(' · '));
    const padding=text(box,'div','');padding.className='padding';padding.title='Inside spacing';
    text(padding,'small',[s.paddingTop,s.paddingRight,s.paddingBottom,s.paddingLeft].map(v=>parseFloat(v)||0).join(' · '));
    const content=text(padding,'div',selected.tagName.toLowerCase());content.className='content';
    const tokens=text(body,'div','');tokens.className='tokens';
    [['Gap',s.gap,'space'],['Corners',s.borderTopLeftRadius,'radius'],['Fill',s.backgroundColor,'color'],['Text',s.color,'color']].forEach(([label,value,category])=>{
      const row=text(tokens,'div','');row.className='token';
      const mark=text(row,category==='color'?'i':'em','');
      if(category==='color'){mark.className='swatch';mark.style.backgroundColor=value;}
      else mark.innerHTML=icon(category==='space'?'spacing':'corner');
      const name=tokenName(category,value);
      const details=text(row,'span',colorKey(value));text(details,'small',label+(name?` · ${name}`:''));row.title=`${label}: ${value}`;
    });
  }
  function position(el) {
    const r=el.getBoundingClientRect();pickBox.style.display='block';
    Object.assign(pickBox.style,{left:`${r.left}px`,top:`${r.top}px`,width:`${r.width}px`,height:`${r.height}px`});
  }
  function ownEvent(e) {return e.composedPath().includes(host);}
  function onMove(e) {if(!ownEvent(e)&&e.target instanceof Element)position(e.target);}
  function onPick(e) {
    if(ownEvent(e))return;
    if(!(e.target instanceof Element))return;
    e.preventDefault();e.stopImmediatePropagation();selected=e.target;setPicking(false);activate('element');position(selected);
  }
  function reposition(){if(selected?.isConnected)position(selected);else pickBox.style.display='none';}
  function setPicking(next) {
    picking=next;$('[data-action="pick"]').setAttribute('aria-pressed',String(next));
    document.removeEventListener('pointermove',onMove,true);document.removeEventListener('click',onPick,true);
    if(next){document.addEventListener('pointermove',onMove,true);document.addEventListener('click',onPick,true);}
  }
  function flash(node) {
    if(!(node instanceof Element)||host.contains(node)||boxes.size>=16)return;
    const r=node.getBoundingClientRect();if(!r.width||!r.height)return;
    const box=document.createElement('div');box.style.cssText=`position:fixed;left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;border:2px solid #388c73;background:#388c7314;border-radius:3px;pointer-events:none`;
    overlay.append(box);boxes.add(box);
    const timer=setTimeout(()=>{box.remove();boxes.delete(box);timers.delete(timer);},650);timers.add(timer);
  }
  function queueDraw() {
    if(draw===null)draw=requestAnimationFrame(()=>{
      draw=null;if(disposed)return;draws++;paintCredits=16;
      bars($('.spark'),false);if(open&&!sampling())render();if(selected)reposition();
    });
  }
  const toolsButton=$('[data-action=tools]');
  function syncCheck() {
    const id=Number(source()?.dataset.checkError);
    toolsButton.toggleAttribute('data-error',id>0);
    toolsButton.title=id>0?'Open source error':'Tool activity';
    toolsButton.setAttribute('aria-label',toolsButton.title);
    return id>0?id:null;
  }
  function onPatch(e) {
    if(suspended)return;
    if(!source()){dispose();return;}
    syncCheck();
    const ops=e.detail?.ops||[];history.push({ops:ops.length,run:runId()});if(history.length>32)history.shift();
    if(paint&&boxes.size<16)ops.slice(0,Math.min(paintCredits,16-boxes.size)).forEach(op=>{
      // Same Live path lookup used by the older tooling/studio.js instrument.
      paintCredits--;paintLookups++;
      try {let n=window.Live?.at(e.detail.root,op[1]);if(n?.nodeType===3)n=n.parentElement;flash(n);}catch{}
    });
    if(selected&&!selected.isConnected){selected=null;pickBox.style.display='none';}
    queueDraw();
  }
  function onMount(e) {
    if(suspended)return;
    if(!source()){dispose();return;}
    syncCheck();
    history.push({ops:null,run:runId()});if(history.length>32)history.shift();
    if(paint&&paintCredits>0){paintCredits--;paintLookups++;flash(e.detail.root);}
    if(selected&&!selected.isConnected){selected=null;pickBox.style.display='none';}
    queueDraw();
  }
  function onKey(e) {
    if(e.key==='Escape'&&open)close();
    if(ownEvent(e)&&(e.key==='Enter'||e.key===' ')) {
      const target=e.composedPath().find(n=>n?.dataset?.action==='updates');
      if(target){e.preventDefault();activate('updates');}
    }
  }
  root.addEventListener('click',e=>{
    const button=e.target.closest('[data-action],[data-tab],[data-run]');if(!button)return;
    e.stopPropagation();
    if(button.dataset.run){selectedRun=Number(button.dataset.run);if(tab==='tools'){render();}else activate('tools');return;}
    if(button.dataset.tab){activate(button.dataset.tab);return;}
    switch(button.dataset.action) {
      case 'open':open?close():activate('updates');break;
      case 'updates':activate('updates');break;
      case 'all-runs':selectedRun=null;render();break;
      case 'tools':selectedRun=syncCheck();activate('tools');break;
      case 'server':activate('server');break;
      case 'pick':activate('element');setPicking(!picking);break;
      case 'paint':paint=!paint;paintCredits=16;button.setAttribute('aria-pressed',String(paint));if(!paint)clearFlashes();break;
      case 'refresh':refresh();break;
      case 'copy-report':if(sample)copy(JSON.stringify(report(),null,2));break;
      case 'copy-source': {
        const row=[...(sample?.activity?.running||[]),...(sample?.activity?.recent||[])].find(r=>r.id===selectedRun);
        if(row?.location?.path)copy(sourcePosition(row));
        break;
      }
    }
  });
  function visibility(){stopSampling();if(!document.hidden&&open&&sampling())refresh();}
  function pageHide(event) {
    if(!event.persisted){dispose();return;}
    suspended=true;
    stopSampling();
    setPicking(false);selected=null;pickBox.style.display='none';
    if(draw!==null)cancelAnimationFrame(draw);draw=null;
    clearFlashes();
  }
  function pageShow(event) {
    if(!event.persisted||!suspended)return;
    if(!source()){dispose();return;}
    syncCheck();
    suspended=false;
    queueDraw();
    if(open&&sampling())refresh();
  }
  function clearFlashes() {
    timers.forEach(clearTimeout);timers.clear();
    boxes.forEach(box=>box.remove());boxes.clear();
  }
  function dispose() {
    if(disposed)return;disposed=true;close();
    if(draw!==null)cancelAnimationFrame(draw);draw=null;
    clearFlashes();overlay.remove();
    host.remove();
    document.removeEventListener('live:patch',onPatch);document.removeEventListener('visibilitychange',visibility);
    document.removeEventListener('live:mount',onMount);
    document.removeEventListener('keydown',onKey,true);document.removeEventListener('scroll',reposition,true);
    window.removeEventListener('resize',reposition);window.removeEventListener('pagehide',pageHide);
    window.removeEventListener('pageshow',pageShow);
  }
  syncCheck();
  document.addEventListener('live:patch',onPatch);document.addEventListener('live:mount',onMount);document.addEventListener('visibilitychange',visibility);
  document.addEventListener('keydown',onKey,true);document.addEventListener('scroll',reposition,true);
  window.addEventListener('resize',reposition);window.addEventListener('pagehide',pageHide);
  window.addEventListener('pageshow',pageShow);
  window.EnchantInspector={version:2,dispose,debug:()=>({open,tab,picking,paint,selectedRun,frames:history.length,flashes:boxes.size,
    requests:queries,sampleMemory:sample?.runtime?.vm?.memory??null,inFlight:!!flight,activeRequests:pending,peakFlights,pollScheduled:poll!==null,
    drawScheduled:draw!==null,draws,paintLookups,suspended,disposed})};
})();
