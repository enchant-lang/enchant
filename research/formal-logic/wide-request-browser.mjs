import {spawn} from 'node:child_process';
import {mkdir, writeFile, readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, join} from 'node:path';

const project=resolve('research/formal-logic'), base=process.argv[2], output=resolve(process.argv[3]);
await mkdir(output,{recursive:true});
const helper=spawn(process.execPath,[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{
 buffer=Buffer.concat([buffer,chunk]);
 while(buffer.length>=4){
  const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;
  const value=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);
  const item=waiting.shift();clearTimeout(item.timer);
  value.ok?item.resolve(value.result):item.reject(Error(value.error));
 }
});
function call(message){return new Promise((resolve,reject)=>{
 const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);
 waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);
 size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));
});}
const evaluate=expression=>call({op:'eval',expression});
const report={schema:'bl.wide-request-browser.v1',base,checks:[],screenshots:[],started:new Date().toISOString()};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
const section='#s-one-request-more-theories';
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});
  await call({op:'navigate',url:base+'/#one-request-more-theories'});
  await call({op:'wait',expression:`document.querySelector('${section}').getClientRects().length>0`});
  check(size.name+': chapter deep link opens the actual pane',await evaluate(`document.querySelector('${section}').getClientRects().length>0`));
  check(size.name+': 94 original cells retained without authoring errors',await evaluate("document.querySelectorAll('.cell').length===94&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors,.ms-errors').length===0"));
  check(size.name+': admission, reports, points and proof are separately explained',await evaluate(`(()=>{const t=document.querySelector('${section}').innerText;return ['Can these terms enter?','What did the engine report?','Does this point work?','Does this argument prove it?'].every(x=>t.includes(x))})()`));
  check(size.name+': wide replay and SDK limits stay explicit',await evaluate(`(()=>{const t=document.querySelector('${section}').innerText;return t.includes('point interpreter and proof strategies are not installed')&&t.includes('prototype beside the selected SDK')&&t.includes('per-query deadlines')})()`));
  check(size.name+': actual pure evidence is scoped',await evaluate(`(()=>{const t=document.querySelector('${section}').innerText;return t.includes('424')&&t.includes('187')&&t.includes('6')&&t.toLowerCase().includes('whole-source capacity limits')})()`));
  check(size.name+': all common operations are present',await evaluate(`(()=>{const t=document.querySelector('${section} pre').innerText;return ['prepare-request','compare-evidence','propose-evidence','recheck-evidence','wide-native-policy'].every(x=>t.includes(x))})()`));
  check(size.name+': actual native sample keeps unavailable support visible',await evaluate(`(()=>{const t=document.querySelector('${section}').innerText;return t.includes('330 assertions')&&t.includes('Generic sequence empty/unit length')&&t.includes('Unsupported')&&t.includes('Signed zeros are structurally equal')})()`));
  check(size.name+': two independent cold readers remain separate from native execution',await evaluate(`(()=>{const t=document.querySelector('${section}').innerText;return t.includes('Two separate cold processes')&&t.includes('zero native exchanges and zero oracle calls')})()`));
  for(const [name,theme] of [['day','light'],['night','dark']]){
   const actual=await evaluate("document.documentElement.dataset.theme==='dark'?'dark':'light'");
   if(actual!==theme)await call({op:'click',selector:'#theme'});
   check(size.name+': requested theme '+name,await evaluate(`(document.documentElement.dataset.theme==='dark'?'dark':'light')==='${theme}'`));
   check(size.name+': no document overflow '+name,await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
   await evaluate("document.getElementById('one-request-more-theories').scrollIntoView({block:'start',behavior:'instant'})");
   await shot(size.name+'-wide-introduction-'+name);
   await evaluate("document.getElementById('four-separate-promises').scrollIntoView({block:'start',behavior:'instant'})");
   check(size.name+': four judgment rows remain readable '+name,await evaluate(`(()=>{const e=document.querySelector('${section} .rosetta');return e&&e.getBoundingClientRect().width<=innerWidth&&getComputedStyle(e).fontSize!=='0px'})()`));
   await shot(size.name+'-wide-judgments-'+name);
   await evaluate("document.getElementById('what-feels-native-in-beam-lisp').scrollIntoView({block:'start',behavior:'instant'})");
   await shot(size.name+'-wide-language-'+name);
   await evaluate("document.getElementById('what-the-actual-owners-report').scrollIntoView({block:'start',behavior:'instant'})");
   await shot(size.name+'-wide-native-top-'+name);
   await evaluate(`document.querySelectorAll('${section} .rosetta')[1].lastElementChild.scrollIntoView({block:'center',behavior:'instant'})`);
   await shot(size.name+'-wide-native-bottom-'+name);
   await evaluate("document.getElementById('make-saved-answers-lighter').scrollIntoView({block:'start',behavior:'instant'})");
   await shot(size.name+'-wide-reference-cost-'+name);
  }
  // Cross-pane navigation and direct links must work with the added chapter.
  await call({op:'click',selector:section+' .pager .next'});
  await call({op:'wait',expression:"document.querySelector('#s-try-the-language-ideas').getClientRects().length>0"});
  check(size.name+': next opens language ideas',await evaluate("document.querySelector('#s-try-the-language-ideas').getClientRects().length>0"));
  await call({op:'click',selector:'#s-try-the-language-ideas .pager .prev'});
  await call({op:'wait',expression:`document.querySelector('${section}').getClientRects().length>0`});
  check(size.name+': previous returns to the wide chapter',await evaluate(`document.querySelector('${section}').getClientRects().length>0`));
 }
 for(const path of ['evidence/wide-owner-prototype/pure/qualification.json',
                    'evidence/wide-owner-prototype/native-smoke/qualification.json',
                    'evidence/wide-owner-prototype/native-smoke/observations.json',
                    'evidence/wide-owner-prototype/native-smoke/projected/checks/wide-owner-native-check.bl',
                    'evidence/wide-owner-prototype/native-smoke/reader-one/qualification.json',
                    'evidence/wide-owner-prototype/native-smoke/reader-two/qualification.json',
                    'evidence/wide-owner-prototype/reader-profile/qualification.json',
                    'evidence/wide-owner-prototype/reader-profile-components/qualification.json',
                    'proposals/evidence-reference-review.md','prototypes/wide-owner/formal/request-evidence.bl',
                    'prototypes/wide-owner/formal/logic.bl',
                    'prototypes/wide-owner/formal/point-profile.bl','prototypes/wide-owner/README.md',
                    'prototypes/wide-owner/wide-owner-native-check.bl','prototypes/wide-readers/candidate-reader.bl',
                    'proposals/wide-theory-request-interface.md']){
  const response=await fetch(base+'/'+path),bytes=Buffer.from(await response.arrayBuffer());
  check('Exact declared source: '+path,response.status===200&&createHash('sha256').update(bytes).digest('hex')===createHash('sha256').update(await readFile(join(project,path))).digest('hex'));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};report.checks.push({name:'Focused audit completed',passed:false,error:error.message});}
finally{
 try{await call({op:'stop'});}catch{}
 helper.stdin.end();if(helper.exitCode===null)await new Promise(resolve=>helper.once('exit',resolve));
 report.passed=report.checks.every(row=>row.passed);report.finished=new Date().toISOString();
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,screenshots:report.screenshots.length}));
 process.exitCode=report.passed?0:1;
}
