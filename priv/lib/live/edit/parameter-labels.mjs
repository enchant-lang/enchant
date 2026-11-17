// Labels describe choices; their exact values remain the semantic arguments.
export function choiceLabel(parameter,value){
  const key=String(value),labels=parameter.labels;
  if(labels&&Object.hasOwn(labels,key)&&typeof labels[key]==='string'&&labels[key].trim())return labels[key];
  const text=value==null?'':String(value);
  if(!text)return parameter['empty-label']||'None';
  const [first,...rest]=Array.from(text);return first.toUpperCase()+rest.join('');
}
