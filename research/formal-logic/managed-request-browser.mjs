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
const report = {schema: 'enchant.formal.managed-request-browser.v1', base, checks: [], screenshots: [], started: new Date().toISOString()};
function check(name, ok) {
 report.checks.push({name, passed: Boolean(ok)});
 if (!ok) throw Error(name);
}
async function shot(name) {
 await call({op: 'screenshot', path: join(output, name + '.png')});
 report.screenshots.push(name + '.png');
}
const chapter = 'one-portable-request-either-backend';
try {
 await call({op: 'open', width: 390, height: 844, mobile: true});
 for (const size of [{name: 'phone', width: 390, height: 844, mobile: true}, {name: 'desktop', width: 1440, height: 1000, mobile: false}]) {
  await call({op: 'viewport', ...size});
  await call({op: 'navigate', url: base + '/#' + chapter});
  check(size.name + ': all 88 cells present; no authoring failures', await evaluate("document.querySelectorAll('.cell').length===88&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name + ': no page overflow', await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name + ': question and backend choice are explained together', await evaluate("document.body.innerText.includes('One portable request, either backend')&&document.body.innerText.includes('A backend choice changes how we ask, not what we ask.')"));
  check(size.name + ': graph keys and shared checker scope are explicit', await evaluate("document.body.innerText.includes('Unfamiliar application keys stay data')&&document.body.innerText.includes('The owner and reader share the SDK checker')"));
  check(size.name + ': point and proof authority remain separate', await evaluate("document.body.innerText.includes('A useful witness is not a compiler theorem')&&document.body.innerText.includes('unchecked UNSAT')"));
  for (const theme of ['day', 'night']) {
   if (theme === 'night') await call({op: 'click', selector: '#theme'});
   await evaluate(`window.scrollBy({top:document.getElementById('${chapter}').getBoundingClientRect().top-92,behavior:'instant'})`);
   await shot(size.name + '-request-chapter-' + theme);
  }
  await call({op: 'click', selector: '#theme'});
  await call({op: 'navigate', url: base + '/#s-the-model-running'});
  await evaluate("document.querySelector('#cell-story-formal-request').scrollIntoView({block:'center',behavior:'instant'})");
  check(size.name + ': real request result is visible', await evaluate("(()=>{const r=document.querySelector('#cell-story-formal-request .result').getBoundingClientRect();return r.width>0&&r.height>0&&r.bottom>90&&r.top<innerHeight})()"));
  const result = await evaluate("document.querySelector('#cell-story-formal-request .result')?.innerText||''");
  check(size.name + ': both backends and canonical product are visible', result.includes(':backend :z3') && result.includes(':backend :oxiz') && result.includes(':product {:formal/real [2 15]}'));
  check(size.name + ': original subject and raw graph cursors are retained', result.includes(':same-subject true') && result.includes(':observations :graph-source-cursors') && result.includes(':materialization :deferred'));
  check(size.name + ': fresh point replay and local delegation stay distinct', result.includes(':validation :valid') && result.includes(':delegation :matching-response') && result.includes(':checked-native-execution false'));
  check(size.name + ': handler point and saved point are rechecked', result.includes(':supplied-point :sat') && result.includes(':supplied-native-attempts 0') && result.includes(':reopened-point :sat') && result.includes(':changed-point :invalid-point'));
  check(size.name + ': no certificate or compiler authority is inferred', result.includes(':certificate :not-checked') && result.includes(':compiler-proof-authority false'));
  await shot(size.name + '-request-cell-day');
  await call({op: 'click', selector: '#theme'});
  await evaluate("document.querySelector('#cell-story-formal-request').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name + '-request-cell-night');
  await call({op: 'click', selector: '#theme'});
 }
 for (const path of ['REQUEST-INTERFACE.md', 'MANAGED-GRAPH.md', 'src/formal/question-forest.bl', 'sdk-src/formal/request.bl', 'sdk-src/formal/request-runtime.bl', 'sdk-src/formal/request-point.bl', 'sdk-src/formal/request-answer.bl', 'sdk-src/formal/graph-question.bl', 'sdk-src/formal/coordinates.bl', 'sdk-src/formal/request-record.bl', 'evidence/managed-graph/qualification.json', 'evidence/managed-integration/qualification.json']) {
  const response = await fetch(base + '/' + path), body = Buffer.from(await response.arrayBuffer());
  check('Exact declared source: ' + path, response.status === 200 && createHash('sha256').update(body).digest('hex') === createHash('sha256').update(await readFile(join(project, path))).digest('hex'));
 }
} catch (error) {
 report.fatal = {message: error.message, stack: error.stack};
 report.checks.push({name: 'Focused audit completed', passed: false, error: error.message});
} finally {
 try {await call({op: 'stop'});} catch {}
 helper.stdin.end();
 if (helper.exitCode === null) await new Promise(resolve => helper.once('exit', resolve));
 report.passed = report.checks.every(row => row.passed);
 report.finished = new Date().toISOString();
 await writeFile(join(output, 'audit.json'), JSON.stringify(report, null, 2) + '\n');
 console.log(JSON.stringify({passed: report.passed, checks: report.checks.length, screenshots: report.screenshots.length}));
 process.exitCode = report.passed ? 0 : 1;
}
