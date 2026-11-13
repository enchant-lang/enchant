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
const report = {schema: 'bl.word-request-browser.v1', base, checks: [], screenshots: [], started: new Date().toISOString()};
function check(name, ok) {
 report.checks.push({name, passed: Boolean(ok)});
 if (!ok) throw Error(name);
}
async function shot(name) {
 await call({op: 'screenshot', path: join(output, name + '.png')});
 report.screenshots.push(name + '.png');
}
const chapter = 'one-number-one-value';
async function theme(value) {
 const actual = await evaluate("document.documentElement.dataset.theme==='dark'?'dark':'light'");
 if (actual !== value) await call({op: 'click', selector: '#theme'});
 check('Theme is ' + value, await evaluate("(document.documentElement.dataset.theme==='dark'?'dark':'light')===" + JSON.stringify(value)));
}
try {
 await call({op: 'open', width: 390, height: 844, mobile: true});
 for (const size of [{name: 'phone', width: 390, height: 844, mobile: true}, {name: 'desktop', width: 1440, height: 1000, mobile: false}]) {
  await call({op: 'viewport', ...size});
  await call({op: 'navigate', url: base + '/#' + chapter});
  check(size.name + ': all 91 cells present; no authoring failures', await evaluate("document.querySelectorAll('.cell').length===91&&document.querySelectorAll('.cell.failed,.review-errors,.nb-errors').length===0&&!document.body.innerText.includes('Review authoring errors')"));
  check(size.name + ': no page overflow', await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
  check(size.name + ': value, representation and remaining keys are explained', await evaluate("document.body.innerText.includes('One number, one value')&&document.body.innerText.includes('same-representation?')&&document.body.innerText.includes('Unifying language collection keys is the next semantic implementation')"));
  check(size.name + ': whole-program substitution retains its domain', await evaluate("document.body.innerText.includes('Does equal mean interchangeable in every program?')&&document.body.innerText.includes('Each operation needs its own outcome and effect rules')"));
  for (const [name, value] of [['day', 'light'], ['night', 'dark']]) {
   await theme(value);
   await evaluate(`window.scrollBy({top:document.getElementById('${chapter}').getBoundingClientRect().top-92,behavior:'instant'})`);
   await shot(size.name + '-numbers-chapter-' + name);
   check(size.name + ': meaning graph captions fit their boxes in ' + name, await evaluate(`(()=>{
    const graph=document.querySelector('svg.graph[aria-label="Meaning stays with Beam Lisp"]');
    if(!graph||graph.querySelectorAll('.gr-node').length!==5)return false;
    const boxes=[...graph.querySelectorAll('.gr-node rect')].map(n=>n.getBBox());
    const inside=[...graph.querySelectorAll('.gr-node')].every(n=>{
     const r=n.querySelector('rect').getBBox();
     return [...n.querySelectorAll('text')].every(t=>{const b=t.getBBox();return b.x>=r.x+3&&b.x+b.width<=r.x+r.width-3&&b.y>=r.y&&b.y+b.height<=r.y+r.height});
    });
    const clear=[...graph.querySelectorAll('.gr-edge text')].every(t=>{const b=t.getBBox();return boxes.every(r=>b.x+b.width<=r.x||b.x>=r.x+r.width||b.y+b.height<=r.y||b.y>=r.y+r.height)});
    return inside&&clear;
   })()`));
   await evaluate(`document.querySelector('svg.graph[aria-label="Meaning stays with Beam Lisp"]').scrollIntoView({block:'center',behavior:'instant'})`);
   await shot(size.name + '-numbers-meaning-' + name);
   await evaluate("document.querySelector('.nb-waterfall').scrollIntoView({block:'center',behavior:'instant'})");
   check(size.name + ': observed bridge retains its exact counts in ' + name, await evaluate("(()=>{const n=id=>document.querySelector('.nb-waterfall [data-nb-wf=\"'+id+'\"] .nb-v').textContent.trim();return n('numeric_js_before')==='14'&&n('numeric_js_fixed')==='14'&&n('numeric_js_after')==='0'})()"));
   await shot(size.name + '-numbers-bridge-' + name);
  }
  await theme('light');
  await call({op: 'click', selector: '.nb-waterfall [data-nb="numeric_js_fixed"]'});
  check(size.name + ': bridge explains the calculation', await evaluate("!document.querySelector('#nb-pop').hidden&&document.querySelector('#nb-pop .nb-pop-value').textContent.trim().startsWith('14')&&!!document.querySelector('#nb-pop [data-nb-open=\"numeric_js_before\"]')&&!!document.querySelector('#nb-pop [data-nb-open=\"numeric_js_after\"]')"));
  await call({op: 'click', selector: '#nb-pop [data-nb-open="numeric_js_before"]'});
  check(size.name + ': retained observation stays a fixed recorded quantity', await evaluate("document.querySelector('#nb-pop').textContent.includes('Earlier direct JS discrepancies')&&!document.querySelector('#nb-pop input[data-nb-input]')&&!!document.querySelector('#nb-pop a[href=\"/evidence/numeric-semantics/baseline/observation-summary.json\"]')"));
  await shot(size.name + '-numbers-source-inspector');
  await call({op: 'click', selector: '#nb-pop [data-nb-close]'});
  check(size.name + ': inspector closes through its visible control', await evaluate("document.querySelector('#nb-pop').hidden"));
  await call({op: 'navigate', url: base + '/#s-the-model-running'});
  await evaluate("document.querySelector('#cell-story-exact-numbers').scrollIntoView({block:'center',behavior:'instant'})");
  const result = await evaluate("document.querySelector('#cell-story-exact-numbers .result')?.innerText||''");
  check(size.name + ': actual transitivity and preserved scale are visible', result.includes(':transitive-triple [true true true]') && result.includes(':same-representation false') && result.includes(':retained-scale ["1.5M" "1.50M"]'));
  check(size.name + ': Float exactness and raw keys remain distinct', result.includes(':exact-tenth false') && result.includes(':exact-half true') && result.includes(':raw-map-key-count 2'));
  check(size.name + ': modulus, failure and measured counts are actual results', result.includes(':floor-modulus -2') && result.includes(':zero-divisor :raised') && result.includes(':measured-js-gaps-before 14') && result.includes(':measured-js-gaps-after 0'));
  check(size.name + ': compiler authority is not inferred', result.includes(':compiler-proof-authority false'));
  await shot(size.name + '-numbers-cell-day');
  await theme('dark');
  await evaluate("document.querySelector('#cell-story-exact-numbers').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name + '-numbers-cell-night');
  await theme('light');
 }
 for (const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]) {
  await call({op:'viewport',...size});
  await call({op:'navigate',url:base+'/#keep-every-assumption-with-the-question'});
  check(size.name+': retained assumptions and both lifetimes are explained',await evaluate("document.body.innerText.includes('Keep every assumption with the question')&&document.body.innerText.includes('There are two lifetimes.')&&document.body.innerText.includes('every retained assumption')&&!document.body.innerText.includes('=x = 7=')&&!document.body.innerText.includes('=x = 8=')"));
  for(const [name,value] of [['day','light'],['night','dark']]) {
   await theme(value);
   await evaluate("window.scrollBy({top:document.getElementById('keep-every-assumption-with-the-question').getBoundingClientRect().top-92,behavior:'instant'})");
   await shot(size.name+'-retained-chapter-'+name);
   check(size.name+': retained graph text fits in '+name,await evaluate(`(()=>{
    const g=document.querySelector('svg.graph[aria-label="Keep meaning portable, execution local"]');
    if(!g||g.querySelectorAll('.gr-node').length!==5)return false;
    const boxes=[...g.querySelectorAll('.gr-node rect')].map(n=>n.getBBox());
    const inside=[...g.querySelectorAll('.gr-node')].every(n=>{const r=n.querySelector('rect').getBBox();return [...n.querySelectorAll('text')].every(t=>{const b=t.getBBox();return b.x>=r.x+3&&b.x+b.width<=r.x+r.width-3&&b.y>=r.y&&b.y+b.height<=r.y+r.height})});
    return inside&&[...g.querySelectorAll('.gr-edge text')].every(t=>{const b=t.getBBox();return boxes.every(r=>b.x+b.width<=r.x||b.x>=r.x+r.width||b.y+b.height<=r.y||b.y>=r.y+r.height)});
   })()`));
   await evaluate(`document.querySelector('svg.graph[aria-label="Keep meaning portable, execution local"]').scrollIntoView({block:'center',behavior:'instant'})`);
   await shot(size.name+'-retained-meaning-'+name);
  }
  await theme('light');
  await call({op:'navigate',url:base+'/#s-the-model-running'});
  await evaluate("document.getElementById('cell-story-retained-request').scrollIntoView({block:'center',behavior:'instant'})");
  const result=await evaluate("document.querySelector('#cell-story-retained-request .result')?.innerText||''");
  check(size.name+': actual retained results cover both engines',result.includes(':subject :retained-complete-request')&&result.includes(':backend :z3')&&result.includes(':backend :oxiz')&&result.includes(':answer-version 3'));
  check(size.name+': caller-only and complete point meanings differ correctly',result.includes(':caller-only-eight :sat')&&result.includes(':complete-eight :invalid-point')&&result.includes(':reopened-point :sat'));
  check(size.name+': unused leases expire and supplied points avoid fallback',result.includes(':unused-callback :expired')&&result.includes(':supplied-fallback-attempts 0'));
  check(size.name+': actual external reader evidence stays separate',result.includes(':fresh-sdk-readers 2')&&result.includes(':saved-records 12')&&result.includes(':reader-solver-exchanges 0'));
  check(size.name+': history grants no native or compiler authority',result.includes(':checked-native-execution false')&&result.includes(':compiler-proof-authority false'));
  await shot(size.name+'-retained-cell-day');
  await theme('dark');
  await evaluate("document.getElementById('cell-story-retained-request').scrollIntoView({block:'center',behavior:'instant'})");
  await shot(size.name+'-retained-cell-night');
  await theme('light');
 }
 for (const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]) {
  await call({op:'viewport',...size});
  await call({op:'navigate',url:base+'/#a-byte-can-carry-its-meaning-across-both-solvers'});
  check(size.name+': word chapter explains width, budget and claim boundaries',await evaluate("document.body.innerText.includes('A byte can carry its meaning across both solvers')&&document.body.innerText.includes('Raising a work allowance cannot enlarge')&&document.body.innerText.includes('A native unsatisfiable answer remains a solver claim')"));
  for(const [name,value] of [['day','light'],['night','dark']]) {
   await call({op:'navigate',url:base+'/#a-byte-can-carry-its-meaning-across-both-solvers'});
   await theme(value);
   await evaluate("window.scrollBy({top:document.getElementById('a-byte-can-carry-its-meaning-across-both-solvers').getBoundingClientRect().top-92,behavior:'instant'})");
   await shot(size.name+'-word-chapter-'+name);
   check(size.name+': word graph text fits in '+name,await evaluate(`(()=>{
    const g=document.querySelector('svg.graph[aria-label="Width belongs to the question"]');
    if(!g||g.querySelectorAll('.gr-node').length!==5)return false;
    const boxes=[...g.querySelectorAll('.gr-node rect')].map(n=>n.getBBox());
    const inside=[...g.querySelectorAll('.gr-node')].every(n=>{const r=n.querySelector('rect').getBBox();return [...n.querySelectorAll('text')].every(t=>{const b=t.getBBox();return b.x>=r.x+3&&b.x+b.width<=r.x+r.width-3&&b.y>=r.y&&b.y+b.height<=r.y+r.height})});
    return inside&&[...g.querySelectorAll('.gr-edge text')].every(t=>{const b=t.getBBox();return boxes.every(r=>b.x+b.width<=r.x||b.x>=r.x+r.width||b.y+b.height<=r.y||b.y>=r.y+r.height)});
   })()`));
   await evaluate(`document.querySelector('svg.graph[aria-label="Width belongs to the question"]').scrollIntoView({block:'center',behavior:'instant'})`);
   await shot(size.name+'-word-meaning-'+name);
   await call({op:'navigate',url:base+'/#s-the-model-running'});
   await theme(value);
   await evaluate("window.scrollBy({top:document.getElementById('cell-story-word-request').getBoundingClientRect().top-110,behavior:'instant'})");
   check(size.name+': executed word cell is visible in '+name,await evaluate("(()=>{const c=document.getElementById('cell-story-word-request'),r=c.getBoundingClientRect();return c.getClientRects().length>0&&r.top>=90&&r.top<innerHeight&&r.bottom>r.top})()"));
   const result=await evaluate("document.querySelector('#cell-story-word-request .result')?.innerText||''");
   check(size.name+': actual byte wrapping and wrong-point rejection in '+name,result.includes(':eight-bit-wrap :sat')&&result.includes(':changed-counter :invalid-point')&&result.includes(':last-counter 255')&&result.includes(':next-counter 0'));
   check(size.name+': same named word policy on both engines in '+name,result.includes(':backend :z3')&&result.includes(':backend :oxiz')&&result.includes(':checking-policy :bl/managed-numeric-word-graph-preview-v1'));
   check(size.name+': actual graph replay and fresh indexed readers in '+name,result.includes(':graph-packet-replay :sat')&&result.includes(':saved-word-records 12')&&result.includes(':fresh-sdk-readers 2')&&result.includes(':normalizer-calls-per-selected-lookup 1')&&result.includes(':reader-solver-exchanges 0'));
   check(size.name+': supplied point needs no fallback or execution authority in '+name,result.includes(':supplied-fallback-attempts 0')&&result.includes(':checked-native-execution false')&&result.includes(':compiler-proof-authority false'));
   await shot(size.name+'-word-cell-'+name);
   await call({op:'navigate',url:base+'/#a-byte-can-carry-its-meaning-across-both-solvers'});
   await theme(value);
   await evaluate("document.getElementById('research-word-answer-evidence').scrollIntoView({block:'center',behavior:'instant'})");
   check(size.name+': actual saved evidence is current in '+name,await evaluate("document.querySelector('[data-research-element]').dataset.researchFreshness==='current'&&document.querySelectorAll('[data-research-row]').length===7&&document.querySelector('.research-status').innerText.includes('Revision 1.')"));
   check(size.name+': proof and program gaps remain visible in '+name,await evaluate("document.querySelector('[data-research-row=proof]').innerText.includes('Still open')&&document.querySelector('[data-research-row=program]').innerText.includes('Still open')"));
   check(size.name+': anonymous dossier has no save action in '+name,await evaluate("!document.querySelector('[data-research-save]')"));
   await shot(size.name+'-word-saved-evidence-'+name);
  }
  await theme('light');
  check(size.name+': no page overflow after word views',await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2'));
 }
 for (const path of ['NUMERIC-IMPLEMENTATION.md', 'SEMANTICS.md', 'FLOOR-MODULUS-MODEL.md', 'metatheory/FloorModulus.lean', 'sdk-src/decimal.bl', 'sdk-src/system/smt.bl', 'evidence/numeric-semantics/qualification.json', 'evidence/numeric-semantics/baseline/observation-summary.json', 'evidence/numeric-semantics/candidate/observation-summary.json', 'evidence/floor-modulus-model/qualification.json', 'RETAINED-REQUEST-IMPLEMENTATION.md', 'RETAINED-REQUEST-PLAN.md', 'TERM-FLOOR-MODULUS-MODEL.md', 'evidence/retained-request/qualification.json', 'evidence/retained-request/records-qualification.json', 'evidence/retained-request/previous-readers-qualification.json', 'sdk-src/formal/retained-question.bl', 'sdk-src/formal/retained-composition.bl', 'WORD-INTEGRATION.md', 'WORD-PROFILE-PLAN.md', 'WORD-ENVELOPE-MODEL.md', 'sdk-src/formal/point-profile.bl', 'sdk-src/formal/resources/word.bl', 'evidence/word-integration/qualification.json', 'evidence/word-integration/records-qualification.json', 'evidence/word-integration/previous-readers-qualification.json', 'evidence/word-envelope-model/qualification.json']) {
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
