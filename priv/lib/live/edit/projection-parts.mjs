// Reuse a block's DOM only when everything outside its editable source is equal.
// Custom renderer output participates in this signature, including dynamic attrs.
export function projectionParts(tree,id){
  let text=null,count=0,dynamic=false;
  const signature=JSON.stringify(tree,(_key,value)=>{
    if(typeof value==='function'){dynamic=true;return null;}
    if(Array.isArray(value)&&value[1]&&typeof value[1]==='object'&&!Array.isArray(value[1])){
      if(value[1]['data-edit-text']===id){text=value;count++;return value.slice(0,2);}
      if(value[1]['data-edit-children'])return value.slice(0,2);
    }
    return value;
  });
  return {text:count===1?text:null,signature:!dynamic&&count===1?signature:null};
}
