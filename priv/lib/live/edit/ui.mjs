import {computePosition,autoUpdate,offset,flip,shift,inline} from '@floating-ui/dom';
import {icon,iconNames} from './icons.mjs';
import {recoveryMessage} from './settlement.mjs';

const element=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!=null)node.textContent=text;if(tag==='kbd')node.setAttribute('aria-hidden','true');return node;};
const button=(label,glyph,action,className='')=>{
  const node=element('button','ed-button '+className);node.type='button';node.setAttribute('aria-label',label);node.title=label;
  if(glyph)node.append(icon(glyph));if(action)node.addEventListener('click',action);return node;
};
const collapsed=selection=>!selection||(selection.anchor.block===selection.head.block&&selection.anchor.offset===selection.head.offset);

class FloatingSurface {
  constructor(owner,name){
    this.owner=owner;this.editor=owner.editor;this.name=name;this.opened=false;
    this.element=element('div','ed-overlay');this.element.hidden=true;this.element.dataset.editorSurface=name;
    this.element.dataset.theme=this.editor.root.closest('[data-theme]')?.dataset.theme||document.documentElement.dataset.theme||'light';
    (this.editor.options.portal||document.body).append(this.element);
    this.editor.listen(document,'pointerdown',event=>{
      if(this.opened&&!this.element.contains(event.target)&&!this.protect?.contains(event.target))this.hide('outside');
    },{capture:true});
    this.editor.listen(this.element,'keydown',event=>{
      if(event.key==='Escape'){event.preventDefault();event.stopPropagation();this.hide('escape');}
    });
  }
  show(anchor,{placement='top',gap=10,role='dialog',onClose,protect}={}){
    this.cleanup?.();this.anchor=anchor;this.onClose=onClose;this.protect=protect;
    this.element.setAttribute('role',role);this.element.hidden=false;this.opened=true;
    this.cleanup=autoUpdate(anchor,this.element,()=>{
      computePosition(anchor,this.element,{strategy:'fixed',placement,middleware:[offset(gap),inline(),flip({padding:12}),shift({padding:12})]})
        .then(({x,y,placement})=>{if(!this.opened)return;this.element.style.left=x+'px';this.element.style.top=y+'px';this.element.dataset.placement=placement;});
    });
  }
  hide(reason='close'){
    if(!this.opened)return;this.opened=false;this.cleanup?.();this.cleanup=null;this.element.hidden=true;
    const callback=this.onClose;this.onClose=null;callback?.(reason);
  }
  dispose(){this.hide('dispose');this.element.remove();}
}
export class SurfaceHost {
  constructor(editor){this.editor=editor;this.owned=new Map();}
  create(name){if(this.owned.has(name))throw Error('Surface already registered: '+name);const view=new FloatingSurface(this,name);this.owned.set(name,view);return view;}
  register(name,definition){
    const view=this.create(name),editor=this.editor;let target;
    const update=()=>{
      if(!view.opened)return;const content=definition.render(editor.state,editor.public);
      view.element.replaceChildren(content instanceof Node?content:editor.services.render(content));
    };
    const unsubscribe=editor.subscribe(state=>state.clock,()=>{
      if(definition.when){if(definition.when(editor.state,editor.public)){if(!view.opened)show();else update();}else view.hide();}
      else update();
    },{immediate:false});
    const show=token=>{
      if(view.opened)view.hide('replace');
      target=token||editor.capture();update();
      const anchor=typeof definition.anchor==='function'?definition.anchor(editor.public,target):editor.geometry.anchor(target);
      view.show(anchor,{placement:definition.placement||'top',role:definition.role||'toolbar',onClose:()=>{editor.session.release(target);target=null;}});
      update();
    };
    editor.listen(view.element,'mousedown',event=>{if(event.target.closest('button'))event.preventDefault();});
    editor.listen(view.element,'click',event=>{const control=event.target.closest('[data-editor-command]');if(control)editor.run(control.dataset.editorCommand,{}, {target});});
    return Object.freeze({show,hide:()=>view.hide(),dispose:()=>{unsubscribe();view.dispose();this.owned.delete(name);}});
  }
  dispose(){for(const view of this.owned.values())view.dispose();this.owned.clear();}
}
export function createDefaultUI(editor){return new DefaultUI(editor);}
class DefaultUI {
  constructor(editor){
    this.editor=editor;this.root=editor.root;this.token=null;this.pointerSelecting=false;this.dialogs=new Set();
    this.bubble=editor.surfaces.create('selection');this.bubble.element.classList.add('ed-selection-toolbar');this.bubble.element.setAttribute('aria-label','Text formatting');
    this.panel=editor.surfaces.create('context');this.panel.element.classList.add('ed-context-panel');
    this.chip=editor.surfaces.create('function');this.chip.element.classList.add('ed-function-chip');
    this.palette=element('dialog','ed-command-dialog');this.palette.setAttribute('aria-label','Search actions');this.root.append(this.palette);
    this.mobile=element('div','ed-mobile-toolbar');this.mobile.setAttribute('role','toolbar');this.mobile.setAttribute('aria-label','Text formatting');this.root.append(this.mobile);
    this.buildHeader();this.buildToolbar(this.bubble.element);this.buildToolbar(this.mobile,true);
    this.conflict=element('section','ed-conflict');this.conflict.hidden=true;this.conflict.setAttribute('aria-label','Retained draft');this.root.prepend(this.conflict);
    this.editor.listen(this.root,'mousedown',event=>{if(event.target.closest('[data-node-menu],[data-node-add],[data-node-icon],[data-node-check]')){editor.rememberSelection();event.preventDefault();}});
    this.editor.listen(this.bubble.element,'mousedown',event=>{if(event.target.closest('button'))event.preventDefault();});
    this.editor.listen(this.mobile,'mousedown',event=>{if(event.target.closest('button'))event.preventDefault();});
    this.editor.listen(this.root,'click',event=>this.blockAction(event));
    this.editor.listen(editor.canvas,'pointerdown',()=>{this.pointerSelecting=true;this.hideSelection();});
    this.editor.listen(document,'pointerup',()=>{if(this.pointerSelecting){this.pointerSelecting=false;requestAnimationFrame(()=>{editor.rememberSelection();this.update(editor.state);});}});
    this.editor.listen(document,'keydown',event=>{
      if((event.ctrlKey||event.metaKey)&&event.shiftKey&&event.key.toLowerCase()==='p'){
        if(this.root.contains(document.activeElement)||this.panel.element.contains(document.activeElement)){event.preventDefault();this.commandPalette();}
      }
    });
    this.editor.listen(this.palette,'close',()=>{if(this.paletteToken)editor.session.release(this.paletteToken);this.paletteToken=null;editor.geometry.restore(editor.state.selection,{focus:true});});
    const viewport=window.visualViewport;
    if(viewport){const place=()=>this.mobile.style.bottom=Math.max(0,innerHeight-viewport.offsetTop-viewport.height)+'px';editor.listen(viewport,'resize',place);editor.listen(viewport,'scroll',place);place();}
    this.update(editor.state);
  }
  buildHeader(){
    this.nav=element('div','ed-appbar');
    const breadcrumb=element('div','ed-breadcrumb'),brand=element('span','ed-brand');brand.append(icon('sparkles'),element('span','',this.editor.model.appearance?.brand||'Enchant'));
    breadcrumb.append(brand,element('span','ed-breadcrumb-separator','/'),element('span','ed-breadcrumb-space',this.editor.model.appearance?.space||'Field notes'));
    const actions=element('div','ed-appbar-actions');this.save=element('span','ed-save-indicator');this.saveDot=element('i','ed-save-dot');this.save.append(this.saveDot,element('span','ed-save-label','Saved'));
    const search=button('Search actions','search',()=>this.commandPalette());search.append(element('span','ed-search-label','Search actions'));
    const searchGroup=element('div','ed-search-action');searchGroup.append(search,element('kbd','','⇧ P'));
    const exportButton=button('Export document','more',()=>this.documentMenu(exportButton));
    actions.append(this.save,searchGroup,exportButton);this.nav.append(breadcrumb,actions);this.root.prepend(this.nav);
    this.header=element('header','ed-document-header');const top=element('div','ed-document-eyebrow');
    top.append(element('span','ed-eyebrow',this.editor.model.appearance?.label||'A SPACE TO THINK'));
    this.documentIcon=button('Change page icon',this.editor.state.meta.icon||'sparkles',()=>this.iconPicker());this.documentIcon.classList.add('ed-document-icon');
    this.title=element('textarea','ed-document-title');this.title.rows=1;this.title.setAttribute('aria-label','Document title');this.title.spellcheck=false;this.title.placeholder='Untitled';this.title.value=this.editor.state.meta.title||'';
    const resize=()=>{this.title.style.height='auto';this.title.style.height=this.title.scrollHeight+'px';};
    this.editor.listen(this.title,'input',()=>{resize();this.editor.transaction({op:'document/meta',patch:{title:this.title.value}},{group:'title'});});
    this.editor.listen(this.title,'keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();const id=this.editor.order[0];this.editor.select({anchor:{block:id,offset:0},head:{block:id,offset:0}});}});
    this.titleHeading=element('h1','ed-sr-only',this.title.value||'Untitled');
    this.header.append(top,this.documentIcon,this.titleHeading,this.title);this.root.insertBefore(this.header,this.editor.canvas);requestAnimationFrame(resize);
    document.fonts.ready.then(()=>{if(!this.editor.disposed)resize();});this.editor.listen(window,'resize',resize);
    this.footer=element('div','ed-writing-footer');this.footer.append(element('span','ed-footer-rule'),element('span','','A little space. A world of possibilities.'));
    this.root.insertBefore(this.footer,this.editor.status);
  }
  buildToolbar(container,mobile=false){
    const items=[['text/bold','Bold','bold'],['text/emphasis','Italic','italic'],['text/link','Link','link'],['text/highlight','Highlight','highlighter']];
    for(const [id,label,glyph]of items){
      const control=button(label,glyph,()=>{
        if(id==='text/link'||id==='text/highlight')this.functionPanel(id);else{
          this.editor.run(id,{},this.token?{target:this.token}:{});this.editor.geometry.restore(this.editor.state.selection,{focus:true});this.update(this.editor.state);
        }
      });control.dataset.command=id;control.setAttribute('aria-pressed','false');container.append(control);
    }
    container.append(element('span','ed-toolbar-divider'));
    const functions=button('Enchant functions','function',()=>this.functionsMenu());functions.append(element('span','ed-function-label',mobile?'':'Functions'));container.append(functions);
    if(mobile){const add=button('Insert a block','plus',()=>this.slash());container.prepend(add);}
    for(const control of container.querySelectorAll('button'))control.tabIndex=-1;
    container.querySelector('button').tabIndex=0;
    this.editor.listen(container,'keydown',event=>{
      const buttons=[...container.querySelectorAll('button:not(:disabled)')],at=buttons.indexOf(document.activeElement);
      if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
        event.preventDefault();const index=event.key==='Home'?0:event.key==='End'?buttons.length-1:(at+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;
        for(const b of buttons)b.tabIndex=-1;buttons[index].tabIndex=0;buttons[index].focus();
      }else if(event.key==='Escape'){event.preventDefault();this.hideSelection();this.editor.geometry.restore(this.editor.state.selection,{focus:true});}
    });
  }
  focusToolbar(){this.update(this.editor.state);this.bubble.element.querySelector('button')?.focus();}
  hideSelection(){clearTimeout(this.chipTimer);this.chip.hide();this.bubble.hide();if(this.token){this.editor.session.release(this.token);this.token=null;}}
  update(state){
    const offline=document.documentElement.dataset.live==='0',conflict=state.conflicts.length||this.editor.recoveryFailure;
    const label=this.save.querySelector('.ed-save-label');label.textContent=conflict?'Draft retained':offline?'Offline':state.pending?'Saving…':'Saved';
    this.save.dataset.state=conflict?'conflict':offline?'offline':state.pending?'saving':'saved';this.save.title=this.editor.status.textContent;
    if(this.title.value!==(state.meta.title||'')){this.title.value=state.meta.title||'';this.title.style.height='auto';this.title.style.height=this.title.scrollHeight+'px';}
    this.titleHeading.textContent=state.meta.title||'Untitled';
    this.title.readOnly=!!conflict||!!this.editor.model.readonly;
    if(this.documentIcon.dataset.value!==state.meta.icon){this.documentIcon.replaceChildren(icon(state.meta.icon||'sparkles'));this.documentIcon.dataset.value=state.meta.icon;}
    if(conflict&&!this.conflictShown){
      this.conflictShown=true;this.conflict.hidden=false;this.conflict.replaceChildren(element('div','ed-conflict-symbol','!'));
      const explanation=this.editor.recoveryFailure?'A previous draft could not be restored. Download it before choosing the current document.':recoveryMessage(state.conflicts[0]?.reason);
      const content=element('div');content.append(element('strong','','Your draft is safe.'),element('p','',explanation));
      const download=button('Download retained draft','download',()=>this.editor.download());download.append(element('span','','Download draft'));
      const reload=!!this.editor.recoveryFailure||state.conflicts.some(item=>/outdated/.test(item.reason));
      const label=reload?'Reload with current tools':'Use saved version';
      const confirmed=button(label,null,()=>{
        const removed=reload?this.editor.drafts.discard():this.editor.drafts.remove();
        if(!removed){this.editor.report(Error('The saved draft could not be cleared. Keep the download and try again.'));return;}
        this.editor.recoveryFailure=null;this.editor.message='';
        if(reload)location.reload();else this.editor.run('use-confirmed');});confirmed.append(element('span','',label));
      const actions=element('div','ed-conflict-actions');actions.append(download,confirmed);content.append(actions);this.conflict.append(content);
    }else if(!conflict){this.conflict.hidden=true;this.conflictShown=false;}
    const focus=this.editor.canvas.contains(document.activeElement),touch=matchMedia('(pointer: coarse)').matches;
    this.mobile.dataset.visible=String(touch&&focus&&!conflict&&!this.editor.composing);
    if(this.panel.opened||this.palette.open||this.pointerSelecting||this.editor.composing||conflict){this.hideSelection();return;}
    const selection=state.selection;
    if(!collapsed(selection)&&focus&&!touch){
      // Rendering must not reread DOM selection: capture() can synchronously
      // publish another selection and release the outer update's bookmark.
      const selected=JSON.stringify(selection);
      if(!this.token||this.selectionKey!==selected){
        const previous=this.token;this.token=this.editor.session.bookmark();this.selectionKey=selected;
        if(previous)this.editor.session.release(previous);
      }
      this.bubble.show(this.editor.geometry.anchor(this.token),{role:'toolbar',protect:this.mobile});this.chip.hide();
    }else{
      this.bubble.hide();if(this.token){this.editor.session.release(this.token);this.token=null;}
      clearTimeout(this.chipTimer);this.chip.hide();
      if(focus&&selection&&!touch){const node=this.editor.node(selection.head.block),at=selection.head.offset;
        const call=node?.marks.find(m=>m.from<=at&&at<m.to)?.call||node?.wraps[0];
        if(call)this.chipTimer=setTimeout(()=>{if(this.editor.composing||this.panel.opened||this.editor.disposed)return;
          const spec=this.editor.catalog.find(f=>f.id===call.function);if(!spec)return;
          const control=button('Edit '+spec.label,'function',()=>this.functionPanel(call.function,call));control.append(element('span','',spec.label));
          this.chip.element.replaceChildren(control);this.chip.show(this.editor.geometry.anchor(),{placement:'bottom-start',gap:5});
        },220);
      }
    }
    if(this.bubble.opened||this.mobile.dataset.visible==='true'){
      const commands=this.editor.query(this.token?{target:this.token}:{});
      for(const control of [...this.bubble.element.querySelectorAll('[data-command]'),...this.mobile.querySelectorAll('[data-command]')]){
        const item=commands.find(c=>c.id===control.dataset.command);control.disabled=!item?.enabled;control.setAttribute('aria-pressed',item?.active==='mixed'?'mixed':String(item?.active==='on'));
      }
    }
  }
  panelTarget(){const token=this.token||this.editor.capture();this.token=null;this.bubble.hide();this.chip.hide();this.panel.hide('replace');return token;}
  openPanel(content,token,anchor=null,{focus=null,placement='bottom-start',onClose}={}){
    this.panel.element.replaceChildren(content);this.panel.element.className='ed-overlay ed-context-panel';
    this.panel.show(anchor||this.editor.geometry.anchor(token),{placement,onClose:reason=>{
      this.editor.session.cancelPreview();if(token)this.editor.session.release(token);onClose?.(reason);
      if(reason!=='outside'&&reason!=='replace'&&reason!=='dispose')this.editor.geometry.restore(this.editor.state.selection,{focus:true});
    }});if(focus)requestAnimationFrame(()=>focus.focus());
  }
  currentCall(fid){const selection=this.editor.state.selection;if(!selection)return null;const b=this.editor.node(selection.head.block),at=selection.head.offset;
    return [...(b?.wraps||[]),...(b?.marks.filter(m=>m.from<=at&&at<=m.to).map(m=>m.call)||[])].find(call=>call.function===fid)||null;}
  functionPanel(fid,existing=null){
    const spec=this.editor.catalog.find(item=>item.id===fid);if(!spec)return;
    const token=this.panelTarget(),call=existing||this.currentCall(fid),params=spec.params||{},args={};
    for(const [key,param]of Object.entries(params))args[key]=call?.args[key]??param.default;
    const content=element('form','ed-function-form'),heading=element('div','ed-panel-heading');heading.append(icon(spec.icon||'function'),element('strong','',spec.label));
    const close=button('Close','close',()=>this.panel.hide('close'));heading.append(close);content.append(heading,element('p','ed-panel-description',call?'Make this function your own.':'A small change, a new possibility.'));
    const error=element('div','ed-panel-error');error.setAttribute('role','status');
    const preview=()=>{try{
      if(call)this.editor.session.previewOperation({op:'call/args',id:call.id,expected:call.args,args:{...args}});
      else this.editor.session.preview(fid,{...args},{target:token});error.textContent='';apply.disabled=false;
    }catch(reason){error.textContent=this.friendly(reason);apply.disabled=true;}};
    for(const [key,param]of Object.entries(params)){
      const field=element(param.type==='enum'?'div':'label','ed-parameter');field.append(element('span','ed-field-label',key==='tone'?'Color':key==='href'?'Destination':key));
      if(param.type==='enum'){
        const group=element('div','ed-value-choices');group.setAttribute('role','radiogroup');group.setAttribute('aria-label',key);
        for(const value of param.values){const choice=button(value,null,()=>{args[key]=value;for(const c of group.children)c.setAttribute('aria-checked',String(c===choice));preview();},'ed-value-choice');choice.dataset.tone=value;choice.setAttribute('role','radio');choice.setAttribute('aria-checked',String(args[key]===value));choice.append(element('span','ed-color-dot'),element('span','',value[0].toUpperCase()+value.slice(1)));group.append(choice);}
        field.append(group);
      }else{
        const input=element('input','ed-field');input.type=param.type==='boolean'?'checkbox':param.type==='integer'?'number':'text';input.setAttribute('aria-label',key);
        if(input.type==='checkbox')input.checked=!!args[key];else input.value=String(args[key]??'');if(key==='href')input.placeholder='https://example.com';
        if(param.min!=null)input.min=param.min;if(param.max!=null)input.max=param.max;
        input.addEventListener('input',()=>{args[key]=input.type==='checkbox'?input.checked:input.type==='number'?Number(input.value):input.value;preview();});field.append(input);
      }content.append(field);
    }
    if(!Object.keys(params).length)content.append(element('p','ed-panel-description',call?'This function is applied to your text.':'Preview this function on the selected text.'));
    content.append(error);const actions=element('div','ed-panel-actions');
    if(call){const remove=button('Remove function','trash',()=>{this.editor.session.cancelPreview();this.editor.transaction({op:'call/remove',id:call.id},{target:token});this.panel.hide('apply');});remove.append(element('span','','Remove'));actions.append(remove);}
    const apply=button(call?'Save change':'Apply function',null,()=>{} ,'ed-primary');apply.type='submit';apply.append(element('span','',call?'Save change':'Apply function'),element('kbd','','↵'));actions.append(apply);content.append(actions);
    content.addEventListener('submit',event=>{event.preventDefault();try{if(!this.editor.state.preview)preview();if(apply.disabled)return;this.editor.session.commitPreview();this.panel.hide('apply');}catch(reason){error.textContent=this.friendly(reason);}});
    this.openPanel(content,token,null,{focus:content.querySelector('input')||apply});preview();
  }
  friendly(error){const message=error?.message||String(error);return {'invalid-link':'Enter a web address, email link, or page anchor.','invalid-arguments':'Choose a valid value for this function.','empty-selection':'Select some text to preview this function.'}[message]||message;}
  functionsMenu(){
    const token=this.panelTarget(),content=element('div','ed-function-list');content.append(element('div','ed-menu-label','ENCHANT FUNCTIONS'));
    const selection=this.editor.session.resolve(token),node=selection&&this.editor.node(selection.head.block),at=selection?.head.offset;
    const calls=[...(node?.wraps||[]),...(node?.marks.filter(m=>m.from<=at&&at<=m.to).map(m=>m.call)||[])];
    for(const call of calls){const spec=this.editor.catalog.find(f=>f.id===call.function);if(!spec)continue;
      const row=this.menuRow({...spec,label:'Edit '+spec.label},()=>{this.panel.hide('replace');this.functionPanel(call.function,call);});content.append(row);}
    if(calls.length)content.append(element('div','ed-menu-rule'));
    for(const spec of this.editor.query({target:token}).filter(item=>item.kind==='wrap'||item.kind==='transform')){
      content.append(this.menuRow(spec,()=>{const selection=this.editor.session.resolve(token);this.panel.hide('replace');if(selection)this.editor.select(selection,{focus:false});if(spec.params&&Object.keys(spec.params).length)this.functionPanel(spec.id);else this.editor.run(spec.id);}));
    }
    this.openPanel(content,token);this.keyboardMenu(content);
  }
  menuRow(item,action){
    const row=item.href?element('a','ed-menu-row'):button(item.label,item.icon||'function',action,'ed-menu-row');
    if(item.href){row.href=item.href;row.setAttribute('aria-label',item.label);if(item.download)row.download=item.download===true?'':item.download;row.addEventListener('click',action);}
    if(item.id)row.dataset.command=item.id;row.append(element('span','ed-menu-row-label',item.label));
    if(item.description)row.append(element('span','ed-menu-row-description',item.description));
    if(item.shortcut)row.append(element('kbd','',item.shortcut.replace('Mod-','⌘ ').replace('Shift-','⇧ ')));
    row.disabled=item.enabled===false;row.tabIndex=-1;if(row.disabled)row.title=item.reason||item.label;return row;
  }
  keyboardMenu(container,search=null){
    const move=(delta,edge)=>{const rows=[...container.querySelectorAll('.ed-menu-row:not(:disabled)')];if(!rows.length)return;
      const at=rows.indexOf(document.activeElement),next=edge==='first'?0:edge==='last'?rows.length-1:(at+delta+rows.length)%rows.length;rows[next].focus();rows[next].scrollIntoView({block:'nearest'});};
    container.addEventListener('keydown',event=>{if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();move(event.key==='ArrowDown'?1:-1);}else if(event.key==='Home'){event.preventDefault();move(0,'first');}else if(event.key==='End'){event.preventDefault();move(0,'last');}});
    if(search)search.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();container.querySelector('.ed-menu-row:not(:disabled)')?.click();}});
  }
  openSearch(mode='all',blockId=null){
    if(!this.editor.state.selection){const id=blockId||this.editor.order[0];this.editor.select({anchor:{block:id,offset:0},head:{block:id,offset:0}},{focus:false});}
    if(blockId)this.editor.select({anchor:{block:blockId,offset:0},head:{block:blockId,offset:0}},{focus:false});
    const token=this.panelTarget(),content=element('div','ed-search-menu');
    const searchLine=element('div','ed-search-line');searchLine.append(icon('search'));const search=element('input','ed-menu-search');search.type='search';search.placeholder=mode==='insert'?'What would you like to add?':'Search actions…';search.setAttribute('aria-label',mode==='insert'?'Search blocks':'Search actions');searchLine.append(search);
    const list=element('div','ed-menu-results');content.append(searchLine,list,element('div','ed-menu-help','↑↓ Navigate   ↵ Choose   esc Close'));
    const render=()=>{
      const query=search.value.toLowerCase(),items=this.editor.query({target:token}).filter(item=>mode!=='insert'||(item.kind==='insert'||item.menu==='insert'));
      const score=item=>{const text=(item.label+' '+(item.description||'')+' '+item.id).toLowerCase();if(!query)return 1;if(text.includes(query))return 100-text.indexOf(query);let at=0;for(const c of text)if(c===query[at])at++;return at===query.length?1:0;};
      const results=items.map(item=>({item,score:score(item)})).filter(row=>row.score>0).sort((a,b)=>b.score-a.score).slice(0,30);list.replaceChildren();
      for(const {item}of results)list.append(this.menuRow(item,()=>{
        const selected=this.editor.session.resolve(token);this.panel.hide('choose');
        if(selected)this.editor.select(selected,{focus:false});
        if(item.params&&Object.keys(item.params).length)this.functionPanel(item.id);else{this.editor.run(item.id,{});this.editor.geometry.restore(this.editor.state.selection,{focus:true});}
      }));
      if(!results.length)list.append(element('p','ed-empty-results','No matching actions. Try another word.'));
    };
    search.addEventListener('input',render);this.openPanel(content,token,null,{focus:search});this.panel.element.classList.add('ed-insertion-panel');this.keyboardMenu(content,search);render();
  }
  slash(blockId=null){this.openSearch('insert',blockId);}
  commandPalette(){
    this.hideSelection();this.panel.hide('replace');this.paletteToken=this.editor.capture();
    if(!this.editor.state.selection){const id=this.editor.order[0];this.editor.select({anchor:{block:id,offset:0},head:{block:id,offset:0}},{focus:false});this.editor.session.release(this.paletteToken);this.paletteToken=this.editor.capture();}
    const content=element('div','ed-search-menu ed-palette-content'),line=element('div','ed-search-line');line.append(icon('search'));
    const search=element('input','ed-menu-search');search.type='search';search.placeholder='What would you like to do?';search.setAttribute('aria-label','Search actions');line.append(search,element('kbd','','esc'));
    const results=element('div','ed-menu-results');content.append(line,results,element('div','ed-menu-help','Your words. Your tools. One place.'));this.palette.replaceChildren(content);
    const render=()=>{const query=search.value.toLowerCase();results.replaceChildren();
      for(const item of this.editor.query({target:this.paletteToken}).filter(item=>(item.label+' '+item.id).toLowerCase().includes(query)).slice(0,30)){
        results.append(this.menuRow(item,()=>{const target=this.paletteToken;const selection=this.editor.session.resolve(target);this.palette.close();if(selection)this.editor.select(selection,{focus:false});
          if(item.params&&Object.keys(item.params).length)this.functionPanel(item.id);else this.editor.run(item.id);
        }));}
    };
    search.addEventListener('input',render);this.keyboardMenu(content,search);render();this.palette.showModal();search.focus();
  }
  blockAction(event){
    const action=event.target.closest('[data-node-add],[data-node-menu],[data-node-icon],[data-node-check],[data-node-media]');if(!action)return;
    const id=action.dataset.nodeAdd||action.dataset.nodeMenu||action.dataset.nodeIcon||action.dataset.nodeCheck||action.dataset.nodeMedia;
    const old=this.editor.state.selection;if(!old||old.head.block!==id)this.editor.select({anchor:{block:id,offset:0},head:{block:id,offset:0}},{focus:false});
    if(action.dataset.nodeAdd)this.slash(id);
    else if(action.dataset.nodeIcon)this.iconPicker(id);
    else if(action.dataset.nodeCheck){const b=this.editor.node(id);this.editor.transaction({op:'node/set',block:id,patch:{attrs:{...b.attrs,checked:!b.attrs.checked}},expected:{attrs:b.attrs}});}
    else if(action.dataset.nodeMedia)this.mediaPanel(id,action);
    else this.blockMenu(id,action);
  }
  blockMenu(id,anchor){
    const token=this.panelTarget(),content=element('div','ed-block-menu'),type=this.editor.node(id)?.type||'block';
    content.append(element('div','ed-menu-label',type.replaceAll('-',' ').toUpperCase()));
    const items=this.editor.query({target:token}),custom=items.filter(item=>item.menu==='block'&&item.enabled);
    const ordinary=items.filter(item=>(item.kind==='turn'||item.kind==='block')&&(!custom.length||item.enabled));
    for(const item of [...custom,...ordinary])content.append(this.menuRow(item,()=>{
      const selection=this.editor.session.resolve(token);this.panel.hide('choose');if(selection)this.editor.select(selection,{focus:false});
      if(item.params&&Object.keys(item.params).length)this.functionPanel(item.id);
      else{this.editor.run(item.id);this.editor.geometry.restore(this.editor.state.selection,{focus:true});}
    }));this.openPanel(content,token,anchor);this.keyboardMenu(content);
  }
  iconPicker(id=null){
    const token=this.panelTarget(),content=element('div','ed-icon-picker');content.append(element('div','ed-menu-label','CHOOSE AN ICON'));
    const grid=element('div','ed-icon-grid');for(const name of iconNames){const control=button(name.replaceAll('-',' '),name,()=>{
      if(id){const node=this.editor.node(id);this.editor.transaction({op:'node/set',block:id,patch:{attrs:{...node.attrs,icon:name}},expected:{attrs:node.attrs}});}
      else this.editor.transaction({op:'document/meta',patch:{icon:name},expected:{icon:this.editor.state.meta.icon}});
      this.panel.hide('choose');
    });grid.append(control);}content.append(grid);this.openPanel(content,token,id?this.editor.geometry.blockAnchor(id):this.documentIcon);
  }
  mediaPanel(id,anchor){
    const token=this.panelTarget(),node=this.editor.node(id),image=node.type==='image',content=element('form','ed-function-form');
    content.append(element('strong','',image?'Add an image':'Add a bookmark'));const field=element('input','ed-field');field.type='url';field.setAttribute('aria-label',image?'Image address':'Bookmark address');field.placeholder='https://…';field.value=(image?node.attrs.src:node.attrs.href)||'';field.required=true;
    const apply=button('Save address',null,null,'ed-primary');apply.type='submit';apply.append(element('span','','Save address'));content.append(field,apply);
    content.addEventListener('submit',event=>{event.preventDefault();if(!field.reportValidity())return;
      this.editor.transaction({op:'node/set',block:id,patch:{attrs:{...node.attrs,[image?'src':'href']:field.value}},expected:{attrs:node.attrs}});this.panel.hide('choose');
    });this.openPanel(content,token,anchor,{focus:field});
  }
  documentMenu(anchor){
    const token=this.panelTarget(),content=element('div','ed-document-menu');
    for(const item of (this.editor.model['document-actions']||[
      {label:'Download Enchant source',icon:'download',action:()=>this.editor.download()},
      {label:'Export Markdown',icon:'text',action:()=>this.editor.download('markdown')},
      {label:'View source',icon:'code',action:()=>this.source()},
      {label:'Switch appearance',icon:'moon',action:()=>{const value=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=value;for(const view of this.editor.surfaces.owned.values())view.element.dataset.theme=value;localStorage.setItem('enchant.edit.theme',value);}},
    ]))content.append(this.menuRow(item,()=>{this.panel.hide('choose');item.action?.();}));this.openPanel(content,token,anchor);
  }
  source(){
    const dialog=element('dialog','ed-source-dialog');dialog.setAttribute('aria-label','Document source');
    const header=element('div','ed-panel-heading');header.append(element('strong','','Document source'),button('Close source','close',()=>dialog.close()));
    const basis=this.editor.session.export();const field=element('textarea','ed-source-field');field.setAttribute('aria-label','Enchant document source');field.spellcheck=false;field.value=JSON.stringify(basis,null,2);
    const error=element('p','ed-panel-error');error.setAttribute('role','status');const apply=button('Apply source',null,()=>{
      try{const document=JSON.parse(field.value);if(this.editor.transaction({op:'document/replace',document,expected:basis}))dialog.close();else error.textContent='The document changed while source was open. Review the current document before applying this source.';}catch(reason){error.textContent='Enter a valid Enchant document. '+this.friendly(reason);}
    },'ed-primary');apply.append(element('span','','Apply source'));
    const actions=element('div','ed-panel-actions');actions.append(button('Download source','download',()=>this.editor.download()),apply);dialog.append(header,field,error,actions);document.body.append(dialog);this.dialogs.add(dialog);this.editor.listen(dialog,'close',()=>{this.dialogs.delete(dialog);dialog.remove();this.editor.geometry.restore(this.editor.state.selection,{focus:true});});dialog.showModal();field.focus();
  }
  report(message){this.editor.status.textContent=message;}
  dispose(){for(const dialog of this.dialogs){dialog.close();dialog.remove();}this.dialogs.clear();clearTimeout(this.chipTimer);this.palette.close();this.palette.remove();this.nav.remove();this.header.remove();this.footer.remove();this.mobile.remove();this.conflict.remove();}
}
