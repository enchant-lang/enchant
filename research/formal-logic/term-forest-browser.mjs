import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join} from 'node:path';

const project=resolve('research/formal-logic');
const base=process.argv[2]||'http://127.0.0.1:24089';
const output=resolve(process.argv[3]||join(project,'evidence/term-forest/focused-browser'));
await mkdir(output,{recursive:true});
const helper=spawn('/home/othman/.nix-profile/bin/node',[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const value=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(n+4);const request=waiting.shift();clearTimeout(request.timer);value.ok?request.resolve(value.result):request.reject(Error(value.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const click=selector=>call({op:'click',selector});
const report={schema:'enchant.formal.term-forest-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const panel='[data-graph="formal-graph-consumers"] .sg-stage>[data-view]:not([hidden])';
const chapter='a-small-graph-can-reach-either-engine-without-growing-into-a-tree';
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await call({op:'navigate',url:base+'/#'+chapter});
  check(size.name+': 81 executed cells without declarations failing',await evaluate("document.querySelectorAll('.cell').length===81&&document.querySelectorAll('.cell.failed,.review-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name+': no page overflow',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': project availability and timing limits remain explicit',await evaluate("document.body.innerText.includes('A qualified project preview')&&document.body.innerText.includes('Small inputs pay more graph-checking overhead')&&document.body.innerText.includes('not end-to-end query or solver benchmarks')"));
  await evaluate(`document.getElementById('${chapter}').scrollIntoView({block:'start',behavior:'instant'})`);await shot(size.name+'-term-forest-chapter');
  for(const id of ['forest','raw']){
   await click(panel+' .review-index [data-sg-to="'+id+'"]');
   await evaluate(`document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail').scrollTo({top:0,behavior:'instant'});document.querySelector(${JSON.stringify(panel)}).scrollIntoView({block:'center',behavior:'instant'})`);
   const t=await evaluate(`document.querySelector(${JSON.stringify(panel)}).innerText`);
   check(size.name+': '+id+' node keeps prototype authority boundaries',id==='forest'?t.includes('Project preview on SDK 44')&&t.includes('binder environment'):t.includes('Raw success invalidates managed portable-context accounting')&&t.includes('compiler authority remains false'));
   await shot(size.name+'-term-forest-'+id);
  }
  if(size.name==='phone'){
   await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail');d.scrollTo({top:d.scrollHeight,behavior:'instant'})})()`);
   check('phone: raw relationships fit above floating controls',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-graph-consumers"]'),r=document.querySelector(${JSON.stringify(panel)}).querySelector('.review-related').getBoundingClientRect();return r.bottom<=g.querySelector('.sg-toolbar').getBoundingClientRect().top})()`));
   await shot('phone-term-forest-raw-details');
  }else{
   await click('#theme');await shot('desktop-term-forest-raw-night');await click('#theme');
  }
  await call({op:'navigate',url:base+'/#s-the-model-running'});
  const text=await evaluate("document.querySelector('#cell-story-term-forest .result')?.innerText||''");
  check(size.name+': actual compact native run is visible',text.includes(':native-definitions 17')&&text.includes(':native-packet-bytes [772 772]')&&text.includes(':observed-roots [true true]'));
  check(size.name+': raw success and zero managed calls are distinct',text.includes(':raw-native-scopes 2')&&text.includes(':managed-query-calls 0')&&text.includes(':managed-contexts-invalidated [true true]')&&text.includes(':transport :raw-compatibility')&&text.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-term-forest').scrollIntoView({block:'center',behavior:'instant'})");await shot(size.name+'-story-term-forest-data');
 }
 for(const path of ['TERM-FOREST.md','TERM-FOREST-PLAN.md','src/formal/term-forest.bl','evidence/term-forest/qualification.json']){
  const r=await fetch(base+'/'+path),body=Buffer.from(await r.arrayBuffer());check('Declared current source bytes: '+path,r.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(x=>x.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(x=>!x.passed)}));if(!report.passed)process.exitCode=1;
}
