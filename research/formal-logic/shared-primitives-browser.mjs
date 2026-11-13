import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join} from 'node:path';
const project=resolve('research/formal-logic'),base=process.argv[2],output=resolve(process.argv[3]);
await mkdir(output,{recursive:true});
const helper=spawn(process.execPath,[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const value=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(4+n);const request=waiting.shift();clearTimeout(request.timer);value.ok?request.resolve(value.result):request.reject(Error(value.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const report={schema:'enchant.formal.shared-sdk-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const chapter='one-sdk-function-for-tree-and-graph-values';
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await call({op:'navigate',url:base+'/#'+chapter});
  check(size.name+': all 87 cells present; no authoring failures',await evaluate("document.querySelectorAll('.cell').length===87&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name+': no page overflow',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': same mathematics and separate policy versions are explained',await evaluate("document.body.innerText.includes('One SDK function for tree and graph values')&&document.body.innerText.includes('2/15')&&document.body.innerText.includes('872')&&document.body.innerText.includes('1,600')"));
  check(size.name+': language privacy and remaining authority boundary stay explicit',await evaluate("document.body.innerText.includes('BL privacy does not hide the native BEAM bridge')&&document.body.innerText.includes('Managed assertion replay remains next')"));
  for(const theme of ['day','night']){
   if(theme==='night')await call({op:'click',selector:'#theme'});
   await evaluate(`window.scrollBy({top:document.getElementById('${chapter}').getBoundingClientRect().top-92,behavior:'instant'})`);
   await shot(size.name+'-shared-chapter-'+theme);
  }
  await call({op:'click',selector:'#theme'});
  await call({op:'navigate',url:base+'/#s-the-model-running'});
  await evaluate("document.querySelector('#cell-story-shared-primitives').scrollIntoView({block:'center',behavior:'instant'})");
  check(size.name+': actual shared SDK result is in the visible panel',await evaluate("(()=>{const r=document.querySelector('#cell-story-shared-primitives .result').getBoundingClientRect();return r.width>0&&r.height>0&&r.bottom>90&&r.top<innerHeight})()"));
  const text=await evaluate("document.querySelector('#cell-story-shared-primitives .result')?.innerText||''");
  check(size.name+': exact fraction and both real execution charges are visible',text.includes(':result {:formal/real [2 15]}')&&text.includes(':legacy-v1-work 1600')&&text.includes(':direct-v2-work 872')&&text.includes(':literal-admission-work 364'));
  check(size.name+': same original graph and distinct settings stay visible',text.includes(':same-original-graph true')&&text.includes(':different-settings true')&&text.includes(':different-execution true'));
  check(size.name+': same allowance completes v2 and refuses v1',text.includes(':v1-at-872 :incomplete')&&text.includes(':v2-at-872 :complete'));
  check(size.name+': no solver or compiler authority is inferred',text.includes(':native-calls 0')&&text.includes(':compiler-proof-authority false')&&text.includes(':assertion-replay :not-run'));
  await shot(size.name+'-shared-cell-day');
  await call({op:'click',selector:'#theme'});
  await evaluate("document.querySelector('#cell-story-shared-primitives').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name+'-shared-cell-night');await call({op:'click',selector:'#theme'});
 }
 for(const path of ['SHARED-PRIMITIVES.md','MANAGED-GRAPH-PLAN.md','src/formal/term-forest-evaluate.bl','src/formal/term-forest.bl','src/formal/integer-preflight.bl','src/formal/rational-preflight.bl','evidence/shared-primitives/sdk-traces.json','evidence/shared-primitives/qualification.json','evidence/shared-primitives/integration-qualification.json']){
  const r=await fetch(base+'/'+path),body=Buffer.from(await r.arrayBuffer());
  check('Exact declared source: '+path,r.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(x=>x.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(x=>!x.passed)}));if(!report.passed)process.exitCode=1;
}
