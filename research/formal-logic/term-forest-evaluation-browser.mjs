import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join} from 'node:path';

const project=resolve('research/formal-logic');
const base=process.argv[2]||'http://127.0.0.1:24089';
const output=resolve(process.argv[3]||join(project,'evidence/term-forest-evaluation/focused-browser'));
await mkdir(output,{recursive:true});
const helper=spawn('/home/othman/.nix-profile/bin/node',[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const value=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(4+n);const request=waiting.shift();clearTimeout(request.timer);value.ok?request.resolve(value.result):request.reject(Error(value.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const click=async(selector,options={})=>{try{return await call({op:'click',selector,...options});}catch(error){throw Error(selector+': '+error.message);}};
const report={schema:'enchant.formal.term-forest-evaluation-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const panel='[data-graph="formal-graph-consumers"] .sg-stage>[data-view]:not([hidden])';
const calculator='try-changing-how-many-layers-share-their-children';
const number=id=>`Number(document.querySelector('.nb-measure-row [data-nb="${id}"]').innerText.replace(/[^0-9]/g,''))`;
const center=selector=>evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({block:'center',behavior:'instant'})`);
const sharingFrame=size=>size.name==='phone'
 ?evaluate(`window.scrollBy({top:document.getElementById('${calculator}').getBoundingClientRect().top-92,behavior:'instant'})`)
 :center('.nb-measure-row');
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await call({op:'navigate',url:base+'/#'+calculator});
  check(size.name+': 83 checked cells and no authoring failures',await evaluate("document.querySelectorAll('.cell').length===83&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name+': no horizontal page overflow',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name+': illustrative counts stay separate from actual execution',await evaluate("document.body.innerText.includes('This calculator counts syntax')&&document.body.innerText.includes('not additional executions of the evaluator')"));
  check(size.name+': default calculator matches checked fixture',await evaluate(`${number('sharing_terms_16')}===131071&&${number('sharing_nodes')}===17`));
  await sharingFrame(size);await shot(size.name+'-sharing-default');
  await center('.nb-controls>summary');
  if(!await evaluate("document.querySelector('.nb-controls').open"))await click('.nb-controls>summary');
  check(size.name+': expanded source badge fits the page',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  await center('.nb-controls [data-nb-input="sharing_layers"]');
  await evaluate("new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))");
  await evaluate("window.formalRangeEvents=[];for(const type of ['pointerdown','mousedown','mouseup','click','input','change'])document.addEventListener(type,e=>{if(e.target.closest('.nb-controls'))window.formalRangeEvents.push({type,target:e.target.tagName,value:e.target.value,x:e.clientX,y:e.clientY})},true)");
  await click('.nb-controls [data-nb-input="sharing_layers"]',{scroll:false});
  const selectedLayers=Number(await evaluate("document.querySelector('.nb-controls [data-nb-input]').value"));
  const diagnostic=await evaluate("(()=>{const e=document.querySelector('.nb-controls [data-nb-input]');return{html:e.outerHTML,rect:e.getBoundingClientRect().toJSON(),events:window.formalRangeEvents,active:document.activeElement===e,scrollY,viewport:visualViewport?.toJSON?.()}})()");
  (report.pointerSelections??=[]).push({viewport:size.name,layers:selectedLayers,diagnostic});
  if(selectedLayers===16)await shot(size.name+'-pointer-diagnostic');
  check(size.name+': real pointer changes layers to a bounded intermediate value',Number.isInteger(selectedLayers)&&selectedLayers>0&&selectedLayers<16);
  check(size.name+': adjusted figures follow the real control',await evaluate(`${number('sharing_terms_16')}===${2**(selectedLayers+1)-1}&&${number('sharing_nodes')}===${selectedLayers+1}`));
  check(size.name+': all 17 browser counts match the cell formula',await evaluate("Array.from({length:17},(_,layers)=>{const v=window.dossierNotebook.calc('value',{sharing_layers:layers});return v.sharing_nodes===layers+1&&v.sharing_terms_16===2**(layers+1)-1}).every(Boolean)"));
  await sharingFrame(size);await shot(size.name+'-sharing-adjusted');
  await click('.nb-measure-row [data-nb="sharing_terms_16"]');
  check(size.name+': figure opens its actual dependency expression',await evaluate("!document.querySelector('#nb-pop').hidden&&document.querySelector('#nb-pop h4').innerText==='Term occurrences through layer 16'&&!!document.querySelector('#nb-pop [data-nb-open=sharing_terms_15]')"));
  await shot(size.name+'-sharing-formula');
  await click('#nb-pop [data-nb-open="sharing_layers"]');
  check(size.name+': dependency inspection reaches its source and control',await evaluate("document.querySelector('#nb-pop h4').innerText==='Shared layers above the leaf'&&document.querySelector('#nb-pop').innerText.includes('16-layer fixture')&&!!document.querySelector('#nb-pop input[data-nb-input=sharing_layers]')"));
  await call({op:'key',key:'Escape'});
  check(size.name+': escape closes the inspector',await evaluate("document.querySelector('#nb-pop').hidden"));
  await click('.nb-controls [data-nb-undo="sharing_layers"]');
  check(size.name+': undo restores the recorded fixture setting',await evaluate(`${number('sharing_terms_16')}===131071&&${number('sharing_nodes')}===17`));
  await call({op:'navigate',url:base+'/#use-the-saved-question-without-unpacking-its-history'});
  await click(panel+' .review-index [data-sg-to="point"]');
  await evaluate(`document.querySelector(${JSON.stringify(panel)}).querySelector('.review-detail').scrollTo({top:0,behavior:'instant'})`);
  await center(panel);
  check(size.name+': graph point branch states scope and demand',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(panel)}).innerText;return t.includes('6,300 exact root comparisons')&&t.includes('Project preview on SDK 44')&&t.includes('implication keeps')&&t.includes('managed reply integration remain open')})()`));
  await shot(size.name+'-graph-point');
  if(size.name==='desktop'){
   await click('#theme');await center(panel);await shot('desktop-graph-point-night');await click('#theme');
  }
  await call({op:'navigate',url:base+'/#s-the-model-running'});
  const text=await evaluate("document.querySelector('#cell-story-graph-point-2 .result')?.innerText||''");
  check(size.name+': actual graph evaluator result is visible',text.includes(':evaluated-nodes 17')&&text.includes(':typed-nodes 17')&&text.includes(':values [true true]')&&text.includes(':native-execution :not-invoked')&&text.includes(':managed-query-calls 0')&&text.includes(':compiler-proof-authority false'));
  check(size.name+': actual notebook cell checks every integer setting',await evaluate("document.querySelector('#cell-story-graph-sharing-notebook .result').innerText.includes(':settings-checked 17')"));
  await center('#cell-story-graph-point-2');await shot(size.name+'-graph-point-cell');
 }
 for(const path of ['TERM-FOREST-EVALUATION.md','src/formal/term-forest-evaluate.bl','evidence/term-forest-evaluation/qualification.json']){
  const r=await fetch(base+'/'+path),body=Buffer.from(await r.arrayBuffer());
  check('Declared source bytes: '+path,r.status===200&&createHash('sha256').update(body).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(x=>x.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length,failed:report.checks.filter(x=>!x.passed)}));if(!report.passed)process.exitCode=1;
}
