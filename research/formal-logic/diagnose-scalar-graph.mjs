import {spawn} from 'node:child_process';
import {mkdir, writeFile, readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve, join} from 'node:path';

const project = resolve('research/formal-logic'), base = process.argv[2], output = resolve(process.argv[3]);
await mkdir(output, {recursive: true});
const helper = spawn(process.execPath, [join(project, 'browser-driver.mjs'), output], {stdio: ['pipe', 'pipe', 'inherit']});
let buffer = Buffer.alloc(0), waiting = [];
helper.stdout.on('data', chunk => {
 buffer = Buffer.concat([buffer, chunk]);
 while (buffer.length >= 4) {
  const n = buffer.readUInt32BE(0);
  if (buffer.length < n + 4) break;
  const value = JSON.parse(buffer.subarray(4, n + 4).toString());
  buffer = buffer.subarray(4 + n);
  const request = waiting.shift();
  clearTimeout(request.timer);
  value.ok ? request.resolve(value.result) : request.reject(Error(value.error));
 }
});
function call(message) {
 return new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(Error('Browser helper deadline')), 35000);
  waiting.push({resolve, reject, timer});
  const body = Buffer.from(JSON.stringify(message)), size = Buffer.alloc(4);
  size.writeUInt32BE(body.length);
  helper.stdin.write(Buffer.concat([size, body]));
 });
}
const evaluate = expression => call({op: 'eval', expression});

const report={schema:'bl.scalar-graph-geometry.v1',frames:[],views:[]};
const box=b=>({x:b.x,y:b.y,width:b.width,height:b.height});
try {
 await call({op:'open',width:390,height:844,mobile:true});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]) {
  await call({op:'viewport',...size});
  await call({op:'navigate',url:base+'/#let-each-kind-of-evidence-say-exactly-what-it-checked'});
  await evaluate("document.querySelector('svg.graph[aria-label=\"One question, explicit evidence\"]').scrollIntoView({block:'center',behavior:'instant'})");
  const geometry=await evaluate(`(()=>{
   const g=document.querySelector('svg.graph[aria-label="One question, explicit evidence"]');
   const box=b=>({x:b.x,y:b.y,width:b.width,height:b.height});
   const nodes=[...g.querySelectorAll('.gr-node')].map(n=>{const r=n.querySelector('rect').getBBox();return {rect:box(r),texts:[...n.querySelectorAll('text')].map(t=>{const b=t.getBBox();return {text:t.textContent,box:box(b),inside:b.x>=r.x+3&&b.x+b.width<=r.x+r.width-3&&b.y>=r.y&&b.y+b.height<=r.y+r.height}})}});
   return {theme:document.documentElement.dataset.theme,visible:box(g.getBoundingClientRect()),nodes,edges:[...g.querySelectorAll('.gr-edge text')].map(t=>{const b=t.getBBox();return {text:t.textContent,box:box(b),overlaps:nodes.filter(n=>{const r=n.rect;return !(b.x+b.width<=r.x||b.x>=r.x+r.width||b.y+b.height<=r.y||b.y>=r.y+r.height)}).map(n=>n.texts.map(t=>t.text))}})};
  })()`);
  report.views.push({size:size.name,...geometry});
  const frame=size.name+'-actual-evidence-graph.png';
  await call({op:'screenshot',path:join(output,frame)});report.frames.push(frame);
 }
} finally {
 try {await call({op:'stop'});}catch{}
 helper.stdin.end();if(helper.exitCode===null)await new Promise(resolve=>helper.once('exit',resolve));
 await writeFile(join(output,'geometry.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({views:report.views.length,frames:report.frames.length}));
}
