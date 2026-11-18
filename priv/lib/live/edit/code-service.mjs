// Standard CM provider protocol. Applications supply an authenticated endpoint;
// the adapter only maps Unicode coordinates, renders data and inserts text.
import {autocompletion} from '@codemirror/autocomplete';
import {linter,lintGutter} from '@codemirror/lint';
import {hoverTooltip,keymap} from '@codemirror/view';
import {cpOffset,unitOffset} from './geometry.mjs';
import {CodeRequests} from './code-requests.mjs';

const commands = [
  {operation:'definition', label:'Go to definition', key:'F12'},
  {operation:'references', label:'Find references', key:'Shift-F12'},
  {operation:'actions', label:'Suggested edits', key:'Mod-.'},
];

function button(label, run) {
  const node = document.createElement('button');
  node.type = 'button';
  node.textContent = label;
  node.addEventListener('click', run);
  return node;
}

export class CodeService {
  constructor(adapter,provider){
    this.adapter=adapter;this.requests=new CodeRequests(()=>adapter.view.state.doc.toString(),
      {...provider,context:{...provider.context,block:adapter.id}});
    this.status=document.createElement('span');this.status.className='ed-code-service-status';this.status.setAttribute('role','status');
    this.controls = document.createElement('div');
    this.controls.append(this.status);
    this.commands = commands.filter(({operation}) => provider.tools?.includes(operation));
    this.generation = 0;
    if (this.commands.length) this.mountTools();
  }
  mountTools() {
    this.details = document.createElement('details');
    this.details.className = 'ed-code-tools';
    const summary = document.createElement('summary');
    summary.textContent = 'Code tools';
    const toolbar = document.createElement('div');
    toolbar.className = 'ed-code-tool-buttons';
    for (const {operation,label} of this.commands) {
      if (operation === 'actions' && this.adapter.editor.model.readonly) continue;
      toolbar.append(button(label, () => this.show(operation)));
    }
    this.results = document.createElement('div');
    this.results.className = 'ed-code-tool-results';
    this.results.setAttribute('aria-live', 'polite');
    this.details.append(summary, toolbar, this.results);
    this.controls.append(this.details);
    this.details.addEventListener('keydown', event => {
      if (event.key !== 'Escape') return;
      event.stopPropagation();
      this.details.open = false;
      this.adapter.view.focus();
    });
  }
  async show(operation) {
    if (operation === 'actions' && this.adapter.editor.model.readonly) return;
    const view = this.adapter.view;
    const text = view.state.doc.toString();
    const caret = view.state.selection.main.head;
    const generation = ++this.generation;
    this.details.open = true;
    this.results.textContent = 'Looking up the code at the caret…';
    const result = await this.request(operation, caret);
    if (generation !== this.generation) return;
    this.results.replaceChildren();
    if (!result || view.state.doc.toString() !== text || view.state.selection.main.head !== caret) return;
    if (operation === 'actions') {
      for (const edit of result.actions || []) this.offerEdit(edit, text);
      if (!this.results.childElementCount) this.results.textContent = 'No suggested edits here.';
    } else {
      for (const location of result.locations || []) {
        if (!location.block || !Number.isInteger(location.offset)) continue;
        this.results.append(button(`${location.name} · Org line ${location.line}`, () => this.jump(location)));
      }
      if (!this.results.childElementCount) this.results.textContent = operation === 'definition'
        ? 'No definition in this document.' : 'No referencing functions in this document.';
    }
  }
  jump({block, offset}) {
    const editor = this.adapter.editor.public;
    const node = editor.node(block);
    if (!node || offset < 0 || offset > Array.from(node.text).length) {
      this.results.textContent = 'The code changed. Look up this location again.';
      return;
    }
    const caret = {block, offset, affinity:'right'};
    this.details.open = false;
    editor.selection.set({anchor:caret, head:caret});
  }
  offerEdit(edit, text) {
    if (!Number.isInteger(edit.from) || edit.from < 0 || edit.from > Array.from(text).length
        || typeof edit.insert !== 'string' || typeof edit.title !== 'string') return;
    const preview = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = edit.title;
    const insertion = document.createElement('code');
    insertion.textContent = edit.insert;
    preview.append(title, insertion, button('Apply edit', () => {
      const view = this.adapter.view;
      if (view.state.doc.toString() !== text || this.adapter.editor.model.readonly) {
        this.results.textContent = 'The code changed. Request the suggestion again.';
        return;
      }
      view.dispatch({changes:{from:unitOffset(text, edit.from), insert:edit.insert}});
      this.results.replaceChildren();
      this.details.open = false;
      view.focus();
    }));
    this.results.append(preview);
  }
  async request(operation,position=0){
    try{const answer=await this.requests.request(operation,cpOffset(this.adapter.view.state.doc.toString(),position));this.status.textContent='';return answer;}
    catch(error){if(error.name!=='AbortError')this.status.textContent='Language tools unavailable; your writing is kept.';return null;}
  }
  extensions(){
    const read=()=>this.adapter.view.state.doc.toString();
    return [
      keymap.of(this.commands.map(({operation,key}) => ({key,run:() => {
        if (operation === 'actions' && this.adapter.editor.model.readonly) return false;
        this.show(operation);
        return true;
      }}))),
      autocompletion({override:[async context=>{
        if(this.adapter.editor.model.readonly)return null;
        const word=context.matchBefore(/[\w!?*+<>=:./-]*/);if(!word||(!context.explicit&&!word.text))return null;
        const answer=await this.request('completion',context.pos);if(!answer)return null;
        return {from:unitOffset(read(),answer.from),options:answer.options||[],validFor:/^[\w!?*+<>=:./-]*$/};
      }]}),
      linter(async()=>{
        const answer=await this.request('diagnostics');if(!answer)return [];
        const text=read();return (answer.diagnostics||[]).map(d=>({...d,from:unitOffset(text,d.from),to:unitOffset(text,d.to)}));
      },{delay:650}),lintGutter(),
      hoverTooltip(async(_view,pos)=>{
        const answer=await this.request('hover',pos);if(!answer?.text)return null;
        return {pos:unitOffset(read(),answer.from),end:unitOffset(read(),answer.to),create:()=>{
          const dom=document.createElement('div');dom.className='ed-code-hover';dom.textContent=answer.text;return {dom};
        }};
      }),
    ];
  }
  dispose(){this.generation++;this.requests.dispose();this.controls.remove();}
}
