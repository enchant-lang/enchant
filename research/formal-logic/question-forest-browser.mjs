import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join} from 'node:path';

const project=resolve('research/formal-logic');
const base=process.argv[2]||'http://127.0.0.1:24089';
const output=resolve(process.argv[3]||join(project,'evidence/question-forest/focused-browser'));
await mkdir(output,{recursive:true});
const helper=spawn('/home/othman/.nix-profile/bin/node',[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const value=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(4+n);const request=waiting.shift();clearTimeout(request.timer);value.ok?request.resolve(value.result):request.reject(Error(value.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const click=async(selector,options={})=>{try{return await call({op:'click',selector,...options});}catch(error){throw Error(selector+': '+error.message);}};
const report={schema:'enchant.formal.question-forest-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const panel='[data-graph="formal-graph-consumers"] .sg-stage>[data-view]:not([hidden])';
const chapter='keep-the-question-attached-to-its-shared-terms';
const center=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center',behavior:'instant'})`);
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await call({op:'navigate',url:base+'/#'+chapter});
  check(size.name+': all 83 retained cells and no declaration failures',await evaluate("document.querySelectorAll('.cell').length===83&&document.querySelectorAll('.cell.failed,.review-errors').length===0"));
  check(size.name+': page fits the viewport',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': admission distinctions remain explicit',await evaluate("document.body.innerText.includes('These are shared semantic issues to repair centrally')&&document.body.innerText.includes('It returns no operational view or decoded witness')"));
  await evaluate(`window.scrollBy({top:document.getElementById('${chapter}').getBoundingClientRect().top-92,behavior:'instant'})`);await shot(size.name+'-question-inventory-chapter');
  await call({op:'navigate',url:base+'/#use-the-saved-question-without-unpacking-its-history'});
  await click(panel+' .review-index [data-sg-to="inventory"]');
  await evaluate(`document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail').scrollTo({top:0,behavior:'instant'})`);await center(panel);
  const t=await evaluate(`document.querySelector(${JSON.stringify(panel)}).innerText`);
  check(size.name+': inventory branch records original meaning and exact comparisons',t.includes('All 187 questions retain exact native definitions')&&t.includes('assertion labels')&&t.includes('vacuity'));
  check(size.name+': inventory branch preserves admission and execution limits',t.includes('Sixty-eight focused assertions')&&t.includes('not a decoded witness or managed execution')&&t.includes('result budgets')&&t.includes('actual owner'));
  check(size.name+': actual qualification makes no engine or managed query call',t.includes('No engine or managed query is called'));
  await shot(size.name+'-question-inventory');
  if(size.name==='phone'){
   await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail');d.scrollTo({top:d.scrollHeight,behavior:'instant'})})()`);
   check('phone: relationships remain above the floating toolbar',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-graph-consumers"]'),r=document.querySelector(${JSON.stringify(panel)}).querySelector('.review-related').getBoundingClientRect();return r.bottom<=g.querySelector('.sg-toolbar').getBoundingClientRect().top})()`));
   await shot('phone-question-inventory-details');
  }else{
   await click('#theme');await center(panel);await shot('desktop-question-inventory-night');await click('#theme');
  }
 }
 for(const path of ['QUESTION-FOREST.md','QUESTION-FOREST-PLAN.md','src/formal/question-forest.bl','evidence/question-forest/qualification.json','TERM-FOREST-RESOURCE-PLAN.md']){
  const r=await fetch(base+'/'+path),body=Buffer.from(await r.arrayBuffer());
  check('Declared source bytes: '+path,r.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(x=>x.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(x=>!x.passed)}));if(!report.passed)process.exitCode=1;
}
