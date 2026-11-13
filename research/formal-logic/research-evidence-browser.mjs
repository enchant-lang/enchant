import {spawn} from 'node:child_process';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
const [base,fixture,output]=process.argv.slice(2);
await mkdir(output,{recursive:true});
const helper=spawn(process.execPath,[resolve('research/formal-logic/browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const v=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const p=waiting.shift();clearTimeout(p.timer);v.ok?p.resolve(v.result):p.reject(Error(v.error));}});
const call=message=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser deadline')),35000);waiting.push({resolve,reject,timer});const b=Buffer.from(JSON.stringify(message)),n=Buffer.alloc(4);n.writeUInt32BE(b.length);helper.stdin.write(Buffer.concat([n,b]));});
const evaluate=expression=>call({op:'eval',expression});
const report={schema:'bl.formal-research-browser.v1',base,fixture:true,checks:[],screenshots:[],started:new Date().toISOString()};
const check=(name,value)=>{report.checks.push({name,passed:Boolean(value)});if(!value)throw Error(name);};
const shot=async name=>{await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');};
const asset=join(fixture,'dossier/research-evidence.js'),store=join(fixture,'elements/word-answer-evidence.bl.org');
const original=await readFile(asset),initial=await readFile(store);
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const revision=async()=>evaluate("Number(document.querySelector('.research-status').textContent.match(/Revision (\\d+)/)?.[1])");
async function state(expected,n){await call({op:'wait',expression:`document.querySelector('[data-research-freshness]')?.dataset.researchFreshness===${JSON.stringify(expected)}&&document.querySelector('.research-status')?.textContent.includes('Revision ${n}.')`});}
try{
 await call({op:'open',width:390,height:844,mobile:true});
 await call({op:'navigate',url:base+'/'});
 check('Anonymous reading retains the comparison without a save control',await evaluate("document.querySelectorAll('[data-research-row]').length===7&&!document.querySelector('[data-research-save]')"));
 const anonymous=await evaluate("fetch('/research-elements/word-answer-evidence/save',{method:'POST',headers:{'content-type':'application/json'},body:'{}'}).then(r=>r.status)");
 check('Anonymous writes are refused',anonymous===403);
 await call({op:'headers',headers:{'tailscale-user-login':'formal-evidence-browser'}});
 await call({op:'navigate',url:base+'/'});
 await state('current',1);
 check('Owner sees the fixed snapshot save action',await evaluate("document.querySelector('[data-research-save]')?.dataset.researchSave==='word-answer-evidence'"));
 check('Pending proof and Source claims stay separate from supported facts',await evaluate("document.querySelector('[data-research-row=\"proof\"]').innerText.includes('Still open')&&document.querySelector('[data-research-row=\"program\"]').innerText.includes('Still open')"));
 await shot('phone-current');
 for(const [name,body,expected] of [['wrong-basis',{basis:'stale'},409],['callable',{basis:'stale',function:'System/eval'},400]]){
  const actual=await evaluate(`fetch('/research-elements/word-answer-evidence/save',{method:'POST',headers:{'content-type':'application/json'},body:${JSON.stringify(JSON.stringify(body))}}).then(r=>r.status)`);
  check('Rejected '+name+' request preserves the snapshot',actual===expected&&(await readFile(store)).equals(initial));
 }
 await writeFile(asset,Buffer.concat([original,Buffer.from('\n// Owned source-basis browser fixture revision.\n')]));
 await call({op:'navigate',url:base+'/'});await state('stale',1);
 check('Source change keeps the prior native Org snapshot',await evaluate("document.querySelector('.research-status').innerText.includes('saved answer is still shown')")&&(await readFile(store)).equals(initial));
 await shot('phone-stale');
 await call({op:'click',selector:'[data-research-save]'});await state('current',2);
 const afterRefresh=await readFile(store);
 check('Explicit browser refresh appends a native Org record',afterRefresh.subarray(0,initial.length).equals(initial)&&(afterRefresh.toString().match(/#\+begin_research_element /g)||[]).length===2);
 await shot('phone-refreshed');
 await writeFile(asset,original);
 await call({op:'navigate',url:base+'/'});await state('stale',2);
 await call({op:'click',selector:'[data-research-save]'});await state('current',3);
 await call({op:'navigate',url:base+'/'});await state('current',3);
 const final=await readFile(store);
 check('Reload reads all three durable native Org revisions',final.subarray(0,initial.length).equals(initial)&&(final.toString().match(/#\+begin_research_element /g)||[]).length===3&&(await revision())===3);
 await call({op:'viewport',width:1440,height:1000,mobile:false});
 await call({op:'click',selector:'#theme'});
 await call({op:'click',selector:'.research-element summary'});
 check('Exact source paths and locators are inspectable',await evaluate("document.querySelector('.research-element').innerText.includes('/ledger/0/lookup-normalizer-calls')&&!!document.querySelector('.research-element a[href=\"/evidence/word-integration/reader-one.json\"]')"));
 await shot('desktop-night-sources');
 for(const surface of ['tool','workspace','specimen']){
  await call({op:'navigate',url:base+'/research-elements/'+surface});
  check(surface+' uses the same installed comparison component',await evaluate("document.querySelectorAll('[data-research-row]').length===7&&document.querySelector('[data-research-element]').dataset.researchElement==='word-answer-evidence'"));
 }
 await call({op:'navigate',url:base+'/explorer?q=id:formal-word-evidence'});
 check('Component discovery registers the actual saved view',await evaluate("document.querySelectorAll('.fl-specimen-example').length===1&&document.querySelectorAll('[data-research-row]').length===7"));
 const unknown=await evaluate("fetch('/research-elements/not-installed/view').then(r=>r.status)");
 check('Browser IDs cannot resolve arbitrary elements',unknown===404);
 report.snapshot={initial_sha256:hash(initial),final_sha256:hash(final),revisions:3,source_fixture_restored:(await readFile(asset)).equals(original)};
 await writeFile(join(output,'actual-snapshots.bl.org'),final);
}catch(error){report.error=error.message;report.checks.push({name:'Browser scenario completed',passed:false,error:error.message});}
finally{
 await writeFile(asset,original);
 try{await call({op:'stop'});}catch{}
 helper.stdin.end();if(helper.exitCode===null)await new Promise(resolve=>helper.once('exit',resolve));
 report.passed=report.checks.every(x=>x.passed);report.finished=new Date().toISOString();
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length}));
 process.exitCode=report.passed?0:1;
}
