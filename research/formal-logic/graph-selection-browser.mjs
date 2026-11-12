import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join} from 'node:path';

const project=resolve('research/formal-logic');
const base=process.argv[2]||'http://127.0.0.1:24089';
const output=resolve(process.argv[3]||join(project,'evidence/graph-selection-model/browser-audit'));
await mkdir(output,{recursive:true});
const helper=spawn('/home/othman/.nix-profile/bin/node',[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const value=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(n+4);const request=waiting.shift();clearTimeout(request.timer);value.ok?request.resolve(value.result):request.reject(Error(value.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const click=selector=>call({op:'click',selector});
const report={schema:'enchant.formal.graph-selection-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString(),scope:'Focused update of the selection-model copy, proof panel and source links. Preceding full graph-consumers presentation receipt retains the wider interaction checks.'};
function check(name,ok,detail={}){report.checks.push({name,passed:Boolean(ok),...detail});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const panel='[data-graph="formal-graph-consumers"] .sg-stage>[data-view]:not([hidden])';
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});
  await call({op:'navigate',url:base+'/#use-the-saved-question-without-unpacking-its-history'});
  check(size.name+': 80 cells and no failed declarations',await evaluate("document.querySelectorAll('.cell').length===80&&document.querySelectorAll('.cell.failed,.review-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name+': existing 49 review graphs retained',await evaluate("[...document.querySelectorAll('.screen-graph[data-graph]')].filter(g=>g.querySelector('.review-app')).length===49"));
  check(size.name+': no page overflow',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': selection model counts and actual selector boundary are readable',await evaluate(`(()=>{const t=document.body.innerText.replaceAll('’',"'");return t.includes('seven general lemmas, five fixture theorems and four rejection controls')&&t.includes("Prove BL's actual dependency selector builds that closed set.")})()`));
  await click(panel+' .review-index [data-sg-to="proof"]');
  check(size.name+': checked proof panel states conditional value agreement',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(panel)}).innerText;return t.includes('seven selection lemmas')&&t.includes('five fixture theorems')&&t.includes('correct scalar admission')&&t.includes('actual BL dependency selector')&&t.includes('compiler correctness remain separate obligations')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(panel)}).scrollIntoView({block:'center',behavior:'instant'})`);
  await shot(size.name+'-selection-proof');
  if(size.name==='phone'){
   await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail');d.scrollTo({top:d.scrollHeight,behavior:'instant'})})()`);
   check('phone: proof relationships remain above floating tools',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-graph-consumers"]'),d=document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=d.getBoundingClientRect().top&&r.bottom<=t.top})()`));
   await shot('phone-selection-proof-details');
  }else{
   await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(panel)}).scrollIntoView({block:'center',behavior:'instant'})`);
   check('desktop: dark theme applied',await evaluate("document.documentElement.dataset.theme==='dark'"));
   await shot('desktop-selection-proof-night');await click('#theme');
  }
  await click('[data-graph="formal-graph-consumers"] [data-sg-mode]');
  await click('[data-graph="formal-graph-consumers"] .sg-overview .sg-node[data-sg-to="proof"]');
  check(size.name+': map returns to selected proof topic',await evaluate(`document.querySelector(${JSON.stringify(panel)}).dataset.view==='proof'`));
  await evaluate("[...document.querySelectorAll('#doc a')].find(a=>/GRAPH-SELECTION-MODEL\\.md$/.test(a.getAttribute('href')||'')).closest('p').scrollIntoView({block:'start',behavior:'instant'})");
  await shot(size.name+'-selection-meaning');
  const refs=await evaluate("['story-graph-selected','story-graph-native','story-graph-intercepted','story-graph-durable'].map(id=>document.querySelector('#cell-'+id+' .result').innerText.match(/:sha256\\s+\"([0-9a-f]{64})\"/)?.[1])");
  check(size.name+': four executed examples retain the original complete question',refs.length===4&&refs.every(Boolean)&&new Set(refs).size===1);
 }
 for(const path of ['GRAPH-SELECTION-MODEL.md','metatheory/GraphSelection.lean','metatheory/GraphSelectionExamples.lean','evidence/graph-selection-model/qualification.json']){
  const response=await fetch(base+'/'+path),body=Buffer.from(await response.arrayBuffer());
  const expected=await readFile(join(project,path));
  check('Declared current source bytes: '+path,response.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(expected).digest('hex'));
 }
 check('Compiled selection module stays unavailable',(await fetch(base+'/evidence/graph-selection-model/GraphSelection.olean')).status===404);
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();
 report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(row=>row.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(row=>!row.passed)}));
 if(!report.passed)process.exitCode=1;
}
