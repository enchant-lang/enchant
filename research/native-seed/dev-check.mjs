// Qualify the live host against a disposable Org copy and a synthetic owner.
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile,appendFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const base=path.dirname(fileURLToPath(import.meta.url));
const url=process.env.NATIVE_REVIEW_QA_URL;
const source=process.env.NATIVE_REVIEW_QA_SOURCE;
assert.ok(url&&source,'Use a disposable QA document and localhost server');
const profile=await mkdtemp(path.join(tmpdir(),'native-review-qa-'));
const browser=spawn('chromium',['--headless=new','--no-sandbox','--disable-gpu',
 '--disable-dev-shm-usage','--disable-background-networking','--no-first-run',
 '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
let socket;
try {
 const address=await new Promise((resolve,reject)=>{let log='';
  const timer=setTimeout(()=>reject(new Error('browser startup timeout')),20000);
  browser.stderr.on('data',d=>{log+=d;const found=log.match(/DevTools listening on (ws:\/\/\S+)/);
   if(found){clearTimeout(timer);resolve(found[1]);}});
  browser.on('exit',code=>{clearTimeout(timer);reject(new Error('browser exited '+code));});});
 const pages=await(await fetch('http://'+new URL(address).host+'/json/list')).json();
 socket=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let seq=0;const pending=new Map(),errors=[];
 socket.onmessage=e=>{const m=JSON.parse(e.data);
  if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);
  const p=pending.get(m.id);if(p){pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(m.error):p.resolve(m.result);}};
 const cdp=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;
  const timer=setTimeout(()=>{pending.delete(id);reject(new Error(method+' timeout'));},25000);
  pending.set(id,{resolve,reject,timer});socket.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;};
 const wait=expression=>evaluate(`new Promise((resolve,reject)=>{const until=Date.now()+15000;const timer=setInterval(()=>{if(${expression}){clearInterval(timer);resolve(true)}else if(Date.now()>until){clearInterval(timer);reject(new Error('condition timed out'))}},100)})`);
 await cdp('Page.enable');await cdp('Runtime.enable');await cdp('Network.enable');
 await cdp('Network.setExtraHTTPHeaders',{headers:{'Tailscale-User-Login':'native-seed-qa@example.test'}});
 await cdp('Emulation.setDeviceMetricsOverride',{width:412,height:915,deviceScaleFactor:1,mobile:true});
 await cdp('Page.navigate',{url:url+'/#all'});
 await wait('document.querySelector("#review-body")&&!document.querySelector("#review-body").disabled');
 await evaluate('document.querySelector(\'[data-review-target="block:use-jolt"] > .review-trigger\').click()');
 await evaluate('document.querySelector("#review-body").value="Live development persistence probe";document.querySelector("#review-body").dispatchEvent(new Event("input",{bubbles:true}));document.querySelector(".review-compose [type=submit]").click()');
 await wait('document.querySelector("#review-body").value===""');
 assert.match(await readFile(source,'utf8'),/Live development persistence probe/);
 await cdp('Page.reload');
 await wait('document.querySelector("#review-body")&&!document.querySelector("#review-body").disabled');
 const persisted=await evaluate('(async()=>{const r=await fetch("/review");const s=await r.json();return s.comments.some(c=>c.body==="Live development persistence probe"&&c.author==="native-seed-qa")})()');
 assert.ok(persisted);
 await evaluate('document.querySelector("#review-toggle").click();document.querySelector("#review-body").value="Preserve this development draft";document.querySelector("#review-body").dispatchEvent(new Event("input",{bubbles:true}))');
 await appendFile(source,'\nLive development refresh probe.\n');
 await wait('document.body.innerText.includes("Live development refresh probe.")');
 assert.equal(await evaluate('document.querySelector("#review-body").value'),'Preserve this development draft');
 assert.equal((await fetch(url+'/review',{method:'POST',headers:{'content-type':'application/json'},body:'{"id":"denied","body":"denied"}'})).status,403);
 assert.equal((await fetch(url+'/answer',{method:'POST',headers:{'content-type':'application/json'},body:'{"id":"use-jolt","answer":"Agree"}'})).status,403);
 assert.deepEqual(errors,[]);
 await writeFile(path.join(base,'evidence/dev-phone.png'),Buffer.from((await cdp('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await writeFile(path.join(base,'evidence/dev-browser.json'),JSON.stringify({status:'pass',
  checks:['owner browser save','native Org persistence','saved comment survives reload','live document refresh',
   'draft survives refresh','anonymous comments denied','anonymous answers denied','no script exceptions'],errors},null,2)+'\n');
 console.log('LIVE_DEV_BROWSER_OK');
}finally{
 socket?.close();browser.kill('SIGTERM');
 await new Promise(resolve=>{if(browser.exitCode!==null)resolve();else browser.once('exit',resolve);});
 await rm(profile,{recursive:true,force:true});
}
