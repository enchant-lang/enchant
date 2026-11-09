// Authorized writes exercise a disposable Org copy on a loopback-only host.
import {spawn} from 'node:child_process';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
const base=process.argv[2],fixture=resolve(process.argv[3]);
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)||!fixture.endsWith('/feedback-fixture.bl.org'))throw Error('Disposable loopback fixture required');
const canonical=resolve('research/formal-logic/ATLAS.bl.org');
const fingerprint=bytes=>createHash('sha256').update(bytes).digest('hex');
const before=fingerprint(await readFile(canonical));
const out=resolve('research/formal-logic/evidence/story/feedback-audit');await mkdir(out,{recursive:true});
const child=spawn('/home/othman/.nix-profile/bin/node',['research/formal-logic/browser-driver.mjs',out],{stdio:['pipe','pipe','inherit']});
let queue=[],buffer=Buffer.alloc(0);
child.stdout.on('data',b=>{buffer=Buffer.concat([buffer,b]);while(buffer.length>=4){const n=buffer.readUInt32BE();if(buffer.length<n+4)break;const value=JSON.parse(buffer.subarray(4,n+4));buffer=buffer.subarray(n+4);const p=queue.shift();clearTimeout(p.timer);value.ok?p.resolve(value.result):p.reject(Error(value.error));}});
const call=m=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser deadline')),35000);queue.push({resolve,reject,timer});const b=Buffer.from(JSON.stringify(m)),h=Buffer.alloc(4);h.writeUInt32BE(b.length);child.stdin.write(Buffer.concat([h,b]));});
const evaluate=expression=>call({op:'eval',expression});
const click=selector=>call({op:'click',selector});const wait=expression=>call({op:'wait',expression});
const form='#roster-formal-work [data-task="FL-EQUALITY"]';
const report={schema:'enchant.formal.feedback-browser-audit.v1',scope:'Disposable Org fixture; fixed test identity; loopback host; no review submitted to the canonical dossier.',checks:[]};
const check=(name,passed)=>{report.checks.push({name,passed:Boolean(passed)});if(!passed)throw Error(name);};
try{
 await call({op:'open',width:1440,height:1000,mobile:false});
 await call({op:'headers',headers:{'Tailscale-User-Login':'formal-review-test@example.invalid'}});
 await call({op:'navigate',url:base+'/#s-a-path-we-can-actually-build'});
 await wait(`!!document.querySelector('${form}')`);
 await click('#roster-formal-work [data-roster-detail="FL-EQUALITY"] .or-note>summary');
 const note='Fixture review: keep the exact-value law visible.';
 await call({op:'fill',selector:form+' textarea',text:note});
 await call({op:'block',urls:['*/roster-note']});await click(form+' button[type="submit"]');
 await wait(`/(fail|error|could not|unable)/i.test(document.querySelector('${form} .or-save-state').innerText)`);
 check('A failed HTTP write preserves the typed note',await evaluate(`document.querySelector('${form} textarea').value===${JSON.stringify(note)}`));
 check('A failed write does not alter the source',!(await readFile(fixture,'utf8')).includes(note));
 await call({op:'block',urls:['https://fonts.googleapis.com/*','https://fonts.gstatic.com/*']});
 await click(form+' button[type="submit"]');
 await wait(`document.querySelector('${form} .or-save-state').innerText.includes('Saved')`);
 check('Authorized UI save writes the selected task in Org',(await readFile(fixture,'utf8')).includes(':REVIEW_NOTE: '+note));
 await call({op:'navigate',url:base+'/?reload=1#s-a-path-we-can-actually-build'});
 await wait(`!!document.querySelector('${form} textarea')`);
 check('Saved review reloads through the HTTP page',await evaluate(`document.querySelector('${form} textarea').value===${JSON.stringify(note)}`));
 const draft='Unsaved fixture draft survives live refresh.';
 await call({op:'fill',selector:form+' textarea',text:draft});
 await writeFile(fixture,(await readFile(fixture,'utf8'))+'\n');
 await new Promise(r=>setTimeout(r,6500));
 check('Live refresh preserves the active draft',await evaluate(`document.querySelector('${form} textarea').value===${JSON.stringify(draft)}`));
 check('Live refresh preserves selected work',await evaluate("document.querySelector('#roster-formal-work').dataset.rosterSelected==='FL-EQUALITY'"));
 check('The draft is not saved without an explicit submit',!(await readFile(fixture,'utf8')).includes(draft));
 await call({op:'screenshot',path:join(out,'saved-and-draft.png')});
 await click('#ask-formal-first-boundary .fb-opts button:first-child');
 await click('#ask-formal-first-boundary button[type="submit"]');
 await wait("document.querySelector('#ask-formal-first-boundary .fb-state').innerText.includes('answered')");
 check('An explicit dossier reaction saves on its block header',/begin_ask[^\n]*formal-first-boundary[^\n]*:answer/.test(await readFile(fixture,'utf8')));
 check('Anonymous POST remains denied',(await fetch(base+'/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"id":"formal-first-boundary","answer":"A"}'})).status===403);
 check('Canonical reader answers remain untouched',fingerprint(await readFile(canonical))===before);
}catch(error){report.fatal={message:error.message,stack:error.stack};process.exitCode=1;}
finally{
 await call({op:'stop'}).catch(()=>{});child.stdin.end();report.passed=!report.fatal&&report.checks.every(c=>c.passed);
 await writeFile(join(out,'audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}
