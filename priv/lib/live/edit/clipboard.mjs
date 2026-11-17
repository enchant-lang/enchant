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
    if(tag==='TABLE'){
      if(element.querySelector('table'))throw Error('Nested tables cannot be pasted as editable cells.');
      const rows=[...element.rows];if(!rows.length||rows.length>256)throw Error('Paste a table with 1 to 256 rows.');
      const width=Math.max(...rows.map(row=>row.cells.length));if(!width||width>32)throw Error('Paste at most 32 columns.');
      if(rows.some(row=>row.cells.length!==width||[...row.cells].some(cell=>cell.rowSpan!==1||cell.colSpan!==1)))
        throw Error('Paste a rectangular table without merged cells.');
      const header=[...rows[0].cells].every(cell=>cell.tagName==='TH'),table=base(identity(),'table','',{rows:rows.length,columns:width,header},parent);
      blocks.push(table);
      rows.forEach((row,r)=>{const id=identity(),isHeader=header&&r===0;
        blocks.push({...base(id,'table-row','',{header:isHeader},table.id),slot:'rows'});
        for(const cell of row.cells){const content=inline(cell.childNodes),align=cell.style.textAlign||cell.getAttribute('align');
          blocks.push({...base(identity(),'table-cell','',{header:isHeader,align:['left','center','right'].includes(align)?align:'left'},id),slot:'cells',...content});}
      });return;
    }
    if(tag==='IMG'){
      const src=safeUrl(element.getAttribute('src'));if(src)blocks.push(base(identity(),'image','',{src,alt:element.getAttribute('alt')||''},parent));return;
    }
    if(tag==='HR'){blocks.push(base(identity(),'divider','',{},parent));return;}
    if(tag==='PRE'){blocks.push(base(identity(),'code',element.textContent,{language:'text'},parent));return;}
    const known=/^(P|H[1-3]|LI|BLOCKQUOTE|ASIDE)$/.test(tag);
    if(!known&&element.querySelector('p,h1,h2,h3,ul,ol,pre,blockquote,aside,hr,img,table')){for(const child of element.children)emit(child,parent);return;}
    const check=tag==='LI'?[...element.children].find(child=>child.tagName==='INPUT'&&child.type==='checkbox'):null;
    const kind=check?'task':type||({H1:'heading',H2:'heading',H3:'heading',BLOCKQUOTE:'quote',ASIDE:'callout'})[tag]||'paragraph';
    const attrs=check?{checked:check.checked}:kind==='heading'?{level:Number(tag[1])}:kind==='callout'?{icon:'lightbulb',tone:'amber'}:{};
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
  const children=new Map();for(const block of blocks){const list=children.get(block.parent)||[];list.push(block);children.set(block.parent,list);}
  function render(b){
    if(b.type==='table')return '<table>'+ (children.get(b.id)||[]).map(render).join('')+'</table>';
    if(b.type==='table-row')return '<tr>'+(children.get(b.id)||[]).map(render).join('')+'</tr>';
    if(b.type==='table-cell'){const tag=b.attrs.header?'th':'td',align=['left','center','right'].includes(b.attrs.align)?b.attrs.align:'left';return `<${tag} style="text-align:${align}">${inline(b)}</${tag}>`;}
    if(b.type==='code')return `<pre><code>${escapes(b.text)}</code></pre>`;
    if(b.type==='divider')return '<hr>';
    if(b.type==='image')return `<img src="${escapes(safeUrl(b.attrs.src))}" alt="${escapes(b.attrs.alt||'')}">`;
    const tag=b.type==='heading'?'h'+Math.max(1,Math.min(3,b.attrs.level||2)):b.type==='quote'?'blockquote':b.type==='callout'?'aside':'p';
    return `<${tag}>${inline(b)}${renderRows(children.get(b.id)||[])}</${tag}>`;
  }
  function renderRows(rows){
    let html='',list=null;
    const close=()=>{if(list){html+=`</${list}>`;list=null;}};
    for(const b of rows){
      if(['bullet','ordered','task'].includes(b.type)){
        const tag=b.type==='ordered'?'ol':'ul';if(list!==tag){close();html+=`<${tag}>`;list=tag;}
        const check=b.type==='task'?`<input type="checkbox" disabled${b.attrs.checked?' checked':''}>`:'';
        html+=`<li>${check}${inline(b)}${renderRows(children.get(b.id)||[])}</li>`;
      }else{close();html+=render(b);}
    }close();return html;
  }
  const identities=new Set(blocks.map(b=>b.id));
  return renderRows(blocks.filter(b=>!identities.has(b.parent)));
}
export function markdown(document){
  return document.blocks.map(b=>{
    const text=b.text,prefix=b.type==='heading'?'#'.repeat(Math.max(1,Math.min(3,b.attrs.level||2)))+' ':b.type==='bullet'?'- ':b.type==='ordered'?'1. ':b.type==='task'?(b.attrs.checked?'- [x] ':'- [ ] '):b.type==='quote'?'> ':'';
    if(b.type==='code')return '```'+(b.attrs.language||'')+'\n'+text+'\n```';
    if(b.type==='divider')return '---';if(b.type==='image')return '!['+(b.attrs.alt||'')+']('+b.attrs.src+')';
    return (b.parent?'  ':'')+prefix+text;
  }).join('\n\n')+'\n';
}

// Spreadsheet text: quotes protect tabs/newlines and doubled quotes are literal.
export function parseTSV(text){
  if(text.length>1024*1024)throw Error('Paste a smaller section at a time.');
  if(!/[\t\r\n]/.test(text))return null;
  const rows=[];let row=[],cell='',quoted=false,afterQuote=false;
  const field=()=>{row.push({text:cell,marks:[]});cell='';afterQuote=false;if(row.length>32)throw Error('Paste at most 32 columns.');};
  const line=()=>{field();rows.push(row);row=[];if(rows.length>256)throw Error('Paste at most 256 rows.');};
  for(let i=0;i<text.length;i++){
    const ch=text[i];
    if(quoted){if(ch==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;afterQuote=true;}}else cell+=ch;continue;}
    if(ch==='"'&&!cell&&!afterQuote){quoted=true;continue;}
    if(ch==='\t'){field();continue;}
    if(ch==='\r'||ch==='\n'){line();if(ch==='\r'&&text[i+1]==='\n')i++;continue;}
    if(afterQuote)throw Error('A quoted table field must end before the next field.');
    cell+=ch;
  }
  if(quoted)throw Error('This table field has an unclosed quote.');
  if(cell||row.length||afterQuote||!rows.length)line();
  const width=Math.max(...rows.map(r=>r.length));
  for(const row of rows)while(row.length<width)row.push({text:'',marks:[]});
  return rows;
}
