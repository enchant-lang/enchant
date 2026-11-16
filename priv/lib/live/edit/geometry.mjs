// Native positions are an adapter detail; public targets use stable IDs + CPs.
export const codepoints = text => Array.from(text);
export const cpOffset = (text, units) => codepoints(text.slice(0, units)).length;
export const unitOffset = (text, points) => codepoints(text).slice(0, points).join('').length;

// The caret and the browser's inserted data disambiguate equal prefixes.
// A plain longest-prefix diff can otherwise format the wrong repeated letters.
export function nativeReplacement(before,after,{head=null,text}={}) {
  if(before===after)return null;
  const a=codepoints(before),b=codepoints(after);
  if(Number.isInteger(head)&&0<=head&&head<=b.length){
    let from,to,inserted;
    if(typeof text==='string'){
      inserted=text;from=head-codepoints(inserted).length;to=from+a.length-b.length+codepoints(inserted).length;
    }else if(b.length>=a.length){
      from=head-(b.length-a.length);to=from;inserted=b.slice(from,head).join('');
    }else{from=head;to=head+a.length-b.length;inserted='';}
    if(0<=from&&from<=to&&to<=a.length&&a.slice(0,from).join('')+inserted+a.slice(to).join('')===after)
      return {from,to,text:inserted,expected:a.slice(from,to).join('')};
  }
  let from=0,suffix=0;
  while(from<a.length&&from<b.length&&a[from]===b[from])from++;
  while(suffix<a.length-from&&suffix<b.length-from&&a[a.length-suffix-1]===b[b.length-suffix-1])suffix++;
  const to=a.length-suffix;
  return {from,to,text:b.slice(from,b.length-suffix).join(''),expected:a.slice(from,to).join('')};
}

export class Geometry {
  constructor(editor) { this.editor = editor; }
  point(node, offset) {
    const element = node?.nodeType === 1 ? node : node?.parentElement;
    const text = element?.closest('[data-edit-text]');
    if (!text || !this.editor.canvas.contains(text) || element.closest('[data-edit-code]')) return null;
    try {
      const range = document.createRange(); range.selectNodeContents(text); range.setEnd(node, offset);
      return {block: text.dataset.editText, offset: codepoints(range.toString()).length, affinity:'right'};
    } catch { return null; }
  }
  hit({x,y}) {
    if(!Number.isFinite(x)||!Number.isFinite(y))return null;
    const element=document.elementFromPoint(x,y);
    if(!element||!this.editor.canvas.contains(element))return null;
    const code=element.closest('[data-edit-code]');
    if(code)return this.editor.code.get(code.dataset.editCode)?.point(x,y)||null;
    const caret=document.caretPositionFromPoint?.(x,y);
    if(caret)return this.point(caret.offsetNode,caret.offset);
    const range=document.caretRangeFromPoint?.(x,y);
    return range?this.point(range.startContainer,range.startOffset):null;
  }
  read() {
    const code = document.activeElement?.closest('[data-edit-code]');
    if (code && this.editor.canvas.contains(code)) return this.editor.code.get(code.dataset.editCode)?.selection();
    const native = document.getSelection(); if (!native?.rangeCount) return null;
    const anchor = this.point(native.anchorNode, native.anchorOffset), head = this.point(native.focusNode, native.focusOffset);
    return anchor && head ? {anchor, head} : null;
  }
  targetRanges(event) {
    const range = event.getTargetRanges?.()[0]; if (!range) return null;
    const anchor=this.point(range.startContainer,range.startOffset),head=this.point(range.endContainer,range.endOffset);
    return anchor && head ? {anchor,head} : null;
  }
  nativePoint(point) {
    const text = this.editor.textElement(point.block); if (!text) return null;
    const walker = document.createTreeWalker(text,NodeFilter.SHOW_TEXT);let remaining=point.offset,node;
    while ((node=walker.nextNode())) {
      const chars=codepoints(node.data);
      if(remaining<=chars.length) return [node,chars.slice(0,remaining).join('').length];
      remaining-=chars.length;
    }
    return [text,text.childNodes.length];
  }
  restore(selection, {focus=false}={}) {
    if(!selection || this.editor.composing || !this.editor.root.isConnected) return;
    const a=selection.anchor,h=selection.head;
    if(a.deleted || h.deleted) return;
    const code=this.editor.code.get(a.block);
    if(code && a.block===h.block) { code.select(a.offset,h.offset,focus);return; }
    const start=this.nativePoint(a),end=this.nativePoint(h);if(!start || !end)return;
    if(focus)this.editor.canvas.focus({preventScroll:true});
    document.getSelection().setBaseAndExtent(start[0],start[1],end[0],end[1]);
  }
  range(selection) {
    if(!selection || selection.anchor.deleted || selection.head.deleted)return null;
    if(this.editor.code.has(selection.anchor.block))return null;
    const order=this.editor.order;
    const a=selection.anchor,h=selection.head;
    const forward=order.indexOf(a.block)<order.indexOf(h.block) || (a.block===h.block && a.offset<=h.offset);
    const from=this.nativePoint(forward?a:h),to=this.nativePoint(forward?h:a);if(!from || !to)return null;
    try {const range=document.createRange();range.setStart(...from);range.setEnd(...to);return range;}catch{return null;}
  }
  anchor(target=null) {
    const selection=()=>typeof target==='string'?this.editor.session.resolve(target):target || this.editor.state.selection;
    const rects=()=>{
      const s=selection();if(!s)return [];
      const code=this.editor.code.get(s.head.block);
      if(code)return [code.rect(s.head.offset)];
      const range=this.range(s),items=range?[...range.getClientRects()].filter(r=>r.height>0):[];
      if(items.length)return items;
      const el=this.editor.textElement(s.head.block)||this.editor.nodes.get(s.head.block);
      if(!el)return [];
      const r=el.getBoundingClientRect();return [new DOMRect(r.left,r.top,1,Math.min(r.height||24,28))];
    };
    return {contextElement:this.editor.canvas,getClientRects:rects,getBoundingClientRect:()=>{
      const items=rects();if(!items.length)return new DOMRect();
      const left=Math.min(...items.map(r=>r.left)),top=Math.min(...items.map(r=>r.top));
      return new DOMRect(left,top,Math.max(...items.map(r=>r.right))-left,Math.max(...items.map(r=>r.bottom))-top);
    }};
  }
  blockAnchor(id) {
    return {contextElement:this.editor.canvas,getBoundingClientRect:()=>this.editor.nodes.get(id)?.getBoundingClientRect()||new DOMRect()};
  }
}
