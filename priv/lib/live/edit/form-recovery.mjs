// Effect-only recovery beside ordinary Live fields. Live keeps their rendering,
// native input events, focus and patch ownership; this region owns its footer.
import {TextDraftStore} from './text-draft.mjs';
import {FormDraft} from './form-draft.mjs';
export function mountFormRecovery(root,model,services){
  let current=model,container=null,disposed=false;
  let store;try{store=new TextDraftStore(model.resource);}catch(error){store={warning:error,read:()=>null,write:()=>false,remove:()=>{}};}
  const draft=new FormDraft(model,store);
  const status=document.createElement('p'),download=document.createElement('button'),discard=document.createElement('button');
  status.setAttribute('role','status');status.setAttribute('aria-live','polite');download.type=discard.type='button';
  download.textContent='Download property draft';discard.textContent='Use current values';root.replaceChildren(status,download,discard);
  const notify=()=>{if(!disposed&&!current.readonly){
    if(current.locals)services.dispatch(draft.assignments(current.locals),{});
    else services.dispatch(current.event,{changes:draft.changes(),basis:draft.basis});
  }};
  const paint=()=>{
    root.dataset.dirty=String(draft.dirty);root.dataset.stale=String(draft.stale);
    status.textContent=store.warning?'Recovery storage is unavailable. Download this draft before leaving.':draft.orphaned?'Some fields changed. Your draft is retained for comparison.':draft.stale?'Source changed. Your property draft is kept.':draft.dirty?(draft.restored?'Recovered property draft':'Property draft on this device'):'Properties match saved source';
    download.hidden=discard.hidden=!draft.dirty&&!store.warning;
  };
  const capture=event=>{
    const field=current.fields.find(f=>container.querySelector('#'+CSS.escape(f.id))===event.target);
    if(!field||current.readonly)return;
    draft.edit(field.key,event.target.type==='checkbox'?event.target.checked:event.target.value);paint();
    // Follow the native event with the complete attempted field set. This also
    // preserves another field when several inputs arrive before a Live echo.
    queueMicrotask(notify);
  };
  const bind=()=>{
    const next=root.closest('[data-recovered-form]');if(next===container)return;
    container?.removeEventListener('input',capture,true);container?.removeEventListener('change',capture,true);container=next;
    container?.addEventListener('input',capture,true);container?.addEventListener('change',capture,true);
  };
  const showValues=()=>{
    for(const field of current.fields){
      if(!Object.hasOwn(draft.values,field.key))continue;
      const input=container?.querySelector('#'+CSS.escape(field.id));if(!input||input===document.activeElement)continue;
      if(input.type==='checkbox')input.checked=!!draft.values[field.key];else input.value=draft.values[field.key]??'';
    }
  };
  download.onclick=()=>{
    const labels=new Map(current.fields.map(f=>[f.key,f.label||f.key]));
    const text='Property draft\nSource basis: '+draft.basis+'\n\n'+Object.entries(draft.values).map(([k,v])=>(labels.get(k)||k)+': '+String(v??'')).join('\n')+'\n';
    const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download='property-draft.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  discard.onclick=()=>{draft.discard();paint();notify();};
  bind();showValues();paint();if(draft.dirty)queueMicrotask(notify);
  return {update(next){
    const before=JSON.stringify(draft.values),basis=draft.basis;current=next;draft.receive(next);bind();showValues();paint();
    if(before!==JSON.stringify(draft.values)||basis!==draft.basis)queueMicrotask(notify);
  },dispose(){disposed=true;draft.persist();container?.removeEventListener('input',capture,true);container?.removeEventListener('change',capture,true);download.onclick=discard.onclick=null;}};
}
