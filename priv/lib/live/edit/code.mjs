// CodeMirror is an owned input/view adapter. BL owns document edits and history.
import {EditorState,Compartment,Transaction} from '@codemirror/state';
import {EditorView,keymap,drawSelection,highlightSpecialChars} from '@codemirror/view';
import {defaultKeymap,indentWithTab} from '@codemirror/commands';
import {syntaxHighlighting,HighlightStyle,bracketMatching,indentOnInput,StreamLanguage} from '@codemirror/language';
import {javascript} from '@codemirror/lang-javascript';
import {markdown} from '@codemirror/lang-markdown';
import {tags} from '@lezer/highlight';
import {cpOffset,unitOffset} from './geometry.mjs';
import {CodeService} from './code-service.mjs';

const lisp=StreamLanguage.define({
  startState:()=>({string:false}),
  token(stream,state){
    if(stream.eatSpace())return null;
    if(state.string){let c;while((c=stream.next())!=null){if(c==='\\'){stream.next();continue;}if(c==='"'){state.string=false;break;}}return 'string';}
    if(stream.peek()===';'){stream.skipToEnd();return 'comment';}
    if(stream.eat('"')){state.string=true;return 'string';}
    if(stream.match(/^:[\w/!?*+.-]+/))return 'atom';
    if(stream.match(/^-?\d+(?:\.\d+)?/))return 'number';
    if(stream.match(/^(?:defn-?|def|fn|let|if|when|do|ns|cond|for|true|false|nil)\b/))return 'keyword';
    if(stream.match(/^[\w/!?*+<>.=:-]+/))return 'variableName';
    stream.next();return 'punctuation';
  },languageData:{commentTokens:{line:';'},closeBrackets:{brackets:['(','[','{','"']}}
});
export const highlight=HighlightStyle.define([
  {tag:tags.keyword,color:'var(--ed-code-keyword)'},{tag:tags.atom,color:'var(--ed-code-atom)'},{tag:tags.string,color:'var(--ed-code-string)'},
  {tag:tags.number,color:'var(--ed-code-atom)'},{tag:tags.comment,color:'var(--ed-code-comment)',fontStyle:'italic'},
  {tag:tags.variableName,color:'var(--ed-code-variable)'},{tag:tags.punctuation,color:'var(--ed-code-punctuation)'},
]);
export const language=name=>name==='javascript'?javascript():name==='markdown'?markdown():name==='beam-lisp'?lisp:[];

export class CodeAdapter {
  point(x,y){
    const at=this.view.posAtCoords({x,y});
    return at===null?null:{block:this.id,offset:cpOffset(this.view.state.doc.toString(),at),affinity:'right'};
  }
  constructor(editor,block,container){
    this.editor=editor;this.id=block.id;this.text=block.text;this.language=block.attrs?.language||'text';
    this.internal=false;this.languageSlot=new Compartment();this.readonly=new Compartment();this.serviceSlot=new Compartment();
    this.service=null;
    this.view=new EditorView({parent:container,state:EditorState.create({doc:block.text,extensions:[
      this.languageSlot.of(language(this.language)),this.readonly.of(EditorState.readOnly.of(false)),this.serviceSlot.of([]),
      syntaxHighlighting(highlight),bracketMatching(),indentOnInput(),drawSelection(),highlightSpecialChars(),
      EditorView.contentAttributes.of({'aria-label':'Code block'}),
      EditorView.theme({'&':{fontSize:'13px'},'.cm-content':{fontFamily:'"IBM Plex Mono",monospace',padding:'16px 20px',lineHeight:'1.8'},
        '.cm-gutters':{display:'none'},'&.cm-focused':{outline:'none'},'.cm-cursor':{borderLeftColor:'var(--ed-accent)'},
        '.cm-selectionBackground':{background:'var(--ed-code-selection)!important'},'&.cm-focused .cm-selectionBackground':{background:'var(--ed-code-selection)'}}),
      keymap.of([
        {key:'Mod-z',run:()=>{editor.run('undo');return true;}},
        {key:'Mod-Shift-z',run:()=>{editor.run('redo');return true;}},
        {key:'Mod-y',run:()=>{editor.run('redo');return true;}},
        {key:'ArrowUp',run:view=>view.state.selection.main.head===0&&editor.focusNeighbour(this.id,-1)},
        {key:'ArrowDown',run:view=>view.state.selection.main.head===view.state.doc.length&&editor.focusNeighbour(this.id,1)},
        indentWithTab,...defaultKeymap,
      ]),
      EditorView.updateListener.of(update=>{
        if(this.internal)return;
        if(update.docChanged && !editor.composing && !this.view.composing)this.flush();
        if(update.selectionSet && !editor.composing)editor.rememberSelection();
      }),
    ]})});
    this.view.scrollDOM.tabIndex=0;this.view.scrollDOM.setAttribute('role','region');this.view.scrollDOM.setAttribute('aria-label','Scrollable code block');
    container.querySelector('.ed-code-fallback')?.remove();this.syncService();
  }
  syncService(){
    const provider=this.editor.model['code-service'];
    const enabled=provider&&this.language===(provider.language||'beam-lisp');
    const key=enabled?JSON.stringify(provider):null;if(key===this.serviceKey)return;
    this.serviceKey=key;this.service?.dispose();this.service=enabled?new CodeService(this,provider):null;
    this.view.dispatch({effects:this.serviceSlot.reconfigure(this.service?.extensions()||[])});
    if(this.service)this.view.dom.after(this.service.status);
  }
  selection(){const s=this.view.state.selection.main,text=this.view.state.doc.toString();return {anchor:{block:this.id,offset:cpOffset(text,s.anchor),affinity:'right'},head:{block:this.id,offset:cpOffset(text,s.head),affinity:'right'}};}
  select(anchor,head=anchor,focus=true){
    const text=this.view.state.doc.toString(),a=unitOffset(text,anchor),h=unitOffset(text,head);this.internal=true;
    try{const old=this.view.state.selection.main;if(old.anchor!==a||old.head!==h)this.view.dispatch({selection:{anchor:a,head:h}});if(focus)this.view.focus();}finally{this.internal=false;}
  }
  rect(at){const r=this.view.coordsAtPos(unitOffset(this.view.state.doc.toString(),at));return r?new DOMRect(r.left,r.top,Math.max(1,r.right-r.left),r.bottom-r.top):this.view.dom.getBoundingClientRect();}
  flush(){
    const next=this.view.state.doc.toString();if(next===this.text)return;
    const selection=this.selection();if(this.editor.nativeText(this.id,this.text,next,selection))this.text=next;
  }
  sync(block){
    if(block.text!==this.view.state.doc.toString()){
      this.internal=true;try{this.view.dispatch({changes:{from:0,to:this.view.state.doc.length,insert:block.text},annotations:Transaction.addToHistory.of(false)});}finally{this.internal=false;}
    }
    this.text=block.text;
    const name=block.attrs?.language||'text';if(name!==this.language){this.language=name;this.view.dispatch({effects:this.languageSlot.reconfigure(language(name))});}
  }
  setReadonly(value){this.syncService();if(value===!!this.isReadonly)return;this.isReadonly=value;this.view.dispatch({effects:this.readonly.reconfigure(EditorState.readOnly.of(value))});}
  dispose(){this.service?.dispose();this.view.destroy();}
}
