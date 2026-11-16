export const FRAGMENT_MIME='application/x-enchant-fragment+json';
const chars=text=>Array.from(text).length;
const base=(id,type='paragraph',text='',attrs={},parent=null)=>({id,type,text,attrs,parent,slot:'body',marks:[],wraps:[]});
const safeUrl=value=>/^(https?:\/\/|mailto:|\/|#)/i.test(value||'')?value:'';
const escapes=text=>String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function importHTML(html){
  if(html.length>2*1024*1024)throw Error('Paste a smaller section at a time.');
  const document=new DOMParser().parseFromString(html,'text/html'),blocks=[];let sequence=0;
  const identity=()=>`import/${sequence++}`;
  function inline(nodes){
    let text='',marks=[];
    function visit(node){
      if(node.nodeType===Node.TEXT_NODE){text+=node.data;return;}
      if(node.nodeType!==Node.ELEMENT_NODE||['SCRIPT','STYLE','NOSCRIPT','IFRAME','OBJECT','SVG','TEMPLATE'].includes(node.tagName))return;
      if(node.tagName==='BR'){text+='\n';return;}
      if(['UL','OL'].includes(node.tagName))return;
      const from=chars(text);for(const child of node.childNodes)visit(child);const to=chars(text);if(from===to)return;
      const fid=({B:'text/bold',STRONG:'text/bold',I:'text/emphasis',EM:'text/emphasis',U:'text/underline',S:'text/strike',DEL:'text/strike',CODE:'text/code',MARK:'text/highlight',A:'text/link'})[node.tagName];
      const args=fid==='text/link'?{href:safeUrl(node.getAttribute('href'))}:fid==='text/highlight'?{tone:'amber'}:{};
      if(fid&&(fid!=='text/link'||args.href))marks.push({from,to,call:{id:identity(),function:fid,version:1,args}});
    }
    for(const node of nodes)visit(node);return {text,marks};
  }
  function emit(element,parent=null,type=null){
    const tag=element.tagName;
    if(['SCRIPT','STYLE','NOSCRIPT','IFRAME','OBJECT','TEMPLATE'].includes(tag))return;
    if(tag==='UL'||tag==='OL'){for(const child of element.children)emit(child,parent,tag==='OL'?'ordered':'bullet');return;}
    if(tag==='IMG'){
      const src=safeUrl(element.getAttribute('src'));if(src)blocks.push(base(identity(),'image','',{src,alt:element.getAttribute('alt')||''},parent));return;
    }
    if(tag==='HR'){blocks.push(base(identity(),'divider','',{},parent));return;}
    if(tag==='PRE'){blocks.push(base(identity(),'code',element.textContent,{language:'text'},parent));return;}
    const known=/^(P|H[1-3]|LI|BLOCKQUOTE|ASIDE)$/.test(tag);
    if(!known&&element.querySelector('p,h1,h2,h3,ul,ol,pre,blockquote,aside,hr,img')){for(const child of element.children)emit(child,parent);return;}
    const kind=type||({H1:'heading',H2:'heading',H3:'heading',BLOCKQUOTE:'quote',ASIDE:'callout'})[tag]||'paragraph';
    const attrs=kind==='heading'?{level:Number(tag[1])}:kind==='callout'?{icon:'lightbulb',tone:'amber'}:{};
    const id=identity(),content=inline(element.childNodes),block={...base(id,kind,'',attrs,parent),...content};
    blocks.push(block);
    for(const child of element.children)if(child.tagName==='UL'||child.tagName==='OL')emit(child,id);
  }
  for(const child of document.body.childNodes){
    if(child.nodeType===Node.TEXT_NODE){if(child.data.trim())blocks.push(base(identity(),'paragraph',child.data));}
    else if(child.nodeType===Node.ELEMENT_NODE)emit(child);
  }
  return blocks.length?blocks:[base(identity())];
}
export function fragmentHTML(blocks){
  function inline(block){
    const points=Array.from(block.text),ends=[...new Set([0,points.length,...block.marks.flatMap(m=>[m.from,m.to])])].sort((a,b)=>a-b);
    let html='';for(let i=0;i<ends.length-1;i++){
      const from=ends[i],to=ends[i+1];let text=escapes(points.slice(from,to).join(''));
      for(const mark of block.marks.filter(m=>m.from<=from&&to<=m.to).toReversed()){
        const fid=mark.call.function,tag=({'text/bold':'strong','text/emphasis':'em','text/underline':'u','text/strike':'s','text/code':'code','text/highlight':'mark','text/link':'a'})[fid]||'span';
        const attrs=tag==='a'?` href="${escapes(safeUrl(mark.call.args.href))}"`:'';text=`<${tag}${attrs}>${text}</${tag}>`;
      }html+=text;
    }return html.replaceAll('\n','<br>');
  }
  return blocks.map(b=>{
    if(b.type==='code')return `<pre><code>${escapes(b.text)}</code></pre>`;
    if(b.type==='divider')return '<hr>';
    if(b.type==='image')return `<img src="${escapes(safeUrl(b.attrs.src))}" alt="${escapes(b.attrs.alt||'')}">`;
    const tag=b.type==='heading'?'h'+Math.max(1,Math.min(3,b.attrs.level||2)):b.type==='quote'?'blockquote':b.type==='callout'?'aside':'p';
    return `<${tag}>${inline(b)}</${tag}>`;
  }).join('');
}
export function markdown(document){
  return document.blocks.map(b=>{
    const text=b.text,prefix=b.type==='heading'?'#'.repeat(Math.max(1,Math.min(3,b.attrs.level||2)))+' ':b.type==='bullet'?'- ':b.type==='ordered'?'1. ':b.type==='task'?(b.attrs.checked?'- [x] ':'- [ ] '):b.type==='quote'?'> ':'';
    if(b.type==='code')return '```'+(b.attrs.language||'')+'\n'+text+'\n```';
    if(b.type==='divider')return '---';if(b.type==='image')return '!['+(b.attrs.alt||'')+']('+b.attrs.src+')';
    return (b.parent?'  ':'')+prefix+text;
  }).join('\n\n')+'\n';
}
