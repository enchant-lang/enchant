// Inspect a captured read-only handoff; no server, write route or new BL VM.
import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join} from 'node:path';
const project=resolve('research/formal-logic'), output=join(project,'evidence/project-handoff');
const helper=spawn(process.execPath,[join(project,'browser-driver.mjs'),output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){
 const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;
 const value=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);
 const item=waiting.shift();clearTimeout(item.timer);value.ok?item.resolve(value.result):item.reject(Error(value.error));
}});
function call(message){return new Promise((resolve,reject)=>{
 const timer=setTimeout(()=>reject(Error('Browser deadline')),35000);waiting.push({resolve,reject,timer});
 const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));
});}
const evaluate=expression=>call({op:'eval',expression});
const report={scope:'Read-only captured Org handoff; no authorized note/approval save or live-refresh qualification.',checks:[],frames:[]};
function check(name,ok){report.checks.push({name,passed:Boolean(ok)});if(!ok)throw Error(name);}
async function shot(name){await call({op:'screenshot',path:join(output,name)});report.frames.push(name);}
try{
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});
  for(const [theme,value] of [['day','light'],['night','dark']]){
   await evaluate("(()=>{try{localStorage.clear()}catch{}return true})()");
   await call({op:'navigate',url:'file://'+join(output,'index.html')+'?capture='+size.name+'-'+theme+'#a-good-place-to-start-again'});
   await evaluate(`document.documentElement.dataset.theme='${value}'`);
   check(size.name+' '+theme+': introduction visible',await evaluate("document.querySelector('#s-a-good-place-to-start-again').getClientRects().length>0"));
   check(size.name+' '+theme+': no document overflow',await evaluate('document.documentElement.scrollWidth<=innerWidth+2'));
   await shot(size.name+'-intro-'+theme+'.png');
   await evaluate("location.hash='find-a-focused-piece-of-work'");
   await call({op:'wait',expression:"document.querySelector('#roster-formal-workstreams').getClientRects().length>0"});
   check(size.name+' '+theme+': all native tasks present',await evaluate("document.querySelectorAll('[data-roster-panel]').length===18&&document.querySelectorAll('.or-errors').length===0"));
   check(size.name+' '+theme+': nine workstreams',await evaluate("document.querySelector('[data-roster-area]').options.length===10"));
   check(size.name+' '+theme+': selected task has a next action',await evaluate("[...document.querySelectorAll('[data-roster-panel]')].some(p=>p.dataset.rosterPanel==='FL01'&&!p.hidden&&p.innerText.includes('Resume the remaining serial phases'))"));
   const scope=await evaluate("(()=>{const s=document.querySelector('[data-roster-area]');s.value='Evidence';s.dispatchEvent(new Event('change',{bubbles:true}));return s.value})()");
   check(size.name+' '+theme+': workstream selection works',scope==='Evidence');
   if(size.mobile)await call({op:'click',selector:'[data-roster-picker]'});
   await call({op:'click',selector:'[data-roster-row="FL20"]'});
   check(size.name+' '+theme+': evidence brief opens',await evaluate("!document.querySelector('[data-roster-panel=\"FL20\"]').hidden"));
   await evaluate("document.querySelector('[data-roster-panel=\"FL20\"]').scrollIntoView({block:'start',behavior:'instant'})");
   check(size.name+' '+theme+': task content stays within viewport',await evaluate('document.documentElement.scrollWidth<=innerWidth+2'));
   check(size.name+' '+theme+': task review cannot write',await evaluate("[...document.querySelectorAll('[data-roster-panel=\"FL20\"] textarea')].every(e=>e.disabled)"));
   await shot(size.name+'-workstream-'+theme+'.png');
  }
 }
}catch(error){report.fatal=error.message;report.checks.push({name:error.message,passed:false});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();
 if(helper.exitCode===null)await new Promise(resolve=>helper.once('exit',resolve));
 report.passed=report.checks.every(row=>row.passed);
 report.document_sha256=createHash('sha256').update(await readFile(join(project,'PROJECT.bl.org'))).digest('hex');
 report.html_sha256=createHash('sha256').update(await readFile(join(output,'index.html'))).digest('hex');
 await writeFile(join(output,'browser.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,frames:report.frames.length}));
 process.exitCode=report.passed?0:1;
}
