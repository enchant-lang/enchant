// Generic CodeMirror text input; source semantics and writes remain in BL.
import {EditorState,Compartment,Transaction} from '@codemirror/state';
import {EditorView,keymap,lineNumbers,drawSelection,highlightSpecialChars} from '@codemirror/view';
import {defaultKeymap,history,historyKeymap,indentWithTab} from '@codemirror/commands';
import {syntaxHighlighting,bracketMatching} from '@codemirror/language';
import {language,highlight} from './code.mjs';
import {TextDraft,TextDraftStore} from './text-draft.mjs';
import {settleAssignments,settlementError} from './settlement.mjs';
import {applySourceChanges,normalizeSource} from './source-changes.mjs';
export function mountSourceInput(root,model,services){
  let current=model,disposed=false,internal=false,isReadonly=!!model.readonly,acknowledged=null,publicationMessage='';
  const lifetime=new AbortController();
  // Access to storage itself can throw in a restricted browsing context.
  let store;try{store=new TextDraftStore(model.resource);}catch(error){store={warning:error,read:()=>null,write:()=>false,remove:()=>{}};}
  const draft=new TextDraft(model,store),readonly=new Compartment();
  root.replaceChildren();
  const container=document.createElement('div'),footer=document.createElement('div'),status=document.createElement('p');
  footer.className='ed-source-footer';status.setAttribute('role','status');status.setAttribute('aria-live','polite');footer.append(status);
  const download=document.createElement('button'),discard=document.createElement('button');
  download.type=discard.type='button';download.textContent='Download draft';discard.textContent='Use current source';
  footer.append(download,discard);root.append(container,footer);
  const notify=()=>{if(!disposed&&!current.readonly&&current.event)services.dispatch(current.event,{value:draft.value,basis:draft.basis});};
  const paint=()=>{
    root.dataset.dirty=String(draft.dirty);root.dataset.stale=String(draft.stale);
    download.textContent=store.corrupt?'Download retained bytes':'Download draft';
    status.textContent=store.warning?'Recovery storage is unavailable. Download your draft before leaving.':draft.stale?'Source changed. Your draft is kept; compare before saving.':publicationMessage||(draft.dirty?(draft.restored?'Recovered source draft':'Unsaved source draft'):'Saved source');
    download.hidden=!draft.dirty&&!store.warning;discard.hidden=!draft.dirty&&!store.warning;
  };
  const view=new EditorView({parent:container,state:EditorState.create({doc:draft.value,extensions:[
    language(model.language),syntaxHighlighting(highlight),lineNumbers(),drawSelection(),highlightSpecialChars(),bracketMatching(),history(),
    readonly.of([EditorState.readOnly.of(!!model.readonly),EditorView.editable.of(!model.readonly)]),
    EditorView.contentAttributes.of({'aria-label':model.label||'Source','aria-multiline':'true',spellcheck:'false'}),
    EditorView.lineWrapping,keymap.of([indentWithTab,...defaultKeymap,...historyKeymap]),
    EditorView.theme({'&':{maxHeight:'65vh',fontSize:'13px'},'.cm-scroller':{overflow:'auto'},'.cm-content':{fontFamily:'"IBM Plex Mono",monospace',padding:'14px 0',lineHeight:'1.8'},
      '.cm-gutters':{backgroundColor:'transparent',color:'var(--ed-muted)',borderRight:'1px solid var(--ed-line)'},'.cm-lineNumbers .cm-gutterElement':{padding:'0 10px'},
      '&.cm-focused':{outline:'2px solid var(--ed-accent)'},'.cm-cursor':{borderLeftColor:'var(--ed-ink)'},'.cm-selectionBackground':{background:'var(--ed-code-selection)!important'}}),
    EditorView.updateListener.of(update=>{
      if(internal||!update.docChanged)return;
      const changes=[];update.changes.iterChanges((from,to,_fromB,_toB,text)=>changes.push({from,to,text:text.toString()}));
      publicationMessage='';draft.edit(applySourceChanges(draft.value,changes));paint();notify();
    }),
  ]})});
  const replace=()=>{if(view.state.doc.toString()===normalizeSource(draft.value))return;internal=true;try{view.dispatch({changes:{from:0,to:view.state.doc.length,insert:draft.value},annotations:Transaction.addToHistory.of(false)});}finally{internal=false;}};
  download.onclick=()=>{
    const body=store.corrupt?JSON.stringify({...store.corrupt,current:{value:draft.value,basis:draft.basis}},null,2)+'\n':draft.value;
    const url=URL.createObjectURL(new Blob([body],{type:store.corrupt?'application/json':'text/plain;charset=utf-8'})),a=document.createElement('a');
    a.href=url;a.download=store.corrupt?'unreadable-source-draft.json':model.filename||'draft.org';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  discard.onclick=()=>{if(draft.discard()===false){report(Error('The saved draft could not be cleared. Keep the download and try again.'));return;}publicationMessage='';replace();paint();notify();};
  const settlementState=()=>({disposed,readonly:!!current.readonly,offline:document.documentElement.dataset.live==='0',
    conflict:!!store.unreadable,stale:draft.stale,composing:view.composing,token:JSON.stringify([draft.basis,draft.value])});
  const report=error=>{publicationMessage=error?.message||String(error);paint();};
  const ready=()=>{const state=settlementState();return !settlementError(state)&&acknowledged===state.token;};
  const settle=async(options={})=>{
    publicationMessage='';paint();
    try{acknowledged=await settleAssignments(settlementState,notify,options=>services.settle(options),
      {...options,signal:options.signal?AbortSignal.any([lifetime.signal,options.signal]):lifetime.signal});}
    catch(error){if(!disposed&&!options.signal?.aborted)report(error);throw error;}
  };
  root.sourceInput=Object.freeze({value:()=>draft.value,basis:()=>draft.basis,focus:()=>view.focus(),settle,ready});
  draft.persist();paint();if(draft.dirty)queueMicrotask(notify);
  return {settle,ready,report,update(next){
    const before=draft.value,basis=draft.basis;current=next;draft.receive(next);
    if(isReadonly!==!!next.readonly){isReadonly=!!next.readonly;view.dispatch({effects:readonly.reconfigure([EditorState.readOnly.of(isReadonly),EditorView.editable.of(!isReadonly)])});}
    replace();paint();if(before!==draft.value||basis!==draft.basis)queueMicrotask(notify);
  },dispose(){disposed=true;lifetime.abort();draft.persist();download.onclick=discard.onclick=null;view.destroy();delete root.sourceInput;}};
}
