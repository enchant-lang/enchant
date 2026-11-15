// Inspect the actual dossier renderer through Chromium's CDP. No browser SDK.
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, writeFile, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const base=path.dirname(fileURLToPath(import.meta.url));
const sha=async file=>createHash('sha256').update(await readFile(file)).digest('hex');
await rm(path.join(base,'evidence/browser.json'),{force:true});
const profile=await mkdtemp(path.join(tmpdir(),'bl-native-review-'));
const browser=spawn('chromium',['--headless=new','--no-sandbox','--disable-gpu',
  '--disable-dev-shm-usage','--disable-background-networking','--no-first-run',
  '--renderer-process-limit=1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
  {stdio:['ignore','ignore','pipe']});
let socket;
try {
 const address=await new Promise((resolve,reject)=>{
  let log='';const timer=setTimeout(()=>reject(new Error('Chromium startup timeout')),20000);
  browser.stderr.on('data',data=>{log+=data;const found=log.match(/DevTools listening on (ws:\/\/\S+)/);
   if(found){clearTimeout(timer);resolve(found[1]);}});
  browser.on('exit',code=>{clearTimeout(timer);reject(new Error('Chromium exited '+code));});
 });
 const endpoint=new URL(address);
 const pages=await (await fetch('http://'+endpoint.host+'/json/list')).json();
 socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let seq=0;const pending=new Map(),errors=[];
 socket.onmessage=event=>{const m=JSON.parse(event.data);
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);
  const p=pending.get(m.id);if(p){pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(m.error):p.resolve(m.result);}};
 const cdp=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;
  const timer=setTimeout(()=>{pending.delete(id);reject(new Error(method+' timeout'));},20000);
  pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 await cdp('Page.enable');await cdp('Runtime.enable');
 await cdp('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1,mobile:true});
 await cdp('Page.navigate',{url:pathToFileURL(path.join(base,'evidence/native-seed.html')).href});
 await evaluate('new Promise(r=>document.readyState==="complete"?r():addEventListener("load",r,{once:true}))');
 const checks={};
 checks.noAuthoringErrors=await evaluate('!document.body.innerText.includes("Review authoring errors")');
 checks.phoneOverflow=await evaluate('document.documentElement.scrollWidth<=innerWidth');
 assert.ok(checks.noAuthoringErrors);assert.ok(checks.phoneOverflow);
 await writeFile(path.join(base,'evidence/phone.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('location.hash="#all";new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
 checks.checkedReaderEvidence=await evaluate('document.body.innerText.includes("8.15×")&&document.body.innerText.includes("whole-compiler speed gate failing")&&document.querySelector("#cell-checked-reader-vertical .result").textContent.includes(":native-checks 77")');
 assert.ok(checks.checkedReaderEvidence);
 await evaluate('window.scrollTo(0,document.querySelector(\'[data-review-label="One complete checked experiment"]\').previousElementSibling.getBoundingClientRect().top+scrollY-80)');
 await writeFile(path.join(base,'evidence/checked-reader-phone.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.documentElement.dataset.theme="dark"');
 await writeFile(path.join(base,'evidence/checked-reader-phone-dark.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.documentElement.dataset.theme="light"');
 await evaluate('window.delivery=document.querySelector(\'[data-milestones="native-devtool"]\')');
 checks.deliveryStartsAtBaseline=await evaluate('delivery.querySelector(\'[data-milestone-detail="measure"]\').hidden===false');
 checks.deliveryNext=await evaluate('delivery.querySelector(\'[data-milestone-move="1"]\').click();delivery.querySelector(\'[data-milestone-detail="core-speed"]\').hidden===false');
 checks.deliveryDependency=await evaluate('delivery.querySelector(\'[data-milestone-detail="core-speed"] [data-milestone-to="measure"]\').click();delivery.querySelector(\'[data-milestone-detail="measure"]\').hidden===false');
 await evaluate('window.scrollTo(0,delivery.getBoundingClientRect().top+scrollY-110)');
 await writeFile(path.join(base,'evidence/native-roadmap-phone.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate(`window.scrollTo(0,document.querySelector('[data-review-label="Incrementality stays in BL"]').getBoundingClientRect().top+scrollY-110)`);
 checks.allSectionsPhoneOverflow=await evaluate('document.documentElement.scrollWidth<=innerWidth');
 await writeFile(path.join(base,'evidence/incremental-graph-phone.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate(`window.scrollTo(0,document.querySelector('[data-review-label="An edit keeps old native closures alive"]').getBoundingClientRect().top+scrollY-110)`);
 await writeFile(path.join(base,'evidence/incremental-closures-phone.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('window.graph=document.querySelector(".screen-graph[data-start=policy]");graph.scrollIntoView()');
 checks.connectedNavigation=await evaluate('graph.querySelector(".sg-view:not([hidden]) [data-sg-to=control]").click();graph.querySelector(".sg-view[data-view=control]").hidden===false');
 checks.back=await evaluate('graph.querySelector("[data-sg-back]").click();graph.querySelector(".sg-view[data-view=policy]").hidden===false');
 checks.graphMode=await evaluate('graph.querySelector("[data-sg-mode]").click();graph.classList.contains("sg-graph-mode")');
 checks.mapSelection=await evaluate('graph.querySelector(".sg-nodes [data-sg-to=values]").click();graph.querySelector(".sg-view[data-view=values]").hidden===false');
 checks.fullscreen=await evaluate('graph.querySelector("[data-sg-expand]").click();graph.classList.contains("sg-expanded")');
 await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
 checks.escape=await evaluate('!graph.classList.contains("sg-expanded")');
 await evaluate('graph.querySelector("[data-sg-reset]").click();document.documentElement.dataset.theme="dark";graph.scrollIntoView()');
 await writeFile(path.join(base,'evidence/phone-dark-detail.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 checks.desktopOverflow=await evaluate('document.documentElement.scrollWidth<=innerWidth');
 await evaluate('document.documentElement.dataset.theme="light";graph.querySelector("[data-sg-mode]").click();graph.scrollIntoView()');
 await writeFile(path.join(base,'evidence/desktop-map.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 checks.noScriptExceptions=errors.length===0;
 for(const [name,passed] of Object.entries(checks))assert.ok(passed,name);
 await writeFile(path.join(base,'evidence/browser.json'),JSON.stringify({status:'pass',checks,errors,
  html_sha256:await sha(path.join(base,'evidence/native-seed.html')),
  source_sha256:await sha(path.join(base,'native-seed.bl.org')),
  browser_check_sha256:await sha(fileURLToPath(import.meta.url))},null,2)+'\n');
 console.log('DOSSIER_BROWSER_OK',Object.keys(checks).length,'checks');
} finally {
 socket?.close();browser.kill('SIGTERM');
 await new Promise(resolve=>{if(browser.exitCode!==null)resolve();else browser.once('exit',resolve);});
 await rm(profile,{recursive:true,force:true});
}
