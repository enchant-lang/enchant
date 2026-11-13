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
const report={schema:'enchant.formal.bounded-point-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const chapter='give-checking-a-budget-without-changing-mathematical-integers';
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await call({op:'navigate',url:base+'/#'+chapter});
  check(size.name+': all 85 cells present; no authoring failures',await evaluate("document.querySelectorAll('.cell').length===85&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name+': no page overflow',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': separate root completion and refusal are explained',await evaluate("document.body.innerText.includes('A refusal does not erase what we can still know')&&document.body.innerText.includes('A cheaper later root')"));
  check(size.name+': cost and implementation limits remain explicit',await evaluate("document.body.innerText.includes('not a theorem about CPU time or heap use')&&document.body.innerText.includes('actual managed assertion replay remain next')"));
  for(const theme of ['day','night']){
   if(theme==='night')await call({op:'click',selector:'#theme'});
   await evaluate(`window.scrollBy({top:document.getElementById('${chapter}').getBoundingClientRect().top-92,behavior:'instant'})`);
   await shot(size.name+'-budget-chapter-'+theme);
  }
  await call({op:'click',selector:'#theme'});
  const text=await evaluate("document.querySelector('#cell-story-bounded-point .result')?.innerText||''");
  check(size.name+': actual limited graph run is visible',text.includes(':typed-nodes 17')&&text.includes(':status :incomplete')&&text.includes(':first-refused-forecast-bits 34')&&text.includes(':performed-multiplications 4')&&text.includes(':charged-work-units 119'));
  check(size.name+': decisive false root and retained refusal coexist',text.includes(':decisive-boolean false')&&text.includes(':decisive-root-status :complete')&&text.includes(':retained-refusals 1'));
  check(size.name+': small integer result and authority boundary visible',text.includes(':small-result 63')&&text.includes(':native-calls 0')&&text.includes(':compiler-proof-authority false')&&text.includes(':assertion-replay :not-run'));
  await evaluate("document.querySelector('#cell-story-bounded-point').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name+'-budget-cell-day');
  await call({op:'click',selector:'#theme'});await shot(size.name+'-budget-cell-night');await call({op:'click',selector:'#theme'});
 }
 for(const path of ['BOUNDED-POINT.md','src/formal/term-forest-evaluate.bl','src/formal/bounded-point-examples.bl','test/bounded_point_test.bl','evidence/bounded-point/qualification.json']){
  const r=await fetch(base+'/'+path),body=Buffer.from(await r.arrayBuffer());
  check('Exact declared source: '+path,r.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(x=>x.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(x=>!x.passed)}));if(!report.passed)process.exitCode=1;
}
