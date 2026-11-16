// Generic CodeMirror text input; source semantics and writes remain in BL.
import {EditorState,Compartment,Transaction} from '@codemirror/state';
import {EditorView,keymap,lineNumbers,drawSelection,highlightSpecialChars} from '@codemirror/view';
import {defaultKeymap,history,historyKeymap,indentWithTab} from '@codemirror/commands';
import {syntaxHighlighting,bracketMatching} from '@codemirror/language';
import {language,highlight} from './code.mjs';
import {TextDraft,TextDraftStore} from './text-draft.mjs';
export function mountSourceInput(root,model,services){
  let current=model,disposed=false,internal=false;
  // Access to storage itself can throw in a restricted browsing context.
  let store;try{store=new TextDraftStore(model.resource);}catch(error){store={warning:error,read:()=>null,write:()=>false,remove:()=>{}};}
  const draft=new TextDraft(model,store),readonly=new Compartment();
  root.replaceChildren();
  const container=document.createElement('div'),footer=document.createElement('div'),status=document.createElement('p');
  footer.className='ed-source-footer';status.setAttribute('role','status');status.setAttribute('aria-live','polite');footer.append(status);
  const download=document.createElement('button'),discard=document.createElement('button');
  download.type=discard.type='button';download.textContent='Download draft';discard.textContent='Use current source';
  footer.append(download,discard);root.append(container,footer);
  const notify=()=>{if(!disposed)services.dispatch(current.event,{value:draft.value,basis:draft.basis});};
  const paint=()=>{
    root.dataset.dirty=String(draft.dirty);root.dataset.stale=String(draft.stale);
    status.textContent=store.warning?'Recovery storage is unavailable. Download your draft before leaving.':draft.stale?'Source changed. Your draft is kept; compare before saving.':draft.dirty?(draft.restored?'Recovered source draft':'Unsaved source draft'):'Saved source';
    download.hidden=!draft.dirty&&!store.warning;discard.hidden=!draft.dirty;
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
      draft.edit(update.state.doc.toString());paint();notify();
    }),
  ]})});
  const replace=()=>{if(view.state.doc.toString()===draft.value)return;internal=true;try{view.dispatch({changes:{from:0,to:view.state.doc.length,insert:draft.value},annotations:Transaction.addToHistory.of(false)});}finally{internal=false;}};
  download.onclick=()=>{
    const url=URL.createObjectURL(new Blob([draft.value],{type:'text/plain;charset=utf-8'})),a=document.createElement('a');
    a.href=url;a.download=model.filename||'draft.org';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  discard.onclick=()=>{draft.discard();replace();paint();notify();};
  root.sourceInput=Object.freeze({value:()=>draft.value,basis:()=>draft.basis,focus:()=>view.focus()});
  draft.persist();paint();if(draft.dirty)queueMicrotask(notify);
  return {update(next){
    const before=draft.value,basis=draft.basis;current=next;draft.receive(next);
    view.dispatch({effects:readonly.reconfigure([EditorState.readOnly.of(!!next.readonly),EditorView.editable.of(!next.readonly)])});
    replace();paint();if(before!==draft.value||basis!==draft.basis)queueMicrotask(notify);
  },dispose(){disposed=true;draft.persist();download.onclick=discard.onclick=null;view.destroy();delete root.sourceInput;}};
}
