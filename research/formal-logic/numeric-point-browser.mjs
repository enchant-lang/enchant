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
const report={schema:'enchant.formal.numeric-point-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const chapter='checking-a-fraction-starts-before-the-arithmetic';
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await call({op:'navigate',url:base+'/#'+chapter});
  check(size.name+': all 86 cells present; no authoring failures',await evaluate("document.querySelectorAll('.cell').length===86&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name+': no page overflow',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': separate root completion and refusal are explained',await evaluate("document.body.innerText.includes('Literal normalization cannot fit')&&document.body.innerText.includes('A refused predicate is followed by false')"));
  check(size.name+': cost and implementation limits remain explicit',await evaluate("document.body.innerText.includes('seven times')&&document.body.innerText.includes('three times')&&document.body.innerText.includes('No speed advantage, totality theorem or compiler proof is claimed')"));
  for(const theme of ['day','night']){
   if(theme==='night')await call({op:'click',selector:'#theme'});
   await evaluate(`window.scrollBy({top:document.getElementById('${chapter}').getBoundingClientRect().top-92,behavior:'instant'})`);
   await shot(size.name+'-numeric-chapter-'+theme);
  }
  await call({op:'click',selector:'#theme'});
  await call({op:'navigate',url:base+'/#s-the-model-running'});
  await evaluate("document.querySelector('#cell-story-numeric-point').scrollIntoView({block:'center',behavior:'instant'})");
  check(size.name+': executed numeric result is in the visible panel',await evaluate("(()=>{const r=document.querySelector('#cell-story-numeric-point .result').getBoundingClientRect();return r.width>0&&r.height>0&&r.bottom>90&&r.top<innerHeight})()"));
  const text=await evaluate("document.querySelector('#cell-story-numeric-point .result')?.innerText||''");
  check(size.name+': actual limited graph run is visible',text.includes(':typed-nodes 17')&&text.includes(':refused-component-forecast 52')&&text.includes(':performed-multiplications 4')&&text.includes(':evaluation-work 123377')&&text.includes(':admission-work 108'));
  check(size.name+': decisive false root and retained refusal coexist',text.includes(':decisive-boolean false')&&text.includes(':decisive-root-status :complete')&&text.includes(':retained-refusals 1'));
  check(size.name+': same graph records admission refusal before constructor execution',text.includes(':same-original-graph true')&&text.includes(':admission-denial-phase :admission')&&text.includes(':constructors-on-denied-admission :not-run')&&text.includes(':sdk-calls-on-denied-admission 0'));
  check(size.name+': exact fraction result and authority boundary visible',text.includes(':small-result {:formal/real [1 2]}')&&text.includes(':native-calls 0')&&text.includes(':compiler-proof-authority false')&&text.includes(':assertion-replay :not-run'));
  await evaluate("document.querySelector('#cell-story-numeric-point').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name+'-numeric-cell-day');
  await call({op:'click',selector:'#theme'});
  await evaluate("document.querySelector('#cell-story-numeric-point').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name+'-numeric-cell-night');await call({op:'click',selector:'#theme'});
 }
 for(const path of ['NUMERIC-POINT.md','src/formal/term-forest-evaluate.bl','src/formal/numeric-point-examples.bl','src/formal/rational-preflight.bl','test/numeric_point_test.bl','test/numeric_execution_trace_test.bl','evidence/numeric-point/trace.json','evidence/numeric-point/qualification.json']){
  const r=await fetch(base+'/'+path),body=Buffer.from(await r.arrayBuffer());
  check('Exact declared source: '+path,r.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(x=>x.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(x=>!x.passed)}));if(!report.passed)process.exitCode=1;
}
