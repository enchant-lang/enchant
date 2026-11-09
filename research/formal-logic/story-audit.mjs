import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
const base=process.argv[2]||'http://127.0.0.1:24089';
const output=resolve('research/formal-logic/evidence/story/browser-audit');
await mkdir(output,{recursive:true});
const helper=spawn('/home/othman/.nix-profile/bin/node',['research/formal-logic/browser-driver.mjs',output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const v=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(n+4);const p=waiting.shift();clearTimeout(p.timer);v.ok?p.resolve(v.result):p.reject(Error(v.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const navigate=path=>call({op:'navigate',url:base+path});
const click=selector=>call({op:'click',selector});
const check=(name,ok,detail={})=>{report.checks.push({name,passed:Boolean(ok),...detail});if(!ok)console.log('FAILED '+name);};
const wait=expression=>call({op:'wait',expression});
const report={schema:'enchant.formal.guided-review-audit.v1',base,started:new Date().toISOString(),checks:[],screenshots:[],scope:'Live presentation, recorded data, source-backed views and kit interactions. No production semantic change.'};
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
try{
 await call({op:'open',width:1440,height:1000,mobile:false});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await navigate('/#s-the-big-idea');await wait("!!document.querySelector('#s-the-big-idea')");
  const top=await evaluate("({title:document.title,w:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth,failed:document.querySelectorAll('.cell.failed,.ms-errors,.review-errors,.cl-errors,.lt-errors').length})");
  check(size.name+': readable page width',top.sw<=top.w+2,top);check(size.name+': no failed cells or declarations',top.failed===0,top);
  await shot(size.name+'-introduction');
  await navigate('/#s-could-beam-lisp-be-fully-formal');
  check(size.name+': full formality discussion present',await evaluate("document.body.innerText.includes('Can it still feel like a Lisp?')&&document.body.innerText.includes('Self-hosting a checker in BL does not verify')"));
  await shot(size.name+'-formal-language');
  await navigate('/#s-a-path-we-can-actually-build');
  await click('#milestones-formal-delivery [data-milestone-to="M3"]');
  check(size.name+': milestone selects its own detail',await evaluate("!document.querySelector('[data-milestone-detail=\"M3\"]').hidden"));
  await shot(size.name+'-milestones');
  await click('#milestones-formal-delivery [data-milestone-detail="M3"] [data-milestone-to="M2"]');
  check(size.name+': milestone dependency navigates',await evaluate("!document.querySelector('[data-milestone-detail=\"M2\"]').hidden"));
  await click('#milestones-formal-delivery [data-milestone-to="M3"]');
  await evaluate("fetch('/doc').then(r=>r.json()).then(d=>{window.__auditDoc=d;return true})");
  check(size.name+': live refresh endpoint retains selected milestone',await evaluate("!document.querySelector('[data-milestone-detail=\"M3\"]').hidden&&!!window.__auditDoc.rev"));
  await navigate('/#s-try-the-language-ideas');
  await wait("!!document.querySelector('[data-source-id=\"story-lab\"] iframe')?.contentDocument?.querySelector('.fl-app')");
  check(size.name+': preview uses public source components',await evaluate("!!document.querySelector('[data-source-id=\"story-lab\"] iframe').contentDocument.querySelector('[data-ui-component=\"formal-answer\"]')"));
  await shot(size.name+'-source-preview');
  await click('#claims-formal-promises [data-claims-filter="open"]');
  check(size.name+': promises ledger keeps future work visibly open',await evaluate("(()=>{const r=document.querySelector('#claims-formal-promises');const rows=[...r.querySelectorAll('.cl-row')].filter(e=>!e.hidden);return rows.length===2&&rows.every(e=>e.dataset.open==='1')})()"));
  await shot(size.name+'-open-promises');
  await click('#claims-formal-promises [data-claims-filter="open"]');
  await click('#claims-formal-promises [data-claims-view="maps"]');
  await wait("!!document.querySelector('#claims-formal-promises .cl-frame')?.contentDocument?.querySelector('[data-ui-composition=\"maps\"]')");
  check(size.name+': promise opens its actual source-backed view',await evaluate("document.querySelector('#claims-formal-promises .cl-dialog').open"));
  await shot(size.name+'-promise-view');
  await call({op:'key',key:'Escape'});
  check(size.name+': promise dialog restores focus',await evaluate("!document.querySelector('#claims-formal-promises .cl-dialog').open&&document.activeElement===document.querySelector('#claims-formal-promises [data-claims-view=\"maps\"]')"));
  await navigate('/#s-could-beam-lisp-be-fully-formal');
  await click('#lifetime-formal-proof-lifetime .lt-scroll [data-lt-item="s1"]');
  check(size.name+': proof lifetime opens the selected explanation',await evaluate("!document.querySelector('#lifetime-formal-proof-lifetime [data-lt-detail=\"s1\"]').hidden"));
  check(size.name+': proof lifetime contains scrolling within its panel',await evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+2"));
  await shot(size.name+'-proof-lifetime');
  await call({op:'key',key:'Escape'});
  check(size.name+': proof lifetime Escape clears detail',await evaluate("[...document.querySelectorAll('#lifetime-formal-proof-lifetime [data-lt-detail]')].every(e=>e.hidden)"));
  await navigate('/#s-try-the-language-ideas');
  await click('[data-source-id="story-lab"] [data-source-highlight]');
  check(size.name+': source link highlighting remains available',await evaluate("document.querySelector('[data-source-id=\"story-lab\"] [data-source-highlight]').getAttribute('aria-pressed')==='true'"));
  await click('[data-source-id="story-lab"] [data-source-highlight]');
  await click('[data-source-id="story-lab"] [data-source-inspect]');
  check(size.name+': source component inspection remains available',await evaluate("document.querySelector('[data-source-id=\"story-lab\"] [data-source-inspect]').getAttribute('aria-pressed')==='true'"));
  await click('[data-source-id="story-lab"] [data-source-inspect]');
  await click('[data-source-id="story-lab"] [data-source-mode]');
  await wait("document.querySelectorAll('[data-source-id=\"story-lab\"] .sg-node').length>=5");
  check(size.name+': source graph discovers all five declared views',await evaluate("document.querySelectorAll('[data-source-id=\"story-lab\"] .sg-node').length===5"));
  await shot(size.name+'-source-map');
  await click('[data-source-id="story-lab"] [data-source-mode]');
  for(const view of ['maps','accounts','bits','fp','evidence']){
   await navigate('/views?view='+view);
   check(size.name+'/'+view+': rendered shared composition',await evaluate(`!!document.querySelector('[data-ui-composition="${view}"]')`));
   const width=await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2');check(size.name+'/'+view+': no page overflow',width);
  }
  await shot(size.name+'-evidence');
  await navigate('/explorer?q=family:Evidence%20state:Candidate');
  check(size.name+': explorer query narrows actual state examples',await evaluate("document.querySelectorAll('.fl-specimen-example').length===1&&!!document.querySelector('.fl-answer.candidate')"));
  await navigate('/explorer?q=bad:query');check(size.name+': invalid query is explained',await evaluate("document.body.innerText.includes('Use id:')"));
  await navigate('/#s-watch-the-evidence');
  await wait("document.querySelectorAll('#witness-formal-browser-witness .witness-steps button').length>=5");
  await click('#witness-formal-browser-witness [data-witness-move="1"]');
  check(size.name+': witness advances recorded claim',await evaluate("document.querySelector('#witness-formal-browser-witness [data-witness-position]').innerText.startsWith('2 /')"));
  await evaluate("document.querySelector('#witness-formal-browser-witness .witness-stage:not([hidden]) img').scrollIntoView({block:'center'})");
  await wait("[...document.querySelectorAll('#witness-formal-browser-witness .witness-stage:not([hidden]) img')].some(i=>i.complete&&i.naturalWidth>0)");
  check(size.name+': witnessed frame is an actual loaded image',await evaluate("[...document.querySelectorAll('#witness-formal-browser-witness .witness-stage:not([hidden]) img')].every(i=>i.complete&&i.naturalWidth>0)"));
  await shot(size.name+'-witness');
  await navigate('/#s-the-presentation-language');
  await click('#theme');check(size.name+': dark theme changes document',await evaluate("document.documentElement.dataset.theme==='dark'"));
  await shot(size.name+'-night');await click('#theme');
  await navigate('/#all');
  const graphs=await evaluate("[...document.querySelectorAll('.screen-graph[data-graph]')].filter(g=>g.querySelector('.review-app')).map(g=>g.dataset.graph)");
  for(const id of graphs){
   const root=`[data-graph="${id}"]`;
   await click(root+' [data-sg-reset]');
   const start=await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view`);
   const target=await evaluate(`(()=>{const g=document.querySelector('${root}');return [...g.querySelectorAll('.review-index [data-sg-to]')].find(e=>e.dataset.sgTo!==${JSON.stringify(start)})?.dataset.sgTo})()`);
   await click(root+` .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="${target}"]`);
   check(size.name+'/'+id+': connected topic opens',await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view===${JSON.stringify(target)}`));
   await click(root+' [data-sg-back]');
   check(size.name+'/'+id+': Back restores the topic',await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view===${JSON.stringify(start)}`));
   await click(root+' [data-sg-mode]');
   check(size.name+'/'+id+': map contains every topic',await evaluate(`(()=>{const g=document.querySelector('${root}');return g.querySelectorAll('.sg-overview .sg-node').length===g.querySelectorAll('.sg-stage>[data-view]').length})()`));
   await click(root+` .sg-overview .sg-node[data-sg-to="${target}"]`);
   check(size.name+'/'+id+': map selection returns to detail',await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view===${JSON.stringify(target)}`));
   await click(root+' [data-sg-expand]');
   check(size.name+'/'+id+': full-screen focus scope opens',await evaluate(`document.querySelector('${root}').classList.contains('sg-expanded')&&document.querySelector('${root} .sg-workbench').getAttribute('aria-modal')==='true'`));
   await call({op:'key',key:'Escape'});
   check(size.name+'/'+id+': Escape returns focus',await evaluate(`!document.querySelector('${root}').classList.contains('sg-expanded')&&document.activeElement===document.querySelector('${root} [data-sg-expand]')`));
  }
 }
 const record=await fetch(base+'/explorer.json?q=family:Comparison').then(r=>r.json());
 check('Catalog comes from three annotated renderer definitions',record.length===1&&record[0].qualified==='formal.presentation/comparison-card'&&record[0].source.endsWith('presentation.bl'));
 check('Unknown preview routes refuse explicitly',(await fetch(base+'/views?view=missing')).status===404);
 check('Anonymous answer writes are denied',(await fetch(base+'/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:'formal-total-core-direction',answer:'agree'})})).status===403);
}catch(error){report.fatal={message:error.message,stack:error.stack};check('Audit completed',false,{error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();
 report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(c=>c.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,failed:report.checks.filter(c=>!c.passed),screenshots:report.screenshots.length}));
 if(!report.passed)process.exitCode=1;
}
