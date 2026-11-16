export {mountFormRecovery} from './form-recovery.mjs';
export {mountSourceInput} from './source-input.mjs';
// Owned DOM/input adapter. Semantic policy and persistent session state are BL.
import {Geometry,codepoints,nativeReplacement} from './geometry.mjs';
import {CodeAdapter} from './code.mjs';
import {projectionParts} from './projection-parts.mjs';
import {DraftStore} from './drafts.mjs';
import {FRAGMENT_MIME,importHTML,fragmentHTML,markdown} from './clipboard.mjs';
import {hydrateIcons} from './icons.mjs';
import {createDefaultUI,SurfaceHost} from './ui.mjs';

const identity=()=>crypto.randomUUID();
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function mount(root,model,services,api,options={}) {
  const editor=new Editor(root,model,services,api,options);
  return {update:next=>editor.update(next),dispose:()=>editor.dispose()};
}
export class Editor {
  constructor(root,model,services,api,options={}){
    this.root=root;this.model=model;this.services=services;this.options=options;
    this.canvas=root.querySelector('[data-edit-canvas]');this.status=root.querySelector('.ed-live-status');
    this.nodes=new Map([...this.canvas.querySelectorAll('[data-edit-block]')].map(el=>[el.dataset.editBlock,el]));
    this.code=new Map();this.shells=new Map();this.listeners=new Set();this.controller=new AbortController();this.signal=this.controller.signal;
    this.geometry=new Geometry(this);this.composing=false;this.disposed=false;this.deferred=null;
    this.sent=null;this.focused=null;this.message='';this.metrics={projected:0,textPatches:0,transactions:0,lastTransactionMs:0};
    this.drafts=new DraftStore(model.resource||`${location.pathname}:${model.snapshot.document.id}`,options.drafts||{});
    const cached=this.drafts.read(),pending=cached?.recovery?.pending?.length||cached?.recovery?.draft;
    const base=pending?cached.checkpoint:model.snapshot;
    this.session=api.create(base);this.checkpoint=base;
    let restored=false;
    if(pending)try{this.session.restore(cached.recovery);this.session.receive(model.snapshot);restored=true;}
      catch(error){this.recoveryFailure=cached;this.message='A previous draft is retained. Download it before choosing the current document.';}
    this.checkpoint=model.snapshot;this.state=this.session.read();this.catalog=this.session.catalog();
    this.current=new Map(model.snapshot.document.blocks.map(b=>[b.id,b]));
    this.layout=this.session.layout();this.order=this.layout.map(b=>b.id);
    this.unsubscribe=this.session.subscribe(change=>this.changed(change));
    this.surfaces=new SurfaceHost(this);
    this.public=this.publicAPI();root.editor=this.public;
    root.enchanted={getState:()=>this.session.debug(),select:(a,h=a)=>this.select({anchor:a,head:h}),command:id=>this.run(id),apply:op=>this.transaction(op)};
    this.canvas.contentEditable=String(!model.readonly);
    if(restored)this.paint({changed:[...new Set([...this.nodes.keys(),...this.order])],structural:true});
    hydrateIcons(root);this.paint({changed:[],structural:true});this.syncCode();this.installInput();
    this.ui=options.ui===false?null:(options.ui||createDefaultUI)(this);
    this.paintStatus();this.persist();this.send();
    root.dispatchEvent(new CustomEvent('enchanted:ready',{bubbles:true,detail:{editor:this.public}}));
  }
  listen(target,type,fn,options={}){target.addEventListener(type,fn,{...options,signal:this.signal});}
  textElement(id){const node=this.nodes.get(id);return [...(node?.querySelectorAll('[data-edit-text]')||[])].find(el=>el.dataset.editText===id);}
  rememberSelection(){
    const active=document.activeElement;
    const selection=(active===this.canvas||this.canvas.contains(active))?this.geometry.read():null;
    if(selection)this.session.selection(selection);return selection||this.state.selection;
  }
  select(selection,{focus=true}={}){this.session.selection(selection);this.geometry.restore(selection,{focus});this.ui?.update?.(this.state);}
  node(id){return this.current.get(id)||this.session.node(id);}
  capture(){this.rememberSelection();return this.session.bookmark();}
  report(error){this.message=error?.message||String(error);this.paintStatus();this.ui?.report?.(this.message);return false;}
  publicAPI(){
    return Object.freeze({
      id:this.model.snapshot.document.id,
      commands:{list:()=>this.catalog,query:options=>this.query(options),run:(id,args={},options={})=>this.run(id,args,options),
        preview:(id,args={},options={})=>{if(this.model.readonly)throw Error('This document is read only.');return this.session.preview(id,args,options);},
        commitPreview:()=>{if(this.model.readonly)throw Error('This document is read only.');return this.session.commitPreview();},cancelPreview:()=>this.session.cancelPreview()},
      selection:{get:()=>this.state.selection,set:(selection,options)=>this.select(selection,options),capture:()=>this.capture(),
        resolve:token=>this.session.resolve(token),release:token=>this.session.release(token)},
      geometry:{hit:position=>this.geometry.hit(position),anchor:target=>this.geometry.anchor(target),block:id=>this.geometry.blockAnchor(id)},
      node:id=>this.session.node(id),transaction:(op,options)=>this.transaction(op,options),
      subscribe:(selector,listener,options)=>this.subscribe(selector,listener,options),
      surfaces:{register:(name,definition)=>this.surfaces.register(name,definition)},
      export:()=>this.session.export(),serialize:()=>JSON.stringify(this.session.export(),null,2)+'\n',
      import:document=>this.transaction({op:'document/replace',document,expected:this.session.export()}),
      metrics:()=>({...this.metrics}),dispose:()=>this.dispose(),
    });
  }
  subscribe(selector,listener,{equals=Object.is,immediate=true}={}){
    let previous=selector(this.state);if(immediate)listener(previous,this.public);
    const update=()=>{const value=selector(this.state);if(!equals(value,previous)){const old=previous;previous=value;listener(value,this.public,old);}};
    this.listeners.add(update);return ()=>this.listeners.delete(update);
  }
  query(options={}){const items=this.session.query(options);return this.model.readonly?items.map(item=>({...item,enabled:false,reason:'This document is read only.'})):items;}
  changed(change){
    if(this.disposed)return;this.state=change;
    const started=performance.now();
    if(!this.localInput&&change.changed.length)this.typing=null;
    if(!this.composing)this.paint(change);
    const projected=performance.now();
    this.paintStatus();for(const listener of this.listeners)listener();
    this.persist();this.send();const persisted=performance.now();this.ui?.update?.(change);
    this.metrics.lastPhases={projection:projected-started,persistence:persisted-projected,ui:performance.now()-persisted};
    this.root.dispatchEvent(new CustomEvent('enchanted:change',{detail:change}));
  }
  paint(change){
    const ids=[...new Set(change.changed||[])];if(!ids.length&&!change.structural)return;
    const selection=this.state.selection,active=document.activeElement;
    const shouldRestore=this.canvas.contains(active)||active===this.canvas;
    const trees=this.session.project(ids);this.metrics.projected+=trees.length;
    for(let i=0;i<ids.length;i++){
      const id=ids[i],tree=trees[i],old=this.nodes.get(id),next=this.session.node(id);
      if(!tree){old?.remove();this.nodes.delete(id);this.current.delete(id);this.shells.delete(id);this.code.get(id)?.dispose();this.code.delete(id);continue;}
      if(old&&same(this.current.get(id),next))continue;
      const parts=projectionParts(tree,id),oldText=old&&this.textElement(id);
      if(next.type!=='code'&&parts.signature&&parts.signature===this.shells.get(id)&&oldText){
        const freshText=this.services.render(parts.text);
        if(!oldText.isEqualNode(freshText))oldText.replaceChildren(...freshText.childNodes);
        this.current.set(id,next);this.metrics.textPatches++;hydrateIcons(oldText);continue;
      }
      this.shells.set(id,parts.signature);const fresh=this.services.render(tree);
      if(old){
        const slots=[...old.querySelectorAll('[data-edit-children]')].filter(el=>el.closest('[data-edit-block]')===old);
        for(const container of slots){const replacement=[...fresh.querySelectorAll('[data-edit-children]')].find(el=>el.dataset.editChildren===container.dataset.editChildren);if(replacement)replacement.append(...container.childNodes);}
        const code=this.code.get(id),codeRoot=fresh.querySelector('[data-edit-code]');
        if(code&&codeRoot){codeRoot.replaceChildren(code.view.dom);code.sync(next);}else if(code){code.dispose();this.code.delete(id);}
        old.replaceWith(fresh);
      }
      this.nodes.set(id,fresh);this.current.set(id,next);hydrateIcons(fresh);
    }
    if(change.structural){
      this.layout=this.session.layout();this.order=this.layout.map(b=>b.id);const live=new Set(this.order);
      for(const [id,node] of this.nodes)if(!live.has(id)){node.remove();this.nodes.delete(id);this.current.delete(id);this.shells.delete(id);this.code.get(id)?.dispose();this.code.delete(id);}
      const positions=new Map();
      for(const row of this.layout){
        const node=this.nodes.get(row.id);if(!node)continue;
        let parent=this.canvas;
        if(row.parent){
          const container=this.nodes.get(row.parent);if(!container)continue;
          parent=[...container.querySelectorAll('[data-edit-children]')].find(el=>el.closest('[data-edit-block]')===container&&el.dataset.editChildren===row.slot);
          if(!parent){parent=document.createElement('div');parent.className='ed-children ed-retained-slot';parent.dataset.editChildren=row.slot;parent.contentEditable='true';container.append(parent);}
        }
        const at=positions.get(parent)||0;if(parent.children[at]!==node)parent.insertBefore(node,parent.children[at]||null);positions.set(parent,at+1);
      }
    }
    this.syncCode(ids);
    if(shouldRestore)this.geometry.restore(selection,{focus:!!active?.closest?.('[data-edit-code]')});
  }
  syncCode(ids=this.nodes.keys()){
    for(const id of ids){const node=this.nodes.get(id);if(!node)continue;
      const container=node.querySelector(`[data-edit-code="${CSS.escape(id)}"]`);if(!container)continue;
      const block=this.node(id);if(!this.code.has(id))this.code.set(id,new CodeAdapter(this,block,container));
    }
  }
  paintStatus(){
    const conflict=this.state.conflicts.length||!!this.recoveryFailure,offline=document.documentElement.dataset.live==='0';
    this.root.dataset.editPending=String(this.state.pending);this.root.dataset.editConflict=String(this.state.conflicts.length);
    this.root.dataset.editRevision=String(this.state.revision);this.canvas.setAttribute('aria-readonly',String(!!conflict||!!this.model.readonly));
    this.canvas.contentEditable=String(!conflict&&!this.model.readonly);
    for(const code of this.code.values())code.setReadonly(!!conflict||!!this.model.readonly);
    const message=this.message||(conflict?'Draft retained — review changes':offline?'Offline · draft on this device':this.state.pending?'Saving…':'All changes saved');
    if(this.status.textContent!==message)this.status.textContent=message;
    this.root.dataset.connection=conflict?'conflict':offline?'offline':this.state.pending?'saving':'saved';
  }
  persist(){
    if(this.disposed||this.recoveryFailure)return;
    if(!this.drafts.write(this.checkpoint,this.session.recovery())&&this.drafts.warning){this.message='Draft storage is unavailable. Download a copy to keep your local changes.';this.paintStatus();}
  }
  send(){
    if(this.disposed||this.composing||this.recoveryFailure||document.documentElement.dataset.live==='0')return;
    const proposal=this.session.outbound();if(!proposal||this.sent===proposal.id)return;
    this.session.markSent();this.persist();this.sent=proposal.id;const term=[this.model.event[0],this.model.event[1],{...(this.model.event[2]||{}),proposal}];
    this.services.dispatch(term,{});
  }
  update(model){
    if(this.disposed)return;
    if(this.composing){this.deferred=model;return;}
    this.model=model;this.rememberSelection();this.checkpoint=model.snapshot;
    try{
      const before=this.session.outbound()?.id;this.session.receive(model.snapshot);
      if(model.refusal?.id)this.session.refuse({ok:false,...model.refusal,snapshot:model.snapshot});
      if(before!==this.session.outbound()?.id)this.sent=null;
      this.persist();this.send();
    }catch(error){this.report(error);}
  }
  transaction(op,options={}){
    if(this.composing||this.disposed)return false;
    if(this.model.readonly)return this.report(Error('This document is read only.'));
    if(this.recoveryFailure)return this.report(Error('Download or dismiss the retained draft first.'));
    this.message='';const t=performance.now();this.localInput=true;
    try{this.session.change(op,options);this.metrics.transactions++;this.metrics.lastTransactionMs=performance.now()-t;return true;}
    catch(error){return this.report(error);}finally{this.localInput=false;}
  }
  run(id,args={},options={}){
    if(this.composing||this.disposed)return false;this.message='';
    if(this.model.readonly&&id!=='use-confirmed')return this.report(Error('This document is read only.'));
    try{if(!options.target)this.rememberSelection();this.session.run(id,args,options);return true;}catch(error){return this.report(error);}
  }
  ordered(selection=this.state.selection){
    if(!selection)throw Error('Place the caret in the document.');const a=selection.anchor,h=selection.head;
    return this.order.indexOf(a.block)<this.order.indexOf(h.block)||(a.block===h.block&&a.offset<=h.offset)?[a,h]:[h,a];
  }
  replace(text,fragment=null,selection=this.rememberSelection()){
    const [from,to]=this.ordered(selection),seed=identity();
    if(from.block===to.block&&!fragment&&!/[\r\n]/.test(text)){
      const end={...from,offset:from.offset+codepoints(text).length};
      const op={op:'text/replace',block:from.block,from:from.offset,to:to.offset,text,styles:this.state.pendingStyles};
      return this.transaction(op,{id:seed,group:this.typingGroup(from.block,from.offset,to.offset,text),selection:{anchor:end,head:end}});
    }
    return this.transaction({op:'range/replace',from,to,seed,...(fragment?{fragment}:{text})},{id:seed});
  }
  nativeText(id,before,after,selection,input=null){
    if(this.composing)return false;
    const head=selection?.anchor.block===id&&selection.head.block===id&&selection.anchor.offset===selection.head.offset?selection.head.offset:null;
    const delta=nativeReplacement(before,after,{head,text:input?.data});if(!delta)return true;
    const group=this.typingGroup(id,delta.from,delta.to,delta.text);
    return this.transaction({op:'text/replace',block:id,...delta,styles:this.node(id)?.type==='code'?[]:this.state.pendingStyles},{group,selection});
  }
  typingGroup(id,from,to,text){
    const now=performance.now(),direction=text?'insert':'delete';
    const continuing=this.typing&&this.typing.block===id&&this.typing.direction===direction&&now-this.typing.time<1000&&
      (direction==='insert'?from===this.typing.end:to===this.typing.end||from===this.typing.end);
    const group=continuing?this.typing.id:identity();this.typing={id:group,block:id,direction,time:now,end:from+codepoints(text).length};
    return group;
  }
  readNative(event){
    const text=event?.target?.closest?.('[data-edit-text]')||this.textElement(this.state.selection?.head.block);
    if(!text||text.closest('[data-edit-code]'))return;
    const id=text.dataset.editText,before=this.node(id)?.text;if(before==null)return;
    this.nativeText(id,before,text.textContent,this.geometry.read(),event);
  }
  focusNeighbour(id,direction){
    const at=this.order.indexOf(id),next=this.order[at+direction];if(!next)return false;
    const block=this.node(next);this.select({anchor:{block:next,offset:direction<0?codepoints(block.text).length:0},head:{block:next,offset:direction<0?codepoints(block.text).length:0}});return true;
  }
  installInput(){
    this.listen(this.canvas,'compositionstart',()=>{this.composing=true;this.root.dataset.editComposing='true';this.ui?.hideSelection?.();});
    this.listen(this.canvas,'compositionend',event=>{
      queueMicrotask(()=>{if(this.disposed)return;this.composing=false;this.root.dataset.editComposing='false';
        const code=event.target.closest?.('[data-edit-code]');if(code)this.code.get(code.dataset.editCode)?.flush();else this.readNative(event);
        if(this.deferred){const next=this.deferred;this.deferred=null;this.update(next);}this.send();});
    });
    this.listen(this.canvas,'input',event=>{if(!this.composing&&!event.isComposing)this.readNative(event);});
    this.listen(this.canvas,'beforeinput',event=>{
      if(this.composing||event.isComposing||event.target.closest?.('.cm-editor'))return;
      if(this.state.conflicts.length||this.recoveryFailure){event.preventDefault();return;}
      if(!event.cancelable)return;
      try{
        const selection=this.geometry.targetRanges(event)||this.geometry.read()||this.state.selection;
        if(!selection){event.preventDefault();return;}this.session.selection(selection);
        const [from,to]=this.ordered(selection),sameBlock=from.block===to.block,collapsed=sameBlock&&from.offset===to.offset;
        const formats={formatBold:'text/bold',formatItalic:'text/emphasis',formatUnderline:'text/underline',formatStrikeThrough:'text/strike'};
        if(event.inputType==='historyUndo'||event.inputType==='historyRedo'){event.preventDefault();this.run(event.inputType==='historyUndo'?'undo':'redo');}
        else if(formats[event.inputType]){event.preventDefault();this.run(formats[event.inputType]);}
        else if(event.inputType.startsWith('format')){event.preventDefault();}
        else if(event.inputType==='insertParagraph'||event.inputType==='insertLineBreak'){
          event.preventDefault();const block=this.node(from.block);
          if(event.inputType==='insertLineBreak'){
            if(sameBlock){const end={...from,offset:from.offset+1};this.transaction({op:'text/replace',block:from.block,from:from.offset,to:to.offset,text:'\n'},{selection:{anchor:end,head:end}});}
            else this.replace('',[{id:'line-break',type:'paragraph',attrs:{},text:'\n',marks:[],wraps:[],parent:null,slot:'body'}],selection);return;
          }
          if(!collapsed){this.replace('\n',null,selection);return;}
          if(!block.text&&['bullet','ordered','task'].includes(block.type)){this.run(block.parent?'block/outdent':'turn/paragraph');return;}
          const next=identity(),type=['bullet','ordered','task'].includes(block.type)?block.type:'paragraph';
          this.transaction({op:'block/split',block:from.block,at:from.offset,new:next,rightMeta:{type,attrs:type==='task'?{checked:false}:block.type===type?block.attrs:{}}},
            {selection:{anchor:{block:next,offset:0},head:{block:next,offset:0}}});
        }else if((!sameBlock&&event.inputType.startsWith('delete'))||(!sameBlock&&event.inputType==='insertText')){event.preventDefault();this.replace(event.data||'',null,selection);}
        else if(event.inputType==='insertReplacementText'&&typeof event.data==='string'){event.preventDefault();this.replace(event.data,null,selection);}
        else if(event.inputType==='insertText'&&this.state.pendingStyles.length){event.preventDefault();this.replace(event.data||'',null,selection);}
        else if(collapsed&&event.inputType.startsWith('delete')&&/(Backward|Forward)$/.test(event.inputType)){
          const i=this.order.indexOf(from.block),block=this.node(from.block),back=event.inputType.endsWith('Backward');
          if((back&&from.offset===0&&i>0)||(!back&&from.offset===codepoints(block.text).length&&i<this.order.length-1)){
            event.preventDefault();if(back&&block.parent){this.run('block/outdent');return;}
            const left=back?this.node(this.order[i-1]):block,right=back?block:this.node(this.order[i+1]);
            const at=codepoints(left.text).length;this.transaction({op:'block/join',left:left.id,right:right.id},{selection:{anchor:{block:left.id,offset:at},head:{block:left.id,offset:at}}});
          }
        }
      }catch(error){event.preventDefault();this.report(error);}
    });
    this.listen(this.canvas,'keydown',event=>{
      if(this.composing||event.isComposing||event.target.closest('.cm-editor'))return;
      const mod=event.ctrlKey||event.metaKey,key=event.key.toLowerCase();
      if(mod&&key==='z'){event.preventDefault();this.run(event.shiftKey?'redo':'undo');return;}
      if(mod&&['b','i','u','e','k'].includes(key)){
        event.preventDefault();const id={b:'text/bold',i:'text/emphasis',u:'text/underline',e:'text/code',k:'text/link'}[key];
        if(key==='k')this.ui?.functionPanel(id);else this.run(id);return;
      }
      if(event.key==='Tab'){event.preventDefault();this.run(event.shiftKey?'block/outdent':'block/indent');}
      if(event.key==='/'&&!mod&&this.state.selection&&this.ordered()[0].offset===0){event.preventDefault();this.ui?.slash();}
      if(event.altKey&&event.key==='ArrowUp'){event.preventDefault();this.run('block/up');}
      if(event.altKey&&event.key==='ArrowDown'){event.preventDefault();this.run('block/down');}
      if(event.key==='F10'&&event.altKey){event.preventDefault();this.ui?.focusToolbar();}
    });
    this.listen(this.canvas,'copy',event=>this.copy(event,false));this.listen(this.canvas,'cut',event=>this.copy(event,true));
    this.listen(this.canvas,'paste',event=>{
      if(this.composing||event.target.closest('.cm-editor'))return;event.preventDefault();
      try{
        const custom=event.clipboardData.getData(FRAGMENT_MIME);if(custom&&custom.length<=1024*1024){const payload=JSON.parse(custom);if(payload.schema==='enchant.fragment/2'||payload.schema==='enchant.fragment/1'){this.replace('',payload.blocks);return;}}
        const html=event.clipboardData.getData('text/html');if(html){this.replace('',importHTML(html));return;}
        const plain=event.clipboardData.getData('text/plain');if(plain)this.replace(plain);
      }catch(error){this.report(error);}
    });
    this.listen(this.canvas,'drop',event=>{
      event.preventDefault();const id=event.dataTransfer.getData('application/x-enchant-block');if(!id)return;
      const target=event.target.closest('[data-edit-block]')?.dataset.editBlock;if(target&&target!==id){const node=this.node(target);this.transaction({op:'node/move',block:id,after:target,parent:node.parent,slot:node.slot});}
    });
    this.listen(this.canvas,'dragstart',event=>{const grip=event.target.closest('[data-node-menu]');if(grip){event.dataTransfer.setData('application/x-enchant-block',grip.dataset.nodeMenu);event.dataTransfer.effectAllowed='move';}});
    this.listen(document,'focusin',event=>{if(this.root.contains(event.target))this.focused=event.target;else if(this.root.isConnected)this.focused=null;});
    this.listen(document,'selectionchange',()=>{
      if(this.selectionFrame||this.composing)return;this.selectionFrame=requestAnimationFrame(()=>{this.selectionFrame=null;if(!this.disposed)this.rememberSelection();});
    });
    this.listen(document,'live:state',event=>{if(event.detail.up){this.sent=null;this.send();}this.paintStatus();this.ui?.update?.(this.state);});
    this.listen(document,'live:mount',()=>{
      if(this.focused?.isConnected){this.focused.focus({preventScroll:true});if(this.canvas.contains(this.focused))this.geometry.restore(this.state.selection);}
      this.sent=null;this.send();this.ui?.update?.(this.state);
    });
    this.listen(window,'pagehide',()=>this.persist());
  }
  copy(event,cut){
    if(this.composing||event.target.closest?.('.cm-editor'))return;
    try{const selection=this.geometry.read();if(!selection)return;const blocks=this.session.fragment(selection);event.preventDefault();
      event.clipboardData.setData('text/plain',blocks.map(b=>b.text).join('\n'));event.clipboardData.setData('text/html',fragmentHTML(blocks));
      event.clipboardData.setData(FRAGMENT_MIME,JSON.stringify({schema:'enchant.fragment/2',blocks}));if(cut)this.replace('',null,selection);
    }catch(error){this.report(error);}
  }
  download(format='json'){
    const doc=this.session.export(),body=this.recoveryFailure?JSON.stringify(this.recoveryFailure,null,2):format==='markdown'?markdown(doc):JSON.stringify(doc,null,2)+'\n';
    const url=URL.createObjectURL(new Blob([body],{type:format==='markdown'?'text/markdown':'application/json'}));
    const a=document.createElement('a');a.href=url;a.download=(doc.meta.title||'Untitled').replaceAll(/[\\/:*?"<>|]/g,'-')+(format==='markdown'?'.md':'.enchant.json');a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  dispose(){
    if(this.disposed)return;this.persist();this.disposed=true;this.controller.abort();this.unsubscribe();
    if(this.selectionFrame)cancelAnimationFrame(this.selectionFrame);
    this.ui?.dispose?.();this.surfaces.dispose();for(const code of this.code.values())code.dispose();this.code.clear();
    this.listeners.clear();this.shells.clear();this.session.dispose();this.canvas.contentEditable='false';delete this.root.editor;delete this.root.enchanted;
  }
}
