// Standard CM provider protocol. Applications supply an authenticated endpoint;
// the adapter only maps Unicode coordinates, renders data and inserts text.
import {autocompletion} from '@codemirror/autocomplete';
import {linter,lintGutter} from '@codemirror/lint';
import {hoverTooltip} from '@codemirror/view';
import {cpOffset,unitOffset} from './geometry.mjs';
import {CodeRequests} from './code-requests.mjs';
export class CodeService {
  constructor(adapter,provider){
    this.adapter=adapter;this.requests=new CodeRequests(()=>adapter.view.state.doc.toString(),provider);
    this.status=document.createElement('span');this.status.className='ed-code-service-status';this.status.setAttribute('role','status');
  }
  async request(operation,position=0){
    try{const answer=await this.requests.request(operation,cpOffset(this.adapter.view.state.doc.toString(),position));this.status.textContent='';return answer;}
    catch(error){if(error.name!=='AbortError')this.status.textContent='Language tools unavailable; your writing is kept.';return null;}
  }
  extensions(){
    const read=()=>this.adapter.view.state.doc.toString();
    return [
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
  dispose(){this.requests.dispose();this.status.remove();}
}
