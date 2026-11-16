// CodeMirror positions count UTF-16 units and one unit per line break. Native
// source keeps its original separators; only newly inserted breaks adopt style.
export const normalizeSource=value=>value.replace(/\r\n?|\n/g,'\n');
export function applySourceChanges(value,changes){
  const separator=value.match(/\r\n|\r|\n/)?.[0]||'\n';
  let raw=0,position=0,previous=0,result='',copied=0;
  const at=target=>{
    while(position<target){
      if(raw>=value.length)throw Error('Source change is outside the current text.');
      raw+=value[raw]==='\r'&&value[raw+1]==='\n'?2:1;position++;
    }
    return raw;
  };
  for(const change of changes){
    if(!Number.isInteger(change.from)||!Number.isInteger(change.to)||change.from<previous||change.to<change.from||typeof change.text!=='string')
      throw Error('Invalid source change.');
    const from=at(change.from),to=at(change.to);
    result+=value.slice(copied,from)+normalizeSource(change.text).replaceAll('\n',separator);
    copied=to;previous=change.to;
  }
  return result+value.slice(copied);
}
