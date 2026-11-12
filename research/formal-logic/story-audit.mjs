import {spawn} from 'node:child_process';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {resolve,join} from 'node:path';
const base=process.argv[2]||'http://127.0.0.1:24089';
const output=resolve(process.argv[3]||'research/formal-logic/evidence/story/browser-audit');
await mkdir(output,{recursive:true});
const helper=spawn('/home/othman/.nix-profile/bin/node',['research/formal-logic/browser-driver.mjs',output],{stdio:['pipe','pipe','inherit']});
let buffer=Buffer.alloc(0),waiting=[];
helper.stdout.on('data',chunk=>{buffer=Buffer.concat([buffer,chunk]);while(buffer.length>=4){const n=buffer.readUInt32BE(0);if(buffer.length<n+4)break;const v=JSON.parse(buffer.subarray(4,n+4).toString());buffer=buffer.subarray(n+4);const p=waiting.shift();clearTimeout(p.timer);v.ok?p.resolve(v.result):p.reject(Error(v.error));}});
function call(message){return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Browser helper deadline')),35000);waiting.push({resolve,reject,timer});const body=Buffer.from(JSON.stringify(message)),size=Buffer.alloc(4);size.writeUInt32BE(body.length);helper.stdin.write(Buffer.concat([size,body]));});}
const evaluate=expression=>call({op:'eval',expression});
const navigate=path=>call({op:'navigate',url:base+path});
const click=selector=>call({op:'click',selector});
const check=(name,ok,detail={})=>{report.checks.push({name,passed:Boolean(ok),...detail});if(!ok)console.log('FAILED '+name);};
const wait=expression=>call({op:'wait',expression});
const report={schema:'enchant.formal.guided-review-audit.v1',base,started:new Date().toISOString(),checks:[],screenshots:[],scope:'Live presentation, recorded data, source-backed views and kit interactions. Presentation checks do not establish source/compiler preservation.'};
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
try{
 await call({op:'open',width:1440,height:1000,mobile:false});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await navigate('/#s-the-big-idea');await wait("!!document.querySelector('#s-the-big-idea')");
  const top=await evaluate("({title:document.title,w:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth,failed:document.querySelectorAll('.cell.failed,.ms-errors,.review-errors,.cl-errors,.lt-errors').length})");
  check(size.name+': readable page width',top.sw<=top.w+2,top);check(size.name+': no failed cells or declarations',top.failed===0,top);
  const authoring=await evaluate("[...document.querySelectorAll('aside.callout.warning')].filter(e=>e.textContent.includes('Review authoring errors')).map(e=>e.textContent)");
  check(size.name+': connected review grammar is valid',authoring.length===0,{errors:authoring});
  if(authoring.length)throw Error('Connected review authoring errors: '+authoring.join(' | '));
  check(size.name+': model proofs retain their implementation boundary',await evaluate("document.body.innerText.includes('18 theorems')&&document.body.innerText.includes('not that the BL implementation or compiler faithfully implements it')"));
  check(size.name+': loop model exposes its proof-rule assumptions',await evaluate("document.body.innerText.includes('twenty-two checked theorems')&&document.body.innerText.includes('Classical.choice')"));
  await shot(size.name+'-introduction');
  await navigate('/#s-could-beam-lisp-be-fully-formal');
  check(size.name+': full formality discussion present',await evaluate("document.body.innerText.includes('Can it still feel like a Lisp?')&&document.body.innerText.includes('Self-hosting a checker in BL does not verify')&&document.body.innerText.includes('first executable fragment')"));
  await shot(size.name+'-formal-language');
  await navigate('/#s-the-model-running');
  check(size.name+': executable certificate example shows its checked result',await evaluate("/:proof\\s+:checked/.test(document.body.innerText)&&document.body.innerText.includes(':source-connection :not-established')"));
  check(size.name+': executable loop example remains a model argument',await evaluate("/:loop-model\\s+:checked/.test(document.body.innerText)&&document.body.innerText.includes(':conditional-normal-return-of-loop-model')"));
  check(size.name+': core change is gated by checked outcome evidence',await evaluate("/:core-change\\s+:optimized/.test(document.body.innerText)&&document.body.innerText.includes(':return-value-and-named-error')"));
  check(size.name+': seven subject kinds share the checked interface',await evaluate("document.body.innerText.includes(':subjects [:query :contract :loop :translation :protocol :source-protocol :protocol-trace]')&&document.body.innerText.includes(':common-term-interface true')"));
  check(size.name+': source functions keep whole-record outcomes',await evaluate("/:record-function-contract\\s+:checked/.test(document.body.innerText)&&document.body.innerText.includes(':bl/core-record-outcomes-v2')"));
  check(size.name+': source handler evidence retains the live actor boundary',await evaluate("/:source-handler-protocol\\s+:checked/.test(document.body.innerText)&&document.body.innerText.includes(':handler-core-replay :valid')&&document.body.innerText.includes(':live-actor-connection :not-established')"));
  check(size.name+': protocol proof retains its unbounded model scope',await evaluate("/:protocol-model\\s+:checked/.test(document.body.innerText)&&document.body.innerText.includes(':all-finite-prefixes-of-the-declared-state-model')"));
  check(size.name+': protocol evidence retains the actor and progress boundary',await evaluate("document.body.innerText.includes(':source-connection :authored-model-not-live-beam-actor')&&/:liveness\\s+:not-established/.test(document.body.innerText)"));
  await evaluate("[...document.querySelectorAll('pre')].find(e=>e.innerText.includes(':protocol-model :checked'))?.scrollIntoView({block:'center'})");
  await shot(size.name+'-protocol-proof');
  check(size.name+': bounded native search shows its replayed counterexample',await evaluate("/:bounded-search\\s+:refuted/.test(document.body.innerText)&&document.body.innerText.includes(':choices [1 1]')&&/:execution-replay\\s+:valid/.test(document.body.innerText)"));
  check(size.name+': bounded witness retains its bound and unchecked native certificate',await evaluate("/:bound\\s+2/.test(document.body.innerText)&&document.body.innerText.includes(':native-solver-certificate :not-checked')"));
  await evaluate("[...document.querySelectorAll('pre')].find(e=>e.innerText.includes(':bounded-search :refuted'))?.scrollIntoView({block:'center'})");
  await shot(size.name+'-bounded-counterexample');
  const sourceBounded=await evaluate("document.querySelector('#cell-story-source-bounded')?.innerText||''");
  check(size.name+': source-bounded counterexample shows matching model and handler states',/:source-bounded-search\s+:refuted/.test(sourceBounded)&&sourceBounded.includes(':model-states [{"i" 0} {"i" 1} {"i" 2}]')&&sourceBounded.includes(':handler-states [{"i" 1} {"i" 2}]'));
  check(size.name+': source-bounded counterexample retains its semantic and runtime limits',sourceBounded.includes(':bl/source-record-trace-v1')&&sourceBounded.includes(':handler-core-replay :valid')&&sourceBounded.includes(':native-solver-certificate :not-checked')&&sourceBounded.includes(':live-actor-connection :not-established'));
  await evaluate("document.querySelector('#cell-story-source-bounded').scrollIntoView({block:'center'})");
  await shot(size.name+'-source-bounded-counterexample');
  const actualRuntime=await evaluate("document.querySelector('#cell-story-actual-runtime')?.innerText||''");
  check(size.name+': actual BEAM counterexample is conforming and unsafe',actualRuntime.includes(':actual-beam :observed')&&actualRuntime.includes(':recorded-conformance :conforming')&&actualRuntime.includes(':finite-safety :violated')&&actualRuntime.includes(':observed-states [{\"i\" 0} {\"i\" 1} {\"i\" 2}]'));
  check(size.name+': actual observer records owned resource cleanup',actualRuntime.includes(':actor-alive false')&&actualRuntime.includes(':handler-artifacts-retired true'));
  check(size.name+': finite observation retains its trust boundary',actualRuntime.includes(':universal-runtime-refinement :not-established')&&actualRuntime.includes(':execution-attestation :observer-trusted-not-cryptographically-attested')&&actualRuntime.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-actual-runtime').scrollIntoView({block:'center'})");
  await shot(size.name+'-actual-beam-observation');
  await navigate('/#s-the-big-idea');
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('identity changes the mathematics')).scrollIntoView({block:'start'})");
  check(size.name+': source callee repair and remaining Var assumption are explained',await evaluate("document.body.innerText.includes('4,877 assertions')&&document.body.innerText.includes('actual compiled handler returned 3.5')&&document.body.innerText.includes('Freezing or checking that runtime binding is a separate next step')"));
  await shot(size.name+'-callee-identity');
  const bindingContext=await evaluate("document.querySelector('#cell-story-binding-context')?.innerText||''");
  const linkedState=bindingContext.match(/:linked-state\s+\{([^}]*)\}/)?.[1]||'';
  check(size.name+': explicit binding context demonstrates the ambient mismatch and linked execution',bindingContext.includes(':ordinary-when-rebound :disagreement')&&bindingContext.includes(':linked-when-rebound :observed')&&/"n"\s+2\b/.test(linkedState)&&/"flag"\s+false\b/.test(linkedState));
  check(size.name+': binding context can also back a function contract',bindingContext.includes(':binding-context :checked-context')&&bindingContext.includes(':function-contract :checked'));
  check(size.name+': local ANF closure retains the transitive and equivalence boundary',bindingContext.includes(':body-closure :no-fetched-vars-in-function-anf')&&bindingContext.includes(':transitive-runtime-closure :not-established')&&bindingContext.includes(':ambient-equivalence :requires-declared-bindings')&&bindingContext.includes(':compiler-proof-authority false'));
  await navigate('/#s-the-model-running');
  await evaluate("document.querySelector('#cell-story-binding-context').scrollIntoView({block:'center'})");
  await shot(size.name+'-binding-context');
  const selectedSource=await evaluate("document.querySelector('#cell-story-selected-source')?.innerText||''");
  check(size.name+': selected Source function and both engines share one promise',selectedSource.includes(':selected-source :checked-context')&&selectedSource.includes(':contract-statuses [:checked :checked]')&&selectedSource.includes(':bl/selected-source-context-v1')&&selectedSource.includes(':phase-check :proved'));
  check(size.name+': selected Source promise retains initialization and preservation scope',selectedSource.includes(':scope :initialize-unit-then-call')&&selectedSource.includes(':binding-closure :selected-source-and-lexical-callees')&&selectedSource.includes(':actual-selected-execution :not-observed')&&selectedSource.includes(':source-core-preservation :reviewed-not-mechanically-proved')&&selectedSource.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-selected-source').scrollIntoView({block:'center'})");
  await shot(size.name+'-selected-source');
  const selectedRuntime=await evaluate("document.querySelector('#cell-story-selected-runtime')?.innerText||''");
  check(size.name+': original selected Source executes and keeps its finite promise',selectedRuntime.includes(':actual-selected-source :observed')&&selectedRuntime.includes(':returned-value 5')&&selectedRuntime.includes(':original-unit :matched')&&selectedRuntime.includes(':receipt-check :conforming')&&selectedRuntime.includes(':contract-safety :holds'));
  check(size.name+': selected runtime keeps cleanup and proof boundaries visible',selectedRuntime.includes(':sdk-snapshot-stage :instance-prepared')&&selectedRuntime.includes(':bl/source-instance-integer-error-projection-v1')&&selectedRuntime.includes(':worker-alive false')&&selectedRuntime.includes(':remaining-preparations 0')&&selectedRuntime.includes(':universal-refinement :not-established')&&selectedRuntime.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-selected-runtime').scrollIntoView({block:'center'})");
  await shot(size.name+'-selected-runtime');
  const hygiene=await evaluate("document.querySelector('#cell-story-hygiene')?.innerText||''");
  check(size.name+': colliding role preserves seventeen and both engines refute twenty',hygiene.includes(':semantic-role "local_3"')&&hygiene.includes(':model-value 17')&&hygiene.includes(':wrong-twenty-promise [:refuted :refuted]'));
  check(size.name+': lexical repair keeps its preservation boundary explicit',hygiene.includes(':source-binding :lexical')&&hygiene.includes(':core-binding :fresh-for-input-roles')&&hygiene.includes(':source-preservation :reviewed-not-mechanically-proved')&&hygiene.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-hygiene').scrollIntoView({block:'center'})");
  await shot(size.name+'-hygiene');
  const elaboration=await evaluate("document.querySelector('#cell-story-elaboration')?.innerText||''");
  check(size.name+': independent ANF/Core gate rejects a freshly rehashed wrong model',elaboration.includes(':anf-core :checked')&&elaboration.includes(':changed-core :rejected')&&elaboration.includes(':pair-bound true'));
  check(size.name+': relation checking does not invoke a producer, solver or evaluator',elaboration.includes(':elaborator-called false')&&elaboration.includes(':solver-called false')&&elaboration.includes(':program-evaluated false'));
  check(size.name+': checked relation retains its soundness and Source boundaries',elaboration.includes(':checker-soundness :reviewed-rule-checker')&&elaboration.includes(':source-to-anf :not-established')&&elaboration.includes(':selected-specialization :not-established')&&elaboration.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-elaboration').scrollIntoView({block:'center'})");
  await shot(size.name+'-elaboration');
  const specialization=await evaluate("document.querySelector('#cell-story-specialization')?.innerText||''");
  check(size.name+': captured helper keeps its own environment in the original Source call',specialization.includes(':unit-anf :checked')&&specialization.includes(':promise :checked')&&specialization.includes(':original-source-value 42'));
  check(size.name+': earlier reduction gate rejects a wrong capture accepted by the later pair gate',specialization.includes(':changed-capture-value 102')&&specialization.includes(':changed-unit-anf :rejected')&&specialization.includes(':changed-anf-core :checked'));
  check(size.name+': reduction result keeps SDK unit and checker soundness premises explicit',specialization.includes(':unit-wellformedness :assumed-sdk-compiled-unit')&&specialization.includes(':checker-soundness :reviewed-rule-checker')&&specialization.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-specialization').scrollIntoView({block:'center'})");
  await shot(size.name+'-specialization');
  const connections=await evaluate("document.querySelector('#cell-story-connections')?.innerText||''");
  check(size.name+': equal Core models retain different authored and actual Source claims',connections.includes(':same-core true')&&connections.includes(':promises [:checked :checked]')&&connections.includes(':authored-source :authored-core-no-source-claim')&&connections.includes(':actual-source :reviewed-not-mechanically-proved'));
  check(size.name+': model interpretation keeps its reviewed implementation status',connections.includes(':interpretation :reviewed-not-mechanically-proved')&&connections.includes(':purpose :implementation-connection-not-proof'));
  check(size.name+': an interpretation record cannot substitute for a certificate',connections.includes(':connection-as-proof :rejected')&&connections.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-connections').scrollIntoView({block:'center'})");
  await shot(size.name+'-connections');
  const refutation=await evaluate("document.querySelector('#cell-story-refutation')?.innerText||''");
  check(size.name+': actual normalized packet reconstructs and altered proof is rejected',refutation.includes(':normalized-packet :ready')&&refutation.includes(':data-connection :checked-data-connection')&&refutation.includes(':rehashed-wrong-proof :rejected'));
  check(size.name+': data export keeps external proof execution separate',refutation.includes(':kernel-execution :not-run')&&refutation.includes(':normalization :reviewed-not-mechanically-proved')&&refutation.includes(':compiler-proof-authority false'));
  await navigate('/#a-proof-checker-with-a-proof');
  check(size.name+': executable kernel theorem keeps original normalization as next bridge',await evaluate("document.body.innerText.includes('every proof it accepts rules out every model of its normalized problem')&&document.body.innerText.includes('Eleven actual BL certificate exports')&&document.body.innerText.includes('Prove original-term normalization')"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('A proof checker with a proof')).scrollIntoView({block:'start'})");
  await shot(size.name+'-refutation-kernel');
  await navigate('/#s-the-model-running');
  await evaluate("document.querySelector('#cell-story-refutation').scrollIntoView({block:'center'})");
  await shot(size.name+'-refutation');
  const originalTerms=await evaluate("document.querySelector('#cell-story-term-connection')?.innerText||''");
  check(size.name+': original term trees and old normalized packet remain bound together',originalTerms.includes(':original-terms :retained')&&originalTerms.includes(':normalized-packet :unchanged')&&originalTerms.includes(':data-connection :checked-data-connection'));
  check(size.name+': changed original question is rejected after rehashing',originalTerms.includes(':rehashed-false-original :rejected')&&originalTerms.includes(':compiler-proof-authority false'));
  check(size.name+': pure original export keeps semantic profile and unexecuted proof status visible',originalTerms.includes(':term-semantics :bl/partial-mathematical-int-bool-v1')&&originalTerms.includes(':term-connection :not-run')&&originalTerms.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-term-connection').scrollIntoView({block:'center'})");
  await shot(size.name+'-original-terms');
  await navigate('/#carry-the-proof-back-to-the-question');
  check(size.name+': original proof chapter explains universal per-question countermodel preservation',await evaluate("document.body.innerText.includes('any counterexample to the original question would also satisfy the normalized problem')&&document.body.innerText.includes('Seventeen real exports')&&document.body.innerText.includes('every integer and Boolean input of that particular typed question')"));
  check(size.name+': original proof chapter keeps undefined results and the implementation bridge explicit',await evaluate("document.body.innerText.includes('returning no value cannot pass')&&document.body.innerText.includes('The reviewed interpretation of BL term data as this typed model')"));
  await click('[data-graph="formal-term-connection"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="connection"]');
  check(size.name+': opened connection panel keeps general normalizer correctness separate',await evaluate("document.querySelector('[data-graph=\"formal-term-connection\"] .sg-stage>[data-view]:not([hidden])').innerText.includes('no blanket BL normalizer theorem')"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Carry the proof back to the question')).scrollIntoView({block:'start'})");
  await shot(size.name+'-term-connection');
  await navigate('/#s-the-model-running');
  const obligations=await evaluate("document.querySelector('#cell-story-obligations')?.innerText||''");
  check(size.name+': common loop proof data retains all eight required premises',obligations.includes(':required 8')&&obligations.includes(':ready 8')&&obligations.includes(':data-connection :checked-data-connection')&&obligations.includes(':missing-premise :rejected'));
  check(size.name+': proof foundations can change without changing the model plan',obligations.includes(':default-policy :lean-standard-v1')&&obligations.includes(':stricter-policy :choice-free-v1')&&obligations.includes(':same-model-plan true'));
  check(size.name+': common proof data keeps external execution and model composition separate',obligations.includes(':kernel-execution :not-run')&&obligations.includes(':feasibility :not-established')&&obligations.includes(':composition :reviewed-not-mechanically-proved')&&obligations.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-obligations').scrollIntoView({block:'center'})");
  await shot(size.name+'-obligation-data');
  await navigate('/#one-proof-plan-for-a-whole-promise');
  check(size.name+': shared plan chapter distinguishes proof coverage from a SAT witness',await evaluate("document.body.innerText.includes('eight separate reasons')&&document.body.innerText.includes('A conditional model promise can have complete required proofs while its initial-state witness remains unavailable')"));
  await click('[data-graph="formal-obligation-plan"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="foundations"]');
  check(size.name+': opened foundation panel shows actual classical dependencies and alternative proof boundary',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-obligation-plan\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('Two actual obligation proofs use Classical.choice')&&t.includes('does not show that no choice-free proof exists')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('One proof plan for a whole promise')).scrollIntoView({block:'start'})");
  await shot(size.name+'-obligation-plan');
  await navigate('/#show-that-a-state-can-exist');
  check(size.name+': positive evidence chapter distinguishes existence from conditional promises',await evaluate("document.body.innerText.includes('Choosing 6 for x and 7 for y makes it true')&&document.body.innerText.includes('actual values that satisfy them')&&document.body.innerText.includes('Thirty-two original packets pass')&&document.body.innerText.includes('twenty-two authored assignments and ten native models')"));
  await click('[data-graph="formal-positive-witness"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="existence"]');
  check(size.name+': constructive witness panel retains actual foundations',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-positive-witness\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('Classical.choice is not admitted')&&t.includes('total integer and Boolean environments')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Show that a state can exist')).scrollIntoView({block:'start'})");
  await shot(size.name+'-positive-witness');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-positive-witness\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-positive-panel');
  }
  await navigate('/#s-the-model-running');
  const positive=await evaluate("document.querySelector('#cell-story-positive-witness')?.innerText||''");
  check(size.name+': executable positive witness keeps original replay and wrong-value rejection',positive.includes(':evidence :positive-sat-witness')&&positive.includes(':data-connection :checked-data-connection')&&positive.includes(':wrong-value :rejected'));
  check(size.name+': positive replay keeps observers and external proof execution separate',positive.includes(':watchers :no-added-assumptions')&&positive.includes(':existence :checked-by-bl-replay')&&positive.includes(':kernel-execution :not-run')&&positive.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-positive-witness').scrollIntoView({block:'center'})");
  await shot(size.name+'-positive-data');
  await navigate('/#s-the-model-running');
  await navigate('/#give-the-proof-a-real-starting-point');
  check(size.name+': mixed evidence chapter names an actual countdown input',await evaluate("document.body.innerText.includes('The binding n = 3 supplies one such input')&&document.body.innerText.includes('A witness and an open proof obligation')"));
  await click('[data-graph="formal-witnessed-obligations"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="apply"]');
  check(size.name+': mixed proof panel shows the applied theorem scope',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-witnessed-obligations\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('applies the imported universal entailment')&&text.includes('this original typed term question')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Give the proof a real starting point')).scrollIntoView({block:'start'})");
  await shot(size.name+'-witnessed-obligations');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-witnessed-obligations\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-witnessed-panel');
  }
  await navigate('/#s-the-model-running');
  const mixed=await evaluate("document.querySelector('#cell-story-witnessed-obligations')?.innerText||''");
  check(size.name+': mixed countdown cell has all required claims and one initial witness',mixed.includes(':initial-value 3')&&mixed.includes(':initial-evidence :witness-ready')&&mixed.includes(':required-claims 8')&&mixed.includes(':ready-claims 8'));
  check(size.name+': only the matching countdown entailment uses the witness',mixed.includes(':matching-entailments ["obligation/initial/normal"]')&&mixed.includes(':data-connection :checked-data-connection')&&mixed.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-witnessed-obligations').scrollIntoView({block:'center'})");
  await shot(size.name+'-witnessed-data');
  await navigate('/#check-what-the-core-terms-mean');
  check(size.name+': Core chapter explains eager defaults and whole outcomes',await evaluate("document.body.innerText.includes('Core still evaluates the default as a call argument')&&document.body.innerText.includes('agree for every typed input to that tree')"));
  await click('[data-graph="formal-core-term-correspondence"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="theorem"]');
  check(size.name+': Core proof panel identifies the exact term theorem and reviewed codec',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-core-term-correspondence\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('exact emitted success, payload and error terms')&&text.includes('named-data codec')&&text.includes('contained typed tree and symbolic outcome')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Check what the Core terms mean')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-term-agreement');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-core-term-correspondence\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-term-panel');
  }
  await navigate('/#s-the-model-running');
  const eager=await evaluate("document.querySelector('#cell-story-core-term-agreement')?.innerText||''");
  check(size.name+': eager default cell shows a present field and the named error',eager.includes(':present-field "balance"')&&eager.includes(':core-outcome :raised')&&eager.includes(':named-error :phase/default')&&eager.includes(':symbolic-success false'));
  check(size.name+': pure Core packet replay records its external execution boundary',eager.includes(':data-connection :checked-data-connection')&&eager.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-term-agreement').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-term-data');
  await navigate('/#prove-the-promise-on-the-core-program');
  check(size.name+': contract chapter explains the return promise and one admitted input',await evaluate("document.body.innerText.includes('The checked policy rules out a raised outcome')&&document.body.innerText.includes('x set to 4')"));
  await click('[data-graph="formal-core-contract-composition"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="layout"]');
  check(size.name+': contract proof panel shows exact name and sort transport',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-core-contract-composition\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('Both proof slots move from index zero to index one')&&text.includes('match the exact assumptions and the whole outcome policy')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Prove the promise on the Core program')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-contract');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-core-contract-composition\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-contract-panel');
  }
  await navigate('/#s-the-model-running');
  const composed=await evaluate("document.querySelector('#cell-story-core-contract-composition')?.innerText||''");
  check(size.name+': contract cell records its input and exact policy replay',composed.includes(':admitted-x 4')&&composed.includes(':core-value 5')&&composed.includes(':declared-inputs 4')&&composed.includes(':witness-inputs 2')&&composed.includes(':must-return true')&&composed.includes(':changed-policy :rejected')&&composed.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-contract-composition').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-contract-data');
  await navigate('/#prove-that-a-rewrite-preserves-the-outcome');
  check(size.name+': rewrite chapter explains both observed outcomes and its precondition',await evaluate("document.body.innerText.includes('when a flag is true and raises a named error otherwise')&&document.body.innerText.includes(\"whenever the rewrite's precondition holds\")"));
  await click('[data-graph="formal-core-translation-composition"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="premises"]');
  check(size.name+': rewrite proof panel describes the exact question and all three imports',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-core-translation-composition\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('imports all three freshly compiled proofs')&&text.includes('after aligning typed input slots')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Prove that a rewrite preserves the outcome')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-translation');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-core-translation-composition\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-translation-panel');
  }
  await navigate('/#s-the-model-running');
  const rewrite=await evaluate("document.querySelector('#cell-story-core-translation-composition')?.innerText||''");
  check(size.name+': executable rewrite shows both values and both error names',rewrite.includes(':returned-values [0 0]')&&rewrite.includes(':raised-errors [:phase/left :phase/left]')&&rewrite.includes(':data-connection :checked-data-connection')&&rewrite.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-translation-composition').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-translation-data');
  await navigate('/#prove-that-the-loop-reaches-its-exit');
  check(size.name+': ranked loop chapter describes a finite trace with no fixed bound',await evaluate("document.body.innerText.includes('A finite return trace exists for every admitted input')&&document.body.innerText.includes('The theorem uses no fixed iteration bound')"));
  await click('[data-graph="formal-core-loop-composition"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="step"]');
  check(size.name+': loop proof panel explains the exact recurrence values',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-core-loop-composition\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('substitution into the invariant and rank uses the actual next values')&&text.includes('State slots are updated together')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Prove that the loop reaches its exit')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-loop');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-core-loop-composition\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-loop-panel');
  }
  await navigate('/#s-the-model-running');
  const ranked=await evaluate("document.querySelector('#cell-story-core-loop-composition')?.innerText||''");
  check(size.name+': executable countdown displays four actual backedges and a replayed packet',ranked.includes(':sample-input 4')&&ranked.includes(':sample-result 4')&&ranked.includes(':sample-backedges 4')&&ranked.includes(':data-connection :checked-data-connection')&&ranked.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-loop-composition').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-loop-data');
  await navigate('/#keep-the-actor-invariant-across-every-admitted-event');
  check(size.name+': actor chapter names message admission and its unbounded trace scope',await evaluate("document.body.innerText.includes('A negative amount falls outside the declared message assumptions')&&document.body.innerText.includes('uses no fixed trace length')"));
  await click('[data-graph="formal-core-actor-composition"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="outcome"]');
  check(size.name+': actor proof panel applies the invariant to actual returned fields',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-core-actor-composition\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('actual returned fields')&&text.includes('the invariant reads only state slots')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Keep the actor invariant across every admitted event')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-actor');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-core-actor-composition\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-actor-panel');
  }
  await navigate('/#s-the-model-running');
  const bank=await evaluate("document.querySelector('#cell-story-core-actor-composition')?.innerText||''");
  check(size.name+': bank cell replays four events and checks both handler packets',bank.includes(':sample-balance 7')&&bank.includes(':sample-safety :holds')&&bank.includes(':handler-count 2')&&bank.includes(':events 4')&&bank.includes(':data-connection :checked-data-connection')&&bank.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-actor-composition').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-actor-data');
  await navigate('/#follow-one-recorded-actor-run-into-core');
  check(size.name+': recorded trace explains both the repaired state and the observer boundary',await evaluate("document.body.innerText.includes('The first bad prefix violates the invariant')&&document.body.innerText.includes('the observer is trusted to report the execution faithfully')"));
  await click('[data-graph="formal-recorded-core-trace"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="apply"]');
  check(size.name+': recorded trace panel applies the exact matching theorem to every prefix',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-recorded-core-trace\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('same exact bank model')&&text.includes('applies it to every recorded prefix')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Follow one recorded actor run into Core')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-observation');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-recorded-core-trace\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-observation-panel');
  }
  await navigate('/#s-the-model-running');
  const recording=await evaluate("document.querySelector('#cell-story-core-observation')?.innerText||''");
  check(size.name+': bank observation cell checks the five recorded states',recording.includes(':balances [0 10 7 7 7]')&&recording.includes(':recorded-prefixes 5')&&recording.includes(':adapter-conformance :conforming')&&recording.includes(':data-connection :checked-data-connection')&&recording.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-observation').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-observation-data');
  await navigate('/#follow-a-counterexample-from-either-solver');
  check(size.name+': native counterexample chapter keeps the original claim and completion origin',await evaluate("document.body.innerText.includes('those values make the original claim false')&&document.body.innerText.includes('retains its origin')"));
  await click('[data-graph="formal-core-counterexample"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="values"]');
  check(size.name+': counterexample panel ties states choices and messages to query bindings',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-core-counterexample\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('State fields, selected choices and messages')&&text.includes('query bindings to the recorded Core trace')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Follow a counterexample from either solver')).scrollIntoView({block:'start'})");
  await shot(size.name+'-core-counterexample');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-core-counterexample\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-core-counterexample-panel');
  }
  await navigate('/#s-the-model-running');
  const counterexample=await evaluate("document.querySelector('#cell-story-core-counterexample')?.innerText||''");
  check(size.name+': paired counterexample cell records the same original query and checked data',counterexample.includes(':engines [:z3 :oxiz]')&&counterexample.includes(':same-query true')&&counterexample.includes(':unsafe-recordings 2')&&counterexample.includes(':data-connections [:checked-data-connection :checked-data-connection]')&&counterexample.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-counterexample').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-counterexample-data');
  await navigate('/#ask-through-the-language-library');
  check(size.name+': SDK chapter exposes public consumers and remaining migration',await evaluate("document.body.innerText.includes('The formal interface now reaches the SDK')&&document.body.innerText.includes('remaining legacy consumers and default text oracle still need migration')"));
  await click('[data-graph="formal-sdk-interface"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="effect"]');
  check(size.name+': SDK effect panel keeps complete questions snapshots and native borrowing visible',await evaluate("(()=>{const text=document.querySelector('[data-graph=\"formal-sdk-interface\"] .sg-stage>[data-view]:not([hidden])').innerText;return text.includes('complete question')&&text.includes(\"calling process's handler snapshot\")&&text.includes('callback custody')&&text.includes('native solver session remains borrower-owned')})()"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Ask through the language library')).scrollIntoView({block:'start'})");
  await shot(size.name+'-sdk-interface');
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-sdk-interface\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-sdk-interface-panel');
  }
  await navigate('/#s-the-model-running');
  await wait("document.querySelector('#cell-story-sdk-interface').getClientRects().length>0");
  check(size.name+': SDK example is visible in its executable section',await evaluate("document.querySelector('#cell-story-sdk-interface').getClientRects().length>0"));
  const sdkInterface=await evaluate("document.querySelector('#cell-story-sdk-interface')?.innerText||''");
  check(size.name+': SDK cell checks portable model and both native engines',sdkInterface.includes(':sdk-entry-point :system/preserves?')&&sdkInterface.includes(':portable-model :checked')&&sdkInterface.includes(':native-verdicts [:proved :proved]'));
  check(size.name+': SDK table sees the same question without opening a native worker',sdkInterface.includes(':same-question true')&&sdkInterface.includes(':table-answer :unknown')&&sdkInterface.includes(':handler-native-worker :not-opened'));
  check(size.name+': SDK handler keeps scope certificate and authority explicit',sdkInterface.includes(':handler-scope :calling-process')&&sdkInterface.includes(':handler-certificate :not-checked')&&sdkInterface.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-sdk-interface .result').scrollIntoView({block:'center'})");
  await shot(size.name+'-sdk-interface-data');
  if(size.name==='desktop'){
    await navigate('/#ask-through-the-language-library');
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-sdk-interface\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-sdk-interface-night');
    await click('#theme');
  }
  await navigate('/#an-answer-has-to-fit-its-question');
  await wait("document.querySelector('#an-answer-has-to-fit-its-question').getClientRects().length>0");
  check(size.name+': answer chapter explains typed bindings and reconstruction',await evaluate("document.body.innerText.includes('accept a contradiction')&&document.body.innerText.includes('standard observation is 8')"));
  await click('[data-graph="formal-answer-integrity"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="bindings"]');
  check(size.name+': typed binding panel refuses language truthiness',await evaluate("document.querySelector('[data-graph=\"formal-answer-integrity\"] .sg-stage>[data-view]:not([hidden])').innerText.includes('Malformed bindings cannot become a satisfying assignment through BL truthiness')"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('An answer has to fit its question')).scrollIntoView({block:'start'})");
  await shot(size.name+'-answer-integrity');
  await click('[data-graph="formal-answer-integrity"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="context"]');
  check(size.name+': context panel exposes tracked state and raw transport boundary',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-answer-integrity\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('cooperative API handles')&&t.includes('Raw native transport')})()"));
  await evaluate("document.querySelector('[data-graph=\"formal-answer-integrity\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
  await shot(size.name+'-answer-context-panel');
  await click('[data-graph="formal-answer-integrity"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="native"]');
  check(size.name+': native reply panel keeps execution and proof separate',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-answer-integrity\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('actual fallback result')&&t.includes('unchecked certificate status')&&t.includes('Compiler proof authority stays disabled')})()"));
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-answer-integrity\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-answer-integrity-night');
    await click('#theme');
  }
  await navigate('/#equality-follows-the-value-s-sort');
  await wait("document.querySelector('#equality-follows-the-value-s-sort').getClientRects().length>0");
  check(size.name+': equality chapter distinguishes formal data SMT identity and IEEE comparison',await evaluate("document.body.innerText.includes('one logical NaN value')&&document.body.innerText.includes('fp.eq has its own comparison rule')&&document.body.innerText.includes('reports the sequence question unsupported')"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes(\"Equality follows the value's sort\")).scrollIntoView({block:'start'})");
  await shot(size.name+'-nested-equality');
  await navigate('/#s-the-model-running');
  for(const id of ['story-answer-integrity','story-answer-context','story-nested-equality']){
    await wait(`document.querySelector('#cell-${id}').getClientRects().length>0`);
    check(size.name+': visible executable result '+id,await evaluate(`document.querySelector('#cell-${id} .result').getClientRects().length>0`));
    const text=await evaluate(`document.querySelector('#cell-${id} .result').innerText`);
    if(id==='story-answer-integrity')check(size.name+': handled answer cell checks sorts observations and phases',text.includes(':ill-sorted-contradiction :invalid-model')&&text.includes(':derived-next 8')&&text.includes(':reported-next 999')&&text.includes(':wrong-phase :error')&&text.includes(':observation-source :independent-replay')&&text.includes(':compiler-proof-authority false'));
    if(id==='story-answer-context')check(size.name+': both engines refuse changed tracked context',text.includes(':engines [:z3 :oxiz]')&&text.includes(':original-verdicts [:refuted :refuted]')&&text.includes(':after-context-change [:error :error]')&&text.includes(':fallback-statuses [:not-run :not-run]'));
    if(id==='story-nested-equality')check(size.name+': equality cell keeps exact native availability and unchecked certificate',text.includes(':independent-values [true true true]')&&text.includes(':z3 [:proved :proved :proved]')&&text.includes(':oxiz [:unsupported :proved :proved]')&&text.includes(':native-certificate :not-checked')&&text.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#the-process-keeps-the-real-context');
  await wait("document.querySelector('#the-process-keeps-the-real-context').getClientRects().length>0");
  check(size.name+': native owner chapter explains authoritative state and restored mirrors',await evaluate("document.body.innerText.includes('diagnostic mirror')&&document.body.innerText.includes('owner now sees a different revision')"));
  await click('[data-graph="formal-native-context-owner"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="question"]');
  check(size.name+': owner question panel separates durable terms and execution token',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-native-context-owner\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('no owner PID, port or native node IDs')&&t.includes('outside the durable question')})()"));
  await click('[data-graph="formal-native-context-owner"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="raw"]');
  check(size.name+': raw transport panel keeps reset policy and introspection scope explicit',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-native-context-owner\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('refuses further managed solving until a reset')&&t.includes('Arbitrary Erlang introspection')})()"));
  await evaluate("document.querySelector('#the-process-keeps-the-real-context').scrollIntoView({block:'start'})");
  await shot(size.name+'-native-context-owner');
  check(size.name+': owner topic navigation remains visible',await evaluate("(()=>{const n=document.querySelector('[data-graph=\"formal-native-context-owner\"] .sg-stage>[data-view]:not([hidden]) .review-index'),r=n.getBoundingClientRect();return [...n.querySelectorAll('button')].some(b=>{const q=b.getBoundingClientRect();return b.innerText.trim()&&q.width>0&&q.height>0&&q.right>r.left&&q.left<r.right&&q.bottom>r.top&&q.top<r.bottom})})()"));
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-native-context-owner\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-native-context-owner-panel');
  }
  await click('[data-graph="formal-native-context-owner"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="retirement"]');
  check(size.name+': retirement panel keeps completed native refusal distinct from future execution',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-native-context-owner\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('without changing the question it answered')&&t.includes('does not authorize another exchange')&&t.includes('Compiler proof authority stays disabled')})()"));
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-native-context-owner\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-native-context-owner-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-native-contexts','story-native-context-revision']){
    await wait(`document.querySelector('#cell-${id} .result').getClientRects().length>0`);
    check(size.name+': visible executable result '+id,await evaluate(`document.querySelector('#cell-${id} .result').getClientRects().length>0`));
    const t=await evaluate(`document.querySelector('#cell-${id} .result').innerText`);
    if(id==='story-native-contexts')check(size.name+': owner cell retains assumptions refuses raw reuse and catches a restored mirror',t.includes(':engines [:z3 :oxiz]')&&t.includes(':after-raw-load [:not-run :not-run]')&&t.includes(':after-managed-reset [:refuted :refuted]')&&t.includes(':retained-assumptions [1 1]')&&t.includes(':restored-mirror-revisions [0 0]')&&t.includes(':actual-owner-revisions [1 1]')&&t.includes(':questions-portable true')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-native-context-revision')check(size.name+': owner revision cell shows no native checks for refused scopes',t.includes(':before-revisions [0 0]')&&t.includes(':after-revisions [1 1]')&&t.includes(':stale-scopes [:context-changed :context-changed]')&&t.includes(':refused-native-checks [0 0]')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#keep-the-handler-with-the-work');
  await wait("document.querySelector('#keep-the-handler-with-the-work').getClientRects().length>0");
  check(size.name+': handler chapter binds submission snapshots to actual code custody',await evaluate("document.body.innerText.includes('keep that snapshot after the caller leaves its scope')&&document.body.innerText.includes(\"retains the handler's executable code\")"));
  await evaluate("document.querySelector('#keep-the-handler-with-the-work').scrollIntoView({block:'start'})");
  await shot(size.name+'-effect-scopes');
  await click('[data-graph="formal-effect-scopes"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="retain"]');
  check(size.name+': handler retention keeps outside dependencies and Source authority distinct',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-effect-scopes\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('before publishing managed work')&&t.includes('explicit outside-dependency contract')&&t.includes('grants no Source execution authority')})()"));
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-effect-scopes\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-effect-custody-panel');
  }
  await click('[data-graph="formal-effect-scopes"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="world"]');
  check(size.name+': explicit world entry has a declared handler boundary',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-effect-scopes\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes(\"clears the builder's callable tables\")&&t.includes(\"uses that world's context\")&&t.includes('Ordinary calls preserve the active dynamic table')})()"));
  await click('[data-graph="formal-effect-scopes"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="limits"]');
  check(size.name+': scoped handler support keeps continuation and proof limits explicit',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-effect-scopes\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('synchronous scoped function calls')&&t.includes('Continuation capture')&&t.includes('Compiler proof authority stays disabled')})()"));
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-effect-scopes\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-effect-scopes-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-managed-effects','story-named-effects']){
    await wait(`document.querySelector('#cell-${id} .result').getClientRects().length>0`);
    check(size.name+': visible executable result '+id,await evaluate(`document.querySelector('#cell-${id} .result').getClientRects().length>0`));
    const t=await evaluate(`document.querySelector('#cell-${id} .result').innerText`);
    if(id==='story-managed-effects')check(size.name+': each backend choice handles four managed boundaries with native paths unavailable',t.includes(':backend-choices [:z3 :oxiz]')&&t.includes(':managed-boundaries [:child :future :registration :actor]')&&t.includes(':observed-x [[7 7 7 7] [7 7 7 7]]')&&t.includes(':native-paths [:unavailable :unavailable]')&&t.includes(':typed-replay :valid')&&t.includes(':caller-restored true')&&t.includes(':certificate :not-checked')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-named-effects')check(size.name+': named effect registration keeps forty-two while caller restores its default',t.includes(':submitted-work 42')&&t.includes(':caller-default 40')&&t.includes(':caller-restored true')&&t.includes(':continuation-capture false')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#the-sdk-brings-its-own-worker');
  await wait("document.querySelector('#the-sdk-brings-its-own-worker').getClientRects().length>0");
  check(size.name+': packaged worker chapter makes ordinary calls independent of research setup',await evaluate("document.body.innerText.includes('no research import path or manual worker build')&&document.body.innerText.includes('does not change the question or hide a theory gap')"));
  await evaluate("document.querySelector('#the-sdk-brings-its-own-worker').scrollIntoView({block:'start'})");
  await shot(size.name+'-packaged-worker');
  await click('[data-graph="formal-packaged-worker"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="image"]');
  check(size.name+': artifact panel keeps actual selection and mixed provenance visible',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-packaged-worker\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('Options override environment pins')&&t.includes('mixed selection')&&t.includes('do not grant compiler proof authority')})()"));
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-packaged-worker\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-packaged-artifacts-panel');
  }
  await click('[data-graph="formal-packaged-worker"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="build"]');
  check(size.name+': build panel distinguishes construction resources from runtime budgets',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-packaged-worker\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('104 registry pins')&&t.includes('Real KVM access')&&t.includes('construction guest')&&t.includes('caller resource limits')})()"));
  await click('[data-graph="formal-packaged-worker"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="portable"]');
  check(size.name+': portable panel keeps changed hashes and activation scope separate',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-packaged-worker\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('producer hashes')&&t.includes('changed runtime hashes')&&t.includes('observed host execution')&&t.includes('Clean-host activation')})()"));
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-packaged-worker\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-packaged-worker-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-packaged-worker','story-portable-provenance']){
    await wait(`document.querySelector('#cell-${id} .result').getClientRects().length>0`);
    check(size.name+': visible executable result '+id,await evaluate(`document.querySelector('#cell-${id} .result').getClientRects().length>0`));
    const t=await evaluate(`document.querySelector('#cell-${id} .result').innerText`);
    if(id==='story-packaged-worker')check(size.name+': SDK cell selects packaged files and validates both ordinary queries',t.includes(':backend-choices [:z3 :oxiz]')&&t.includes(':worker-origins [:sdk :sdk]')&&t.includes(':library-origins [:sdk nil]')&&t.includes(':packaged-components [[:worker :library] [:worker]]')&&t.includes(':observed-x [7 7]')&&t.includes(':typed-replay [:valid :valid]')&&t.includes(':certificate [:not-checked :not-checked]')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-portable-provenance')check(size.name+': portable cell labels recorded host evidence and distinct runtime hashes',t.includes(':evidence :recorded-host-execution')&&t.includes(':packaging "portable-shell-v1"')&&t.includes(':producer-and-runtime-hashes :distinct')&&t.includes(':producer-hashes :retained')&&t.includes(':observed-x [7 7]')&&t.includes(':clean-host-activation :not-qualified')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#a-question-can-end-cleanly');
  await wait("document.querySelector('#a-question-can-end-cleanly').getClientRects().length>0");
  check(size.name+': lifetime chapter explains the two concrete old behaviors',await evaluate("document.body.innerText.includes('stalled owner could survive cleanup')&&document.body.innerText.includes('valid term followed by ignored bytes')"));
  await evaluate("document.querySelector('#a-question-can-end-cleanly').scrollIntoView({block:'start'})");
  await shot(size.name+'-session-lifetime');
  await click('[data-graph="formal-session-lifetime"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="callback"]');
  check(size.name+': cleanup panel names its bounded stop and exact PID',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-session-lifetime\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('one-second graceful-stop deadline')&&t.includes('exact PID')&&t.includes('independently of its solving thread')})()"));
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-session-lifetime\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-session-lifetime-panel');
  }
  await click('[data-graph="formal-session-lifetime"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="fixture"]');
  check(size.name+': cancellation panel keeps the faulty peer separate from a real solver search',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-session-lifetime\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('not a solver')&&t.includes('does not qualify cancellation during a genuine hard solver search')})()"));
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-session-lifetime\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-session-lifetime-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  const ended=await evaluate("document.querySelector('#cell-story-session-lifetime .result').innerText");
  check(size.name+': visible executable result story-session-lifetime',await evaluate("document.querySelector('#cell-story-session-lifetime .result').getClientRects().length>0"));
  check(size.name+': both real native callback errors survive with owner and worker gone',ended.includes(':backends [:z3 :oxiz]')&&ended.includes(':callback-errors [:preserved :preserved]')&&ended.includes(':owner-alive [false false]')&&ended.includes(':worker-alive [false false]')&&ended.includes(':retired [true true]'));
  check(size.name+': execution cell keeps hard-search and proof authority boundaries',ended.includes(':busy-solver-cancellation :not-qualified')&&ended.includes(':compiler-proof-authority false'));
  await evaluate("document.querySelector('#cell-story-session-lifetime .result').scrollIntoView({block:'center'})");
  await shot(size.name+'-story-session-lifetime-data');
  await navigate('/#time-becomes-a-value-you-can-reason-about');
  await wait("document.querySelector('#time-becomes-a-value-you-can-reason-about').getClientRects().length>0");
  check(size.name+': temporal chapter distinguishes mixed datings from solver uncertainty',await evaluate("document.body.innerText.includes('starts somewhere between zero and four')&&document.body.innerText.includes('An engine that cannot decide has a different answer')"));
  await evaluate("document.querySelector('#time-becomes-a-value-you-can-reason-about').scrollIntoView({block:'start'})");
  await shot(size.name+'-temporal-values');
  await click('[data-graph="formal-temporal-values"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="meaning"]');
  check(size.name+': temporal panel separates endpoint data, empty point sets and positive-width Allen relations',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-temporal-values\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('different endpoint data')&&t.includes('positive-width premise')&&t.includes('Input range constraints and model admission remain separate')})()"));
  if(size.name==='phone'){
    await evaluate("document.querySelector('[data-graph=\"formal-temporal-values\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-temporal-meaning-panel');
  }
  await click('[data-graph="formal-temporal-values"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="chronology"]');
  check(size.name+': chronology panel preserves event identities and a strict predicate',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-temporal-values\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('Namespaced keywords and symbols')&&t.includes('raises with the complete answer when unresolved')})()"));
  await click('[data-graph="formal-temporal-values"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="laws"]');
  check(size.name+': temporal law panel keeps exact term theorems separate from runtime correspondence',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-temporal-values\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('Three portable certificates')&&t.includes('exact generated integer-term statements')&&t.includes('runtime remains reviewed')})()"));
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-temporal-values\"]').scrollIntoView({block:'center'})");
    await shot(size.name+'-temporal-values-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-temporal-values','story-temporal-chronology','story-temporal-laws']){
    await wait(`document.querySelector('#cell-${id} .result').getClientRects().length>0`);
    check(size.name+': visible executable result '+id,await evaluate(`document.querySelector('#cell-${id} .result').getClientRects().length>0`));
    const t=await evaluate(`document.querySelector('#cell-${id} .result').innerText`);
    if(id==='story-temporal-values')check(size.name+': both native possibilities retain valid replay and identical complete questions',t.includes(':overlap [:possible :possible]')&&t.includes(':intersecting-starts [2 2]')&&t.includes(':intersecting-replay [:valid :valid]')&&t.includes(':separated-replay [:valid :valid]')&&t.includes(':same-complete-questions true')&&t.includes(':native-certificate :not-checked')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-temporal-chronology')check(size.name+': full event identities and an unresolved strict predicate remain visible',t.includes(':native-consistency [true true]')&&t.includes(':left/event')&&t.includes(':right/event')&&t.includes(':starts [2 2]')&&t.includes(':predicate-refused true')&&t.includes(':verdict :unknown')&&t.includes(':consistent nil')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-temporal-laws')check(size.name+': three original term laws reconnect to recorded external proofs',t.includes(':certificates [:checked :checked :checked]')&&t.includes('intersection-symmetry')&&t.includes('shift-preserves-duration')&&t.includes('empty-spans-same-points')&&t.includes(':external-proof :recorded-Lean-results')&&t.includes(':model-runtime-connection :reviewed-implementation')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#a-function-can-explain-its-failing-example');
  check(size.name+': source property chapter explains exact ANF replay',await evaluate("document.body.innerText.includes('runs that exact representation')&&document.body.innerText.includes('an unused output cannot hide a crash')"));
  await evaluate("document.querySelector('#a-function-can-explain-its-failing-example').scrollIntoView({block:'start'})");
  await shot(size.name+'-source-properties');
  check(size.name+': source answer table labels UNSAT with its own conclusion',await evaluate("(()=>{const r=[...document.querySelectorAll('.rosetta .r-row:not(.r-head)')].find(r=>r.children[0]?.textContent.trim()==='Native UNSAT');return !!r&&r.children[1].textContent.trim()==='solver-claim'&&r.children[1].dataset.h==='Answer'&&r.children[2].textContent.includes('certificate is still unchecked')})()"));
  await click('[data-graph="formal-source-properties"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="replay"]');
  check(size.name+': source panel distinguishes execution agreement and a candidate',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-source-properties\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('same compiler ANF')&&t.includes('remain a candidate')})()"));
  await evaluate("document.querySelector('[data-graph=\"formal-source-properties\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
  await shot(size.name+'-source-replay-panel');
  if(size.name==='desktop'){
    await click('#theme');
    await click('[data-graph="formal-source-properties"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="proof"]');
    await evaluate("document.querySelector('[data-graph=\"formal-source-properties\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-source-proof-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-source-properties','story-source-property-outcomes','story-source-property-proof']){
    const t=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
    check(size.name+': visible executed source result '+id,t.length>100);
    if(id==='story-source-properties')check(size.name+': paired claims retain unchecked certificates and both replays',t.includes(':law [:solver-claim :solver-claim]')&&t.includes(':native-certificate [:not-checked :not-checked]')&&t.includes(':failing-inputs [-2 -2]')&&t.includes(':actual-results [0 0]')&&t.includes(':runtime-replay [:reproduced :reproduced]')&&t.includes(':term-replay [:valid :valid]')&&t.includes(':same-complete-question true'));
    if(id==='story-source-property-outcomes')check(size.name+': source failures and inconclusive answers have distinct meanings',t.includes(':target-crash [:raised :raised]')&&t.includes(':empty-domain [:vacuous :vacuous]')&&t.includes(':unsupported :unsupported')&&t.includes(':explicit-sample :witnessed')&&t.includes(':unknown :unknown')&&t.includes(':unknown-engine :terms'));
    if(id==='story-source-property-proof')check(size.name+': checked term proof retains reviewed runtime correspondence',t.includes(':term-certificate :checked')&&t.includes(':term-claim :entails')&&t.includes(':source-connection :reviewed')&&t.includes(':runtime-correspondence :reviewed-implementation')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#generators-can-speak-the-same-logic');
  check(size.name+': generator chapter distinguishes encodings and runtime units',await evaluate("document.body.innerText.includes('Finite tags encode the alternatives')&&document.body.innerText.includes('BL count uses graphemes')&&document.body.innerText.includes('Bodies are removed before compilation')"));
  await evaluate("document.querySelector('#generators-can-speak-the-same-logic').scrollIntoView({block:'start'})");
  await shot(size.name+'-generator-terms');
  await click('[data-graph="formal-veritas-terms"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="ledger"]');
  check(size.name+': ledger panel records evidence without proof promotion',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-veritas-terms\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('False and nil survive durable storage')&&t.includes('recorded assurance')&&t.includes('does not check a proof')})()"));
  await evaluate("document.querySelector('[data-graph=\"formal-veritas-terms\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
  await shot(size.name+'-recorded-evidence-panel');
  if(size.name==='desktop'){
    await click('#theme');
    await shot(size.name+'-recorded-evidence-night');
    await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-generator-terms','story-clause-coverage','story-runtime-units','story-recorded-verdicts']){
    const t=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
    check(size.name+': visible executed generator result '+id,t.length>100);
    if(id==='story-generator-terms')check(size.name+': composed domains retain abstract scope and false payload replay',t.includes(':composed-claims [:solver-claim :solver-claim]')&&t.includes(':same-complete-question true')&&t.includes(':scope :abstract')&&t.includes(':left/open false')&&t.includes(':runtime-replay [:reproduced :reproduced]')&&t.includes(':enum-model :finite-tag-encoding'));
    if(id==='story-clause-coverage')check(size.name+': coverage retains local names and reproduces zero gap',t.includes(':coverage [:solver-claim :solver-claim]')&&t.includes(':gap [:refuted :refuted]')&&t.includes(':uncovered-inputs [0 0]')&&t.includes(':original-bodies :removed-before-compilation'));
    if(id==='story-runtime-units')check(size.name+': exact shared Unicode law keeps different native verdicts',t.includes(':unicode-prefix [:solver-claim :unknown]')&&t.includes(':same-complete-question true')&&t.includes(':graphemes 1')&&t.includes(':codepoints 2')&&t.includes(':runtime-floats :separate-profile-required'));
    if(id==='story-recorded-verdicts')check(size.name+': search and ledger preserve presence without authority',t.includes(':nil-present true')&&t.includes(':false-witness false')&&t.includes(':sampled-absence :unknown')&&t.includes(':assurance :recorded')&&t.includes(':question-retained true')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#a-contract-can-generate-its-own-responses');
  check(size.name+': response chapter preserves fault and boundary distinctions',await evaluate("document.body.innerText.includes('This is stronger than failing their conjunction')&&document.body.innerText.includes('1,274 focused assertions')&&document.body.innerText.includes('8,102 regression assertions')&&document.body.innerText.includes('missing values are never invented')"));
  await evaluate("document.querySelector('#a-contract-can-generate-its-own-responses').scrollIntoView({block:'start'})");
  await shot(size.name+'-response-contracts');
  await click('[data-graph="formal-response-contracts"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="boundary"]');
  check(size.name+': boundary panel separates feasible replay and unchecked optimality',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-response-contracts\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('strict-improvement question')&&t.includes('cannot establish an optimum or unboundedness')&&t.includes('unchecked optimality claim')})()"));
  await evaluate("document.querySelector('[data-graph=\"formal-response-contracts\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
  await shot(size.name+'-response-boundary-panel');
  if(size.name==='desktop'){
    await click('#theme');await shot(size.name+'-response-boundary-night');await click('#theme');
  }
  await click('[data-graph="formal-response-contracts"] .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="reply"]');
  check(size.name+': reply panel binds complete questions and validates actual fields',await evaluate("(()=>{const t=document.querySelector('[data-graph=\"formal-response-contracts\"] .sg-stage>[data-view]:not([hidden])').innerText;return t.includes('refuses foreign questions')&&t.includes('every original condition and pin')&&t.includes('final absence question gets no witness')})()"));
  await evaluate("document.querySelector('[data-graph=\"formal-response-contracts\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
  await shot(size.name+'-answer-binding-panel');
  if(size.name==='phone'){
    await evaluate("(()=>{const d=document.querySelector('[data-graph=\"formal-response-contracts\"] .sg-stage>[data-view]:not([hidden]) .review-detail');d.scrollTop=d.scrollHeight})()");
    check(size.name+': reply evidence remains readable above the graph controls after panel scroll',await evaluate("(()=>{const g=document.querySelector('[data-graph=\"formal-response-contracts\"]'),d=g.querySelector('.sg-stage>[data-view]:not([hidden]) .review-detail'),r=d.querySelector('.review-facts dd').getBoundingClientRect(),box=d.getBoundingClientRect(),tools=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=box.top&&r.bottom<=box.bottom&&r.bottom<=tools.top})()"));
    await shot(size.name+'-answer-binding-details');
  }
  if(size.name==='desktop'){
    await click('#theme');
    await evaluate("document.querySelector('[data-graph=\"formal-response-contracts\"] .sg-stage>[data-view]:not([hidden])').scrollIntoView({block:'center'})");
    await shot(size.name+'-answer-binding-night');await click('#theme');
  }
  await navigate('/#a-reply-belongs-to-one-exact-question');
  check(size.name+': reply chapter distinguishes identity replay and durable payloads',await evaluate("document.body.innerText.includes('Asking for zero and asking for a value above ten')&&document.body.innerText.includes('A decoded zero cannot borrow credibility')&&document.body.innerText.includes('explicit payload capacity is 16 MiB')&&document.body.innerText.includes('Missing or corrupt payloads raise an error')"));
  await evaluate("document.querySelector('#a-reply-belongs-to-one-exact-question').scrollIntoView({block:'start'})");
  await shot(size.name+'-answer-binding');
  await navigate('/#a-better-question-shape-can-help-both-engines');
  check(size.name+': preparation chapter retains observed representation gains and limited scope',await evaluate("document.body.innerText.includes('162 checked component certificates')&&document.body.innerText.includes('299 new focused assertions')&&document.body.innerText.includes('8,106 regression assertions')&&document.body.innerText.includes('This does not prove a general normalizer correct')"));
  await evaluate("document.querySelector('#a-better-question-shape-can-help-both-engines').scrollIntoView({block:'start'})");
  await shot(size.name+'-question-preparation');
  const preparationPanel='[data-graph="formal-query-preparation"] .sg-stage>[data-view]:not([hidden])';
  await click(preparationPanel+' .review-index [data-sg-to="checking"]');
  check(size.name+': preparation panel checks actual equality objects and metadata',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(preparationPanel)}).innerText;return t.includes('Check its object afresh')&&t.includes('preserve all metadata')&&t.includes('Missing, extra, foreign and stale proof sites')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(preparationPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-prepared-question-panel');
  if(size.name==='phone'){
    await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(preparationPanel)}).querySelector('.review-detail');d.scrollTop=d.scrollHeight})()`);
    check(size.name+': preparation relationships remain readable after panel scroll',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-query-preparation"]'),d=document.querySelector(${JSON.stringify(preparationPanel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),b=d.getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom&&r.bottom<=t.top})()`));
    await shot(size.name+'-preparation-details');
  }
  if(size.name==='desktop'){
    await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(preparationPanel)}).scrollIntoView({block:'center'})`);
    await shot(size.name+'-preparation-night');await click('#theme');
  }
  await click(preparationPanel+' .review-index [data-sg-to="replay"]');
  check(size.name+': replay panel separates original values from native API access',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(preparationPanel)}).innerText;return t.includes('Native API access and original value availability')&&t.includes('no default native value is invented')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(preparationPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-original-replay-panel');
  await navigate('/#what-a-size-result-actually-means');
  check(size.name+': size chapter gives unknown its own truth result and budgets',await evaluate("document.body.innerText.includes('A tiny theorem-search budget leaves the answer unknown')&&document.body.innerText.includes('The theorem search and preparation search have independent budgets')&&document.body.innerText.includes('checked counterexample to the single-placement bound')"));
  await evaluate("document.querySelector('#what-a-size-result-actually-means').scrollIntoView({block:'start'})");
  await shot(size.name+'-size-evidence');
  await navigate('/#a-large-question-should-still-travel-as-language-data');
  check(size.name+': graph chapter preserves the whole question',await evaluate("document.body.innerText.includes('Saving only a formula digest loses part of the question')&&document.body.innerText.includes('Repeated pieces are stored once')"));
  await evaluate("document.querySelector('#a-large-question-should-still-travel-as-language-data').scrollIntoView({block:'start',behavior:'instant'})");
  await shot(size.name+'-question-graph');
  const graphPanel='[data-graph="formal-question-graphs"] .sg-stage>[data-view]:not([hidden])';
  await click(graphPanel+' .review-index [data-sg-to="sharing"]');
  check(size.name+': opened sharing panel states initial tree cost and canonical ordering',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(graphPanel)}).innerText;return t.includes('Initial conversion still visits the supplied tree')&&t.includes('Children precede parents')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(graphPanel)}).scrollIntoView({block:'center',behavior:'instant'})`);
  await shot(size.name+'-graph-sharing-panel');
  if(size.name==='phone'){
   await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(graphPanel)}).querySelector('.review-detail');d.scrollTo({top:d.scrollHeight,behavior:'instant'})})()`);
   check(size.name+': sharing relationships fit above phone controls after scrolling',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-question-graphs"]'),d=document.querySelector(${JSON.stringify(graphPanel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),b=d.getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom&&r.bottom<=t.top})()`));
   await shot(size.name+'-graph-sharing-details');
  }
  await click(graphPanel+' .review-index [data-sg-to="runtime"]');
  check(size.name+': graph materialization panel keeps unfamiliar atoms and equality refusal visible',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(graphPanel)}).innerText;return t.includes('existing keywords only')&&t.includes('Runtime machinery is refused')&&t.includes('collapse distinct entries')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(graphPanel)}).scrollIntoView({block:'center',behavior:'instant'})`);
  await shot(size.name+'-graph-runtime-panel');
  if(size.name==='phone'){
   await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(graphPanel)}).querySelector('.review-detail');d.scrollTop=d.scrollHeight})()`);
   await shot(size.name+'-graph-runtime-details');
  }
  if(size.name==='desktop'){
   await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(graphPanel)}).scrollIntoView({block:'center',behavior:'instant'})`);await shot(size.name+'-graph-night');await click('#theme');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-question-graph','story-graph-point','story-graph-budget']){
   const text=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
   check(size.name+': visible graph result '+id,text.length>100);
   if(id==='story-question-graph')check(size.name+': repeated data keeps exact kinds in six stored nodes',text.includes(':stored-nodes 6')&&text.includes(':expanded-nodes 5001')&&text.includes(':exact-roundtrip true'));
   if(id==='story-graph-point')check(size.name+': graph point opts in explicitly without native or kernel authority',text.includes(':point-version 2')&&text.includes(':question-profile :bl/public-data-graph-v1')&&text.includes(':old-interface :rejected')&&text.includes(':checking :checked-data-connection')&&text.includes(':native-query-calls 0')&&text.includes(':kernel-execution :not-run'));
   if(id==='story-graph-budget')check(size.name+': expansion bomb is refused before decoding',text.includes(':small-graph-nodes 21')&&text.includes(':expanded-nodes 2097151')&&text.includes(':next-doubling :refused')&&text.includes(':decoded-before-refusal false'));
   await evaluate(`document.querySelector('#cell-${id}').scrollIntoView({block:'center',behavior:'instant'})`);await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#use-the-saved-question-without-unpacking-its-history');
  check(size.name+': graph chapter describes completed interface and corpus',await evaluate("(()=>{let h=document.querySelector('#use-the-saved-question-without-unpacking-its-history'),t='';for(let e=h?.nextElementSibling;e&&!/^H[123]$/.test(e.tagName);e=e.nextElementSibling)t+=e.innerText;return t.includes('The common BL interface now carries')&&t.includes('all 187 paired graph contexts retain their preceding results')&&!t.includes('full graph-context corpus is pending')})()"));
  check(size.name+': graph consumer chapter keeps saved context and reports separate',await evaluate("document.body.innerText.includes('Changing that provenance still changes the complete question reference')&&document.body.innerText.includes('Reopening a saved execution label does not establish a new execution')"));
  await evaluate("document.querySelector('#use-the-saved-question-without-unpacking-its-history').scrollIntoView({block:'start',behavior:'instant'})");
  await shot(size.name+'-graph-consumers');
  const consumerPanel='[data-graph="formal-graph-consumers"] .sg-stage>[data-view]:not([hidden])';
  await click(consumerPanel+' .review-index [data-sg-to="selected"]');
  check(size.name+': selected term view leaves unknown provenance as bytes',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(consumerPanel)}).innerText;return t.includes('stays bytes rather than becoming a VM atom')&&t.includes('scope-sensitive validator and evaluator')&&t.includes('materialize!')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(consumerPanel)}).scrollIntoView({block:'center',behavior:'instant'})`);
  await shot(size.name+'-graph-selected-panel');
  if(size.name==='desktop'){
   await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(consumerPanel)}).scrollIntoView({block:'center',behavior:'instant'})`);await shot(size.name+'-graph-consumers-night');await click('#theme');
  }
  await click(consumerPanel+' .review-index [data-sg-to="ledger"]');
  check(size.name+': durable panel separates graph payloads and recorded assurance',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(consumerPanel)}).innerText;return t.includes('once, with separate answer')&&t.includes('false and nil keep their presence')&&t.includes('cannot grant compiler authority')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(consumerPanel)}).scrollIntoView({block:'center',behavior:'instant'})`);await shot(size.name+'-graph-ledger-panel');
  if(size.name==='phone'){
   await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(consumerPanel)}).querySelector('.review-detail');d.scrollTo({top:d.scrollHeight,behavior:'instant'})})()`);
   check(size.name+': graph ledger relationships fit above phone controls',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-graph-consumers"]'),d=document.querySelector(${JSON.stringify(consumerPanel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),b=d.getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom&&r.bottom<=t.top})()`));
   await shot(size.name+'-graph-ledger-details');
  }
  await click(consumerPanel+' .review-index [data-sg-to="proof"]');
  check(size.name+': graph proof panel keeps metatheory and implementation connection open',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(consumerPanel)}).innerText;return t.includes('finite shared tables')&&t.includes('compiler correctness remain separate obligations')})()`));
  await navigate('/#s-the-model-running');
  const consumerReferences=[];
  for(const id of ['story-graph-selected','story-graph-native','story-graph-intercepted','story-graph-durable']){
   const text=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
   check(size.name+': visible graph consumer result '+id,text.length>100);
   const ref=text.match(/:sha256\s+"([0-9a-f]{64})"/);if(ref)consumerReferences.push(ref[1]);
   if(id==='story-graph-selected')check(size.name+': selected terms work while unknown full materialization refuses',text.includes(':full-materialization :refused')&&text.includes(':original-point :checked-data-connection')&&text.includes(':next 8'));
   if(id==='story-graph-native')check(size.name+': both engines share an explicit graph reply format',text.includes(':reply-versions [2 2]')&&text.includes(':same-complete-reference true')&&text.includes(':verdicts [:sat :sat]'));
   if(id==='story-graph-intercepted')check(size.name+': graph handler replay replaces a supplied observation without native execution',text.includes(':supplied-next 999')&&text.includes(':replayed-next 8')&&text.includes(':provided-fallback :not-invoked'));
   if(id==='story-graph-durable')check(size.name+': reopened graph record does not claim execution or compiler authority',text.includes(':assurance :recorded')&&text.includes(':queries-during-record-and-recheck 0')&&text.includes(':actual-execution-claimed-by-recheck false')&&text.includes(':compiler-proof-authority false'));
   await evaluate(`document.querySelector('#cell-${id}').scrollIntoView({block:'center',behavior:'instant'})`);await shot(size.name+'-'+id+'-data');
  }
  check(size.name+': all four graph consumer cells retain one complete question',consumerReferences.length===4&&new Set(consumerReferences).size===1);
  await navigate('/#model-access-and-recovered-values-are-different-facts');
  check(size.name+': model access chapter preserves unavailable original coordinates',await evaluate("document.body.innerText.includes('That label belongs to the executed question')&&document.body.innerText.includes('incomplete original replay')"));
  await evaluate("document.querySelector('#model-access-and-recovered-values-are-different-facts').scrollIntoView({block:'start'})");
  await shot(size.name+'-model-replay');
  await navigate('/#an-explicit-input-can-outlive-a-missing-solver-model');
  check(size.name+': explicit point chapter separates backend answer, data and Source',await evaluate("document.body.innerText.includes('mathematical point against the complete question')&&document.body.innerText.includes('three inspectable facts')"));
  await evaluate("document.querySelector('#an-explicit-input-can-outlive-a-missing-solver-model').scrollIntoView({block:'start'})");
  await shot(size.name+'-explicit-point');
  const pointPanel='[data-graph="formal-explicit-points"] .sg-stage>[data-view]:not([hidden])';
  await click(pointPanel+' .review-index [data-sg-to="check"]');
  check(size.name+': pure point panel keeps Source and metatheory outside data checking',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(pointPanel)}).innerText;return t.includes('performs no Source compilation')&&t.includes('Lean receipts are not borrowed')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(pointPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-point-check-panel');
  if(size.name==='phone'){
    await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(pointPanel)}).querySelector('.review-detail');d.scrollTop=d.scrollHeight})()`);
    check(size.name+': point relationships fit above phone controls',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-explicit-points"]'),d=document.querySelector(${JSON.stringify(pointPanel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),b=d.getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom&&r.bottom<=t.top})()`));
    await shot(size.name+'-point-check-details');
  }
  if(size.name==='desktop'){
    await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(pointPanel)}).scrollIntoView({block:'center'})`);
    await shot(size.name+'-point-night');await click('#theme');
  }
  await click(pointPanel+' .review-index [data-sg-to="actual"]');
  check(size.name+': point Source panel keeps runtime kinds and mismatch visible',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(pointPanel)}).innerText;return t.includes('runtime kinds differ')&&t.includes('mismatch remains disagreement')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(pointPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-point-source-panel');
  await click(pointPanel+' .review-index [data-sg-to="domain"]');
  check(size.name+': Float generator panel distinguishes finite cardinality and budgets',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(pointPanel)}).innerText;return t.includes('both signed zeros')&&t.includes('Enumeration budgets and finite cardinality')&&t.includes('Int endpoints')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(pointPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-point-domain-panel');
  await navigate('/#s-the-model-running');
  for(const id of ['story-explicit-point','story-explicit-source','story-float-domain','story-runtime-kinds']){
    const t=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
    check(size.name+': visible executed point result '+id,t.length>100);
    if(id==='story-explicit-point')check(size.name+': exact rational point is data checked without borrowed kernel authority',t.includes(':original-point :checked-data-connection')&&t.includes(':formal/real [1 3]')&&t.includes(':kernel-execution :not-run')&&t.includes(':native-query-calls 0')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-explicit-source')check(size.name+': native unknown coexists with an explicitly reproduced Source counterexample',t.includes(':native-verdicts [:refuted :unknown]')&&t.includes(':same-complete-question true')&&t.includes(':explicit-point :checked-data-connection')&&t.includes(':source-observation :reproduced')&&t.includes(':explicit-verdict :refuted')&&t.includes(':verdict-basis :explicit-original-point')&&t.includes(':module-retired true'));
    if(id==='story-float-domain')check(size.name+': Float enumeration keeps finite cardinality and both zeros',t.includes(':cardinality 2')&&t.includes('9223372036854775808')&&t.includes(':all-finite-patterns 18437736874454810624')&&t.includes(':all-domain-finite true')&&t.includes(':all-enumeration :over-budget')&&t.includes(':int-is-float-input false')&&t.includes(':legacy-real-admits-int true'));
    if(id==='story-runtime-kinds')check(size.name+': numeric equality does not erase successful result kind',t.includes(':numeric-equality true')&&t.includes(':int-observation-accepts-float false')&&t.includes(':successful-values-equivalent false')&&t.includes(':both-raised-equivalent true')&&t.includes(':exception-categories :outside-profile'));
    await evaluate(`document.querySelector('#cell-${id}').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#float-arithmetic-must-mean-the-same-thing-in-the-program-and-the-proof');
  check(size.name+': Float chapter explains the observed false Real proof',await evaluate("document.body.innerText.includes('the original compiled predicate made false')&&document.body.innerText.includes('Failure stays in the claim')"));
  await evaluate("document.querySelector('#float-arithmetic-must-mean-the-same-thing-in-the-program-and-the-proof').scrollIntoView({block:'start'})");
  await shot(size.name+'-float-source');
  const floatPanel='[data-graph="formal-float-source"] .sg-stage>[data-view]:not([hidden])';
  await click(floatPanel+' .review-index [data-sg-to="replay"]');
  check(size.name+': Float replay distinguishes implementation checks from preservation',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(floatPanel)}).innerText;return t.includes('integer and rational arithmetic')&&t.includes('not a machine-checked IEEE theorem')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(floatPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-float-replay-panel');
  if(size.name==='phone'){
    await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(floatPanel)}).querySelector('.review-detail');d.scrollTop=d.scrollHeight})()`);
    check(size.name+': Float panel relationships remain above phone controls',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-float-source"]'),d=document.querySelector(${JSON.stringify(floatPanel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),b=d.getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom&&r.bottom<=t.top})()`));
    await shot(size.name+'-float-replay-details');
  }
  if(size.name==='desktop'){
    await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(floatPanel)}).scrollIntoView({block:'center'})`);
    await shot(size.name+'-float-night');await click('#theme');
  }
  await click(floatPanel+' .review-index [data-sg-to="legacy"]');
  check(size.name+': Float legacy panel grants no Source proof to ideal models',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(floatPanel)}).innerText;return t.includes('return unsupported by default')&&t.includes('grants no Source proof')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(floatPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-float-legacy-panel');
  await navigate('/#s-the-model-running');
  for(const id of ['story-float-source','story-float-backends']){
    const t=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
    check(size.name+': visible executed Float result '+id,t.length>100);
    if(id==='story-float-source')check(size.name+': Float Source cell demonstrates the repaired mismatch and zero distinction',t.includes(':term-value false')&&t.includes(':actual-value false')&&t.includes(':legacy-source-status :unsupported')&&t.includes(':legacy-source-holds nil')&&t.includes(':zeros-numerically-equal true')&&t.includes(':zeros-strictly-identical false')&&t.includes(':module-retired true')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-float-backends')check(size.name+': Float backends receive identical questions without certificate authority',t.includes(':same-complete-question true')&&t.includes(':backends [:z3 :oxiz]')&&t.includes(':native-proof-certificate :not-checked')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id}').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  await navigate('/#a-migration-needs-three-separate-answers');
  check(size.name+': migration chapter separates admitted inputs, conditional truth and delivery',await evaluate("document.body.innerText.includes('9,891 assertion executions')&&document.body.innerText.includes('Neither failure becomes an assumption')&&document.body.innerText.includes('Re-elaboration may execute phase code')&&document.body.innerText.includes('Every result keeps compiler and delivery authority false')"));
  await evaluate("document.querySelector('#a-migration-needs-three-separate-answers').scrollIntoView({block:'start'})");
  await shot(size.name+'-message-migration');
  const migrationPanel='[data-graph="formal-message-migration"] .sg-stage>[data-view]:not([hidden])';
  await click(migrationPanel+' .review-index [data-sg-to="certificate"]');
  check(size.name+': migration checking panel keeps certificate and admission independent',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(migrationPanel)}).innerText;return t.includes('Native proved cannot replace a missing certificate')&&t.includes('Verified true requires both checked facts')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(migrationPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-migration-certificate-panel');
  if(size.name==='phone'){
    await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(migrationPanel)}).querySelector('.review-detail');d.scrollTop=d.scrollHeight})()`);
    check(size.name+': migration relationships remain readable above phone controls',await evaluate(`(()=>{const g=document.querySelector('[data-graph="formal-message-migration"]'),d=document.querySelector(${JSON.stringify(migrationPanel)}).querySelector('.review-detail'),r=d.querySelector('.review-related').getBoundingClientRect(),b=d.getBoundingClientRect(),t=g.querySelector('.sg-toolbar').getBoundingClientRect();return r.top>=b.top&&r.bottom<=b.bottom&&r.bottom<=t.top})()`));
    await shot(size.name+'-migration-details');
  }
  if(size.name==='desktop'){
    await click('#theme');await evaluate(`document.querySelector(${JSON.stringify(migrationPanel)}).scrollIntoView({block:'center'})`);
    await shot(size.name+'-migration-night');await click('#theme');
  }
  await click(migrationPanel+' .review-index [data-sg-to="source"]');
  check(size.name+': Source observation panel retains one-invocation and function-correspondence limits',await evaluate(`(()=>{const t=document.querySelector(${JSON.stringify(migrationPanel)}).innerText;return t.includes('not universal compiler preservation')&&t.includes('neither invoked nor certified')&&t.includes('compile or publication error remains an observer error')})()`));
  await evaluate(`document.querySelector(${JSON.stringify(migrationPanel)}).scrollIntoView({block:'center'})`);
  await shot(size.name+'-migration-source-panel');
  if(size.name==='phone'){
    await evaluate(`(()=>{const d=document.querySelector(${JSON.stringify(migrationPanel)}).querySelector('.review-detail');d.scrollTop=d.scrollHeight})()`);
    await shot(size.name+'-migration-source-details');
  }
  await navigate('/#s-the-model-running');
  for(const id of ['story-response-relation','story-response-faults','story-response-boundary','story-response-assumptions','story-response-completion','story-response-ledger','story-answer-binding']){
    const t=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
    check(size.name+': visible executed response result '+id,t.length>100);
    if(id==='story-response-relation')check(size.name+': response source replay and exact mathematical rationals stay distinct',t.includes(':responses [:witnessed :witnessed]')&&t.includes(':source-replay [:reproduced :reproduced]')&&t.includes(':formal/real [1 3]')&&t.includes(':math-source-claim false')&&t.includes(':same-complete-question true'));
    if(id==='story-response-faults')check(size.name+': isolated all-law and vacuous results retain separate meanings',t.includes(':isolated [[:witnessed :witnessed :solver-claim] [:witnessed :witnessed :solver-claim]]')&&t.includes(':infeasible-premises [:vacuous :vacuous]')&&t.includes(':any-law-fails :witnessed')&&t.includes(':every-law-fails :solver-claim'));
    if(id==='story-response-boundary')check(size.name+': global minimum keeps feasibility and budget limitations',t.includes(':minimum [-41 -41]')&&t.includes(':feasibility [:witnessed :witnessed]')&&t.includes(':optimality [:solver-claim :solver-claim]')&&t.includes(':budget-result :candidate')&&t.includes(':unboundedness :not-established'));
    if(id==='story-response-assumptions')check(size.name+': semantic assumptions retain conditions and bounded scope',t.includes(':semantic-assumptions :conditions-preserved')&&t.includes(':native-verdicts [:proved :proved]')&&t.includes(':scope :bounded')&&t.includes(':certificate :not-checked'));
    if(id==='story-response-completion')check(size.name+': missing OxiZ coordinates remain candidates until concrete pins replay',t.includes(':unconstrained-models [:witnessed :candidate]')&&t.includes(':oxiz-model :partial')&&t.includes(':pinned-crashes [:raised :raised]')&&t.includes(':invented-native-values false'));
    if(id==='story-response-ledger')check(size.name+': compound ledger evidence grants no witness or proof to the absence claim',t.includes(':assurance :recorded')&&t.includes(':top-level-witness false')&&t.includes(':feasible-value {:x -41}')&&t.includes(':absence-claim :unsat')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-answer-binding')check(size.name+': both engines reject foreign replies and conflicting decoded points',t.includes(':native-question-bound [true true]')&&t.includes(':published [:witnessed :witnessed]')&&t.includes(':response-replay [:valid :valid]')&&t.includes(':foreign-models [:error :error]')&&t.includes(':foreign-absence [:error :error]')&&t.includes(':decoded-mismatch [:candidate :candidate]')&&t.includes(':mismatch-replay [:invalid :invalid]')&&t.includes(':compiler-proof-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  for(const id of ['story-query-preparation','story-size-evidence','story-original-replay','story-message-migration']){
    const t=await evaluate(`document.querySelector('#cell-${id} .result')?.innerText||''`);
    check(size.name+(id==='story-message-migration'?': visible executed migration result ':': visible executed preparation result ')+id,t.length>150);
    if(id==='story-query-preparation')check(size.name+': same checked plan improves the OxiZ examples without native proof promotion',t.includes(':original [:proved :unknown]')&&t.includes(':prepared [:proved :proved]')&&t.includes(':doubled [:refuted :refuted]')&&t.includes(':connections [:checked :checked]')&&t.includes(':counterexample-replay [:valid :valid]')&&t.includes(':native-certificate :not-checked'));
    if(id==='story-size-evidence')check(size.name+': size results distinguish true false and unknown with independent checking',t.includes(':families [:checked :refuted :unknown]')&&t.includes(':holds [true false nil]')&&t.includes(':fresh-positive-objects [:checked :checked]')&&t.includes(':single-placement-counterexample :checked-data-connection')&&t.includes(':negative-controls :checked')&&t.includes(':limited-native-claim :proved')&&t.includes(':arity-zero-double-placement :checked')&&t.includes(':compiler-proof-authority false'));
    if(id==='story-original-replay')check(size.name+': executed constants do not invent original coordinates',t.includes(':satisfiability [:sat :sat]')&&t.includes(':execution-observations [0 0]')&&t.includes(':original-bindings [:incomplete :incomplete]')&&t.includes(':original-observations [:incomplete :incomplete]')&&t.includes(':original-values [:unavailable :unavailable]')&&t.includes(':invented-coordinates false'));
    if(id==='story-message-migration')check(size.name+': migration results retain checked truth, Native-only nil and actual Source cleanup',t.includes(':positive [:checked :checked]')&&t.includes(':negative [:refuted :refuted]')&&t.includes(':verified-positive [true true]')&&t.includes(':verified-negative [false false]')&&t.includes(':verified-native-only [nil nil]')&&t.includes(':fresh-certificates [:checked :checked]')&&t.includes(':admission [:checked-data-connection :checked-data-connection]')&&t.includes(':source-replay :valid')&&t.includes(':actual-value 5')&&t.includes(':module-retired true')&&t.includes(':delivery-authority false'));
    await evaluate(`document.querySelector('#cell-${id} .result').scrollIntoView({block:'center'})`);
    await shot(size.name+'-'+id+'-data');
  }
  const canonical=await evaluate("document.querySelector('#cell-story-canonical-identity')?.innerText||''");
  check(size.name+': canonical identity preserves namespaces and collection kinds',canonical.includes(':identity-profile :bl/canonical-formal-data-v1')&&canonical.includes(':reordered-map :same-identity')&&canonical.includes(':keyword-namespaces :preserved')&&canonical.includes(':vector-and-list :distinct')&&canonical.includes(':runtime-authority-granted false'));
  await evaluate("document.querySelector('#cell-story-canonical-identity').scrollIntoView({block:'center'})");
  await shot(size.name+'-canonical-identity');
  await navigate('/#a-promise-about-the-function-you-actually-wrote');
  check(size.name+': source handler semantics are readable',await evaluate("document.body.innerText.includes('A promise about the function you actually wrote')&&document.body.innerText.includes('Even an empty state record cannot hide the error.')"));
  await shot(size.name+'-source-handler');
  await navigate('/#s-the-big-idea');
  check(size.name+': comparison reference role grants no authority',await evaluate("document.body.innerText.includes('Z3 is now called the reference engine')&&document.body.innerText.includes('That role gives it no compiler authority')"));
  await evaluate("[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Let the optimizer propose'))?.scrollIntoView({block:'start'})");
  check(size.name+': chapter heading stays below navigation',await evaluate(`[...document.querySelectorAll('h2,h3')].find(e=>e.innerText.includes('Let the optimizer propose')).getBoundingClientRect().top>=${size.mobile?100:40}`));
  await shot(size.name+'-checked-changes');
  await navigate('/#s-a-path-we-can-actually-build');
  await click('#milestones-formal-delivery [data-milestone-to="M3"]');
  check(size.name+': milestone selects its own detail',await evaluate("!document.querySelector('[data-milestone-detail=\"M3\"]').hidden"));
  await shot(size.name+'-milestones');
  await click('#milestones-formal-delivery [data-milestone-detail="M3"] [data-milestone-to="M2"]');
  check(size.name+': milestone dependency navigates',await evaluate("!document.querySelector('[data-milestone-detail=\"M2\"]').hidden"));
  await click('#milestones-formal-delivery [data-milestone-to="M3"]');
  await evaluate("fetch('/doc').then(r=>r.json()).then(d=>{window.__auditDoc=d;return true})");
  check(size.name+': live refresh endpoint retains selected milestone',await evaluate("!document.querySelector('[data-milestone-detail=\"M3\"]').hidden&&!!window.__auditDoc.rev"));
  await navigate('/#s-try-the-language-ideas');
  await wait("!!document.querySelector('[data-source-id=\"story-lab\"] iframe')?.contentDocument?.querySelector('.fl-app')");
  check(size.name+': preview uses public source components',await evaluate("!!document.querySelector('[data-source-id=\"story-lab\"] iframe').contentDocument.querySelector('[data-ui-component=\"formal-answer\"]')"));
  await shot(size.name+'-source-preview');
  await click('#claims-formal-promises [data-claims-filter="open"]');
  check(size.name+': promises ledger keeps missing screens visibly open',await evaluate("(()=>{const r=document.querySelector('#claims-formal-promises');const rows=[...r.querySelectorAll('.cl-row')].filter(e=>!e.hidden);return rows.length===2&&rows.every(e=>e.dataset.open==='1')})()"));
  await shot(size.name+'-open-promises');
  await click('#claims-formal-promises [data-claims-filter="open"]');
  await click('#claims-formal-promises [data-claims-view="maps"]');
  await wait("!!document.querySelector('#claims-formal-promises .cl-frame')?.contentDocument?.querySelector('[data-ui-composition=\"maps\"]')");
  check(size.name+': promise opens its actual source-backed view',await evaluate("document.querySelector('#claims-formal-promises .cl-dialog').open"));
  await shot(size.name+'-promise-view');
  await call({op:'key',key:'Escape'});
  check(size.name+': promise dialog restores focus',await evaluate("!document.querySelector('#claims-formal-promises .cl-dialog').open&&document.activeElement===document.querySelector('#claims-formal-promises [data-claims-view=\"maps\"]')"));
  await navigate('/#s-could-beam-lisp-be-fully-formal');
  await click('#lifetime-formal-proof-lifetime .lt-scroll [data-lt-item="s1"]');
  check(size.name+': proof lifetime opens the selected explanation',await evaluate("!document.querySelector('#lifetime-formal-proof-lifetime [data-lt-detail=\"s1\"]').hidden"));
  check(size.name+': proof lifetime contains scrolling within its panel',await evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+2"));
  await shot(size.name+'-proof-lifetime');
  await call({op:'key',key:'Escape'});
  check(size.name+': proof lifetime Escape clears detail',await evaluate("[...document.querySelectorAll('#lifetime-formal-proof-lifetime [data-lt-detail]')].every(e=>e.hidden)"));
  await navigate('/#s-try-the-language-ideas');
  await click('[data-source-id="story-lab"] [data-source-highlight]');
  check(size.name+': source link highlighting remains available',await evaluate("document.querySelector('[data-source-id=\"story-lab\"] [data-source-highlight]').getAttribute('aria-pressed')==='true'"));
  await click('[data-source-id="story-lab"] [data-source-highlight]');
  await click('[data-source-id="story-lab"] [data-source-inspect]');
  check(size.name+': source component inspection remains available',await evaluate("document.querySelector('[data-source-id=\"story-lab\"] [data-source-inspect]').getAttribute('aria-pressed')==='true'"));
  await click('[data-source-id="story-lab"] [data-source-inspect]');
  await click('[data-source-id="story-lab"] [data-source-mode]');
  await wait("document.querySelectorAll('[data-source-id=\"story-lab\"] .sg-node').length>=5");
  check(size.name+': source graph discovers all five declared views',await evaluate("document.querySelectorAll('[data-source-id=\"story-lab\"] .sg-node').length===5"));
  await shot(size.name+'-source-map');
  await click('[data-source-id="story-lab"] [data-source-mode]');
  for(const view of ['maps','accounts','bits','fp','evidence']){
   await navigate('/views?view='+view);
   check(size.name+'/'+view+': rendered shared composition',await evaluate(`!!document.querySelector('[data-ui-composition="${view}"]')`));
   const width=await evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+2');check(size.name+'/'+view+': no page overflow',width);
   if(view==='evidence')check(size.name+': evidence view reflects the implemented checker and its boundary',await evaluate("document.body.innerText.includes('The foundation now has code')&&document.body.innerText.includes('source/runtime correspondence remains unproved')"));
  }
  await shot(size.name+'-evidence');
  await navigate('/explorer?q=family:Evidence%20state:Candidate');
  check(size.name+': explorer query narrows actual state examples',await evaluate("document.querySelectorAll('.fl-specimen-example').length===1&&!!document.querySelector('.fl-answer.candidate')"));
  await navigate('/explorer?q=bad:query');check(size.name+': invalid query is explained',await evaluate("document.body.innerText.includes('Use id:')"));
  await navigate('/#s-watch-the-evidence');
  await wait("document.querySelectorAll('#witness-formal-browser-witness .witness-steps button').length>=5");
  await click('#witness-formal-browser-witness [data-witness-move="1"]');
  check(size.name+': witness advances recorded claim',await evaluate("document.querySelector('#witness-formal-browser-witness [data-witness-position]').innerText.startsWith('2 /')"));
  await evaluate("document.querySelector('#witness-formal-browser-witness .witness-stage:not([hidden]) img').scrollIntoView({block:'center'})");
  await wait("[...document.querySelectorAll('#witness-formal-browser-witness .witness-stage:not([hidden]) img')].some(i=>i.complete&&i.naturalWidth>0)");
  check(size.name+': witnessed frame is an actual loaded image',await evaluate("[...document.querySelectorAll('#witness-formal-browser-witness .witness-stage:not([hidden]) img')].every(i=>i.complete&&i.naturalWidth>0)"));
  await shot(size.name+'-witness');
  await navigate('/#s-the-presentation-language');
  await click('#theme');check(size.name+': dark theme changes document',await evaluate("document.documentElement.dataset.theme==='dark'"));
  await shot(size.name+'-night');await click('#theme');
  await navigate('/#all');
  const graphs=await evaluate("[...document.querySelectorAll('.screen-graph[data-graph]')].filter(g=>g.querySelector('.review-app')).map(g=>g.dataset.graph)");
  for(const id of graphs){
   const root=`[data-graph="${id}"]`;
   await click(root+' [data-sg-reset]');
   const start=await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view`);
   const target=await evaluate(`(()=>{const g=document.querySelector('${root}');return [...g.querySelectorAll('.review-index [data-sg-to]')].find(e=>e.dataset.sgTo!==${JSON.stringify(start)})?.dataset.sgTo})()`);
   await click(root+` .sg-stage>[data-view]:not([hidden]) .review-index [data-sg-to="${target}"]`);
   check(size.name+'/'+id+': connected topic opens',await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view===${JSON.stringify(target)}`));
   await click(root+' [data-sg-back]');
   check(size.name+'/'+id+': Back restores the topic',await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view===${JSON.stringify(start)}`));
   await click(root+' [data-sg-mode]');
   check(size.name+'/'+id+': map contains every topic',await evaluate(`(()=>{const g=document.querySelector('${root}');return g.querySelectorAll('.sg-overview .sg-node').length===g.querySelectorAll('.sg-stage>[data-view]').length})()`));
   await click(root+` .sg-overview .sg-node[data-sg-to="${target}"]`);
   check(size.name+'/'+id+': map selection returns to detail',await evaluate(`document.querySelector('${root} .sg-stage>[data-view]:not([hidden])').dataset.view===${JSON.stringify(target)}`));
   await click(root+' [data-sg-expand]');
   check(size.name+'/'+id+': full-screen focus scope opens',await evaluate(`document.querySelector('${root}').classList.contains('sg-expanded')&&document.querySelector('${root} .sg-workbench').getAttribute('aria-modal')==='true'`));
   await call({op:'key',key:'Escape'});
   check(size.name+'/'+id+': Escape returns focus',await evaluate(`!document.querySelector('${root}').classList.contains('sg-expanded')&&document.activeElement===document.querySelector('${root} [data-sg-expand]')`));
  }
 }
 const record=await fetch(base+'/explorer.json?q=family:Comparison').then(r=>r.json());
 check('Catalog comes from three annotated renderer definitions',record.length===1&&record[0].qualified==='formal.presentation/comparison-card'&&record[0].source.endsWith('presentation.bl'));
 check('Unknown preview routes refuse explicitly',(await fetch(base+'/views?view=missing')).status===404);
 check('Anonymous answer writes are denied',(await fetch(base+'/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:'formal-total-core-direction',answer:'agree'})})).status===403);
 for(const path of ['/metatheory/Core.lean','/evidence/metatheory/qualification.json','/evidence/contracts/qualification.json','/sdk-src/formal/certificate.bl','/LOOPS.md','/evidence/loops/examples.json','/evidence/loops/qualification.json','/evidence/loops/model-qualification.json','/TRANSLATION.md','/src/formal/translation.bl','/src/formal/optimize.bl','/sdk-src/formal/result.bl','/src/formal/api.bl','/evidence/translation/qualification.json','/evidence/translation/examples.json','/PROTOCOLS.md','/sdk-src/formal/protocol.bl','/sdk-src/formal/protocol-run.bl','/evidence/protocol/model-qualification.json','/evidence/protocol/examples.json','/evidence/protocol/qualification.json','/BOUNDED-TRACES.md','/src/formal/protocol-trace.bl','/evidence/protocol-traces/examples.json','/evidence/protocol-traces/qualification.json','/evidence/protocol-traces/model-qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared source/evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/sdk-pin.json','/metatheory/tool-pin.json','/evidence/metatheory/Core.olean','/evidence/actor-runtime/examples.etf','/evidence/actor-runtime/ordinary-update.beam']){
  check('Undeclared or binary project file stays unavailable: '+path,(await fetch(base+path)).status===404);
 }
 for(const path of ['/RECORD-HANDLERS.md','/src/formal/source-protocol.bl','/test/source_trace_test.bl','/evidence/source-traces/checks.txt','/evidence/source-traces/examples.json','/evidence/source-traces/qualification.json','/evidence/source-traces/model-qualification.json','/evidence/record-handlers/examples.json','/evidence/record-handlers/implementation-qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared source handler/trace evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/RUNTIME-OBSERVATIONS.md','/src/formal/runtime-protocol.bl','/src/formal/runtime-artifact.bl','/src/formal/runtime-outcome.bl','/src/formal/runtime-actor.bl','/test/runtime_protocol_test.bl','/evidence/actor-runtime/integrated-checks.txt','/evidence/actor-runtime/examples.json','/evidence/actor-runtime/fresh-replay.json','/evidence/actor-runtime/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared actual-runtime evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/INTRINSICS.md','/sdk-src/formal/intrinsics.bl','/src/formal/elaborate.bl','/test/intrinsics_test.bl','/evidence/intrinsics/intrinsics-probe.json','/evidence/intrinsics/checks.txt','/evidence/intrinsics/fresh-replay.json','/evidence/intrinsics/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared callee-identity evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/CONTEXTS.md','/DATA-IDENTITY.md','/src/formal/context.bl','/sdk-src/formal/identity.bl','/src/formal/contract.bl','/test/context_test.bl','/test/identity_test.bl','/context-check.bl','/evidence/contexts/probe.json','/evidence/contexts/checks.txt','/evidence/contexts/examples.json','/evidence/contexts/fresh-replay.json','/evidence/contexts/qualification.json','/evidence/contexts/canonical-fixtures.json','/evidence/contexts/original-byte-reproduction.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared binding/identity evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/SELECTED-SOURCE.md','/src/formal/selected.bl','/sdk-src/formal/source.bl','/test/selected_test.bl','/test/source_test.bl','/evidence/source-selection/checks.txt','/evidence/source-selection/selected-third-check.txt','/evidence/source-selection/examples/selected-examples.json','/evidence/source-selection/fresh/selected-fresh-replay.json','/evidence/source-selection/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared selected Source evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 check('Trusted selected Source ETF archive stays unavailable to the browser',(await fetch(base+'/evidence/source-selection/examples/selected-examples.etf')).status===404);
 for(const path of ['/SELECTED-RUNTIME.md','/src/formal/selected-artifact.bl','/src/formal/selected-runtime.bl','/test/selected_runtime_test.bl','/selected-runtime-recheck.bl','/evidence/selected-runtime/examples/original-selected.json','/evidence/selected-runtime/fresh/original-selected-fresh.json','/evidence/selected-runtime/checks.txt','/evidence/selected-runtime/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared original selected runtime evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 check('Trusted original selected runtime ETF archive stays unavailable to the browser',(await fetch(base+'/evidence/selected-runtime/examples/original-selected.etf')).status===404);
 for(const path of ['/CONNECTIONS.md','/sdk-src/formal/connection.bl','/test/connection_test.bl','/connections-check.bl','/connections-recheck.bl','/evidence/connections/examples/connections.json','/evidence/connections/fresh/connections-fresh.json','/evidence/connections/checks.txt','/evidence/connections/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared connection evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/REFUTATION-KERNEL.md','/sdk-src/formal/refutation.bl','/test/refutation_test.bl','/refutation-check.bl','/refutation-recheck.bl','/metatheory/Refutation.lean','/metatheory/refutation-pin.json','/evidence/refutation-kernel/model-check-3.txt','/evidence/refutation-kernel/bridge-check.txt','/evidence/refutation-kernel/execution/accepted.json','/evidence/refutation-kernel/execution/rejected.json','/evidence/refutation-kernel/examples/weighted.json','/evidence/refutation-kernel/execution/weighted/Check.lean','/evidence/refutation-kernel/execution/weighted/result.json','/evidence/refutation-kernel/fresh/refutation-fresh.json','/evidence/refutation-kernel/checks.txt','/evidence/refutation-kernel/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared normalized-kernel evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 const refutationReceipt=await fetch(base+'/evidence/refutation-kernel/execution/weighted/result.json').then(r=>r.json());
 check('Recorded kernel run preserves its normalized subject and bridge scope',refutationReceipt.status==='checked-normalized-refutation'&&refutationReceipt.term_normalization==='reviewed-not-mechanically-proved'&&refutationReceipt.compiler_proof_authority===false);
 check('Trusted normalized archive stays unavailable to the browser',(await fetch(base+'/evidence/refutation-kernel/examples/refutation.etf')).status===404);
 check('Compiled normalized kernel stays unavailable to the browser',(await fetch(base+'/evidence/refutation-kernel/Refutation.olean')).status===404);
 for(const path of ['/TERM-REFUTATION.md','/metatheory/Terms.lean','/metatheory/terms-pin.json','/test/term_refutation_test.bl','/term-refutation-check.bl','/term-refutation-recheck.bl','/evidence/term-refutation/model-check.txt','/evidence/term-refutation/bridge-check.txt','/evidence/term-refutation/execution/accepted.json','/evidence/term-refutation/execution/rejected.json','/evidence/term-refutation/execution/weighted/Check.lean','/evidence/term-refutation/execution/weighted/result.json','/evidence/term-refutation/fresh/terms-fresh.json','/evidence/term-refutation/checks.txt','/evidence/term-refutation/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared original-term proof evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 const originalReceipt=await fetch(base+'/evidence/term-refutation/execution/weighted/result.json').then(r=>r.json());
 check('Recorded original-term proof keeps checked question and reviewed semantic data separate',originalReceipt.status==='checked-term-entailment'&&originalReceipt.normalization_connection==='checked-countermodel-preservation-for-this-question'&&originalReceipt.general_bl_normalizer_soundness==='not-established'&&originalReceipt.term_data_model_correspondence==='reviewed-data-semantics-bridge'&&originalReceipt.compiler_proof_authority===false);
 check('Trusted original-term archive stays unavailable to the browser',(await fetch(base+'/evidence/term-refutation/examples/terms.etf')).status===404);
 check('Compiled typed term model stays unavailable to the browser',(await fetch(base+'/evidence/term-refutation/Terms.olean')).status===404);
 for(const path of ['/OBLIGATIONS.md','/src/formal/obligation.bl','/src/formal/obligation-examples.bl','/test/obligation_test.bl','/obligations-check.bl','/obligations-recheck.bl','/evidence/obligations/examples/summary.json','/evidence/obligations/execution/results.json','/evidence/obligations/policy-comparison.json','/evidence/obligations/bridge-check.txt','/evidence/obligations/prior-term-regression-check.txt','/evidence/obligations/fresh/obligations-fresh.json','/evidence/obligations/checks.txt','/evidence/obligations/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared common-obligation evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 const obligationResults=await fetch(base+'/evidence/obligations/execution/results.json').then(r=>r.json());
 check('Common obligation receipts preserve complete versus incomplete declared coverage',obligationResults.length===13&&obligationResults.filter(r=>r.status==='checked-required-term-evidence').length===11&&obligationResults.filter(r=>r.status==='incomplete-obligation-evidence').length===2&&obligationResults.every(r=>r.model_theorem==='not-established-by-this-runner'&&r.compiler_proof_authority===false));
 const policyComparison=await fetch(base+'/evidence/obligations/policy-comparison.json').then(r=>r.json());
 check('Recorded axiom-policy comparison retains actual choice and alternative-proof distinction',policyComparison.standard.status==='accepted'&&policyComparison.choice_free.status==='rejected-by-axiom-policy'&&policyComparison.choice_free.observed_dependency==='Classical.choice'&&policyComparison.statement_requires_classical_choice==='not-established'&&policyComparison.compiler_proof_authority===false);
 check('Trusted common-obligation archive stays unavailable to the browser',(await fetch(base+'/evidence/obligations/examples/archives/loop.etf')).status===404);
 for(const path of ['/WITNESSES.md','/sdk-src/formal/query.bl','/sdk-src/formal/witness.bl','/src/formal/witness-examples.bl','/test/query_test.bl','/test/witness_test.bl','/witness-check.bl','/witness-recheck.bl','/metatheory/Witness.lean','/metatheory/witness-pin.json','/evidence/witnesses/model-check.txt','/evidence/witnesses/examples/summary.json','/evidence/witnesses/examples/nonlinear.json','/evidence/witnesses/execution/accepted.json','/evidence/witnesses/execution/rejected.json','/evidence/witnesses/execution/nonlinear/Check.lean','/evidence/witnesses/execution/nonlinear/result.json','/evidence/witnesses/bridge-check.txt','/evidence/witnesses/fresh/witnesses-fresh.json','/evidence/witnesses/checks.txt','/evidence/witnesses/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared constructive witness evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 const witnessAccepted=await fetch(base+'/evidence/witnesses/execution/accepted.json').then(r=>r.json());
 check('Positive witness reports retain constructive typed existence and the original-query bridge',witnessAccepted.length===32&&witnessAccepted.every(r=>r.status==='checked-term-satisfiability'&&r.full_query_connection==='requires-fresh-BL-question-reconstruction'&&r.backend_attestation==='not-established'&&r.compiler_proof_authority===false&&Object.values(r.axioms).flat().every(a=>['propext','Quot.sound'].includes(a))));
 const witnessRejected=await fetch(base+'/evidence/witnesses/execution/rejected.json').then(r=>r.json());
 check('Six changed false or undefined assignments retain Lean rejection',witnessRejected.length===6&&witnessRejected.every(r=>r.status==='rejected-by-lean'));
 check('Trusted constructive witness archive stays unavailable to the browser',(await fetch(base+'/evidence/witnesses/examples/witnesses.etf')).status===404);
 check('Compiled constructive witness model stays unavailable to the browser',(await fetch(base+'/evidence/witnesses/Witness.olean')).status===404);
 for(const path of ['/test/mixed_obligation_test.bl','/evidence/mixed-obligations/examples/summary.json','/evidence/mixed-obligations/execution/results.json','/evidence/mixed-obligations/execution/named-layout/instances/0002/Instance.lean','/evidence/mixed-obligations/execution/loop/instances/0002/Instance.lean','/evidence/mixed-obligations/fresh/obligations-fresh.json','/evidence/mixed-obligations/bridge-check.txt','/evidence/mixed-obligations/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared mixed obligation evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const mixedResults=await fetch(base+'/evidence/mixed-obligations/execution/results.json').then(response=>response.json());
 const bySubject=Object.fromEntries(mixedResults.map(row=>[row.id,row]));
 check('The mixed report separates feasibility from proof coverage',mixedResults.length===17&&bySubject.unknown.positive_feasibility==='satisfiable-in-contained-typed-term-model'&&!bySubject.unknown.coverage.complete&&bySubject.vacuous.coverage.complete&&bySubject.vacuous.initial_assumption_consistency==='inconsistent-in-contained-typed-term-model');
 check('Both engines supplied the same checked direct SAT packet',bySubject.sat.checked[0].packet===bySubject['sat-z3'].checked[0].packet&&bySubject.sat.coverage.witnesses===1&&bySubject['sat-z3'].coverage.witnesses===1&&!bySubject['sat-no-witness'].coverage.complete);
 check('Eleven witnessed entailments have an applied Lean theorem',mixedResults.flatMap(row=>row.checked_instances).length===11&&bySubject.loop.checked_instances.length===1&&bySubject.loop.checked_instances[0].label==='obligation/initial/normal'&&mixedResults.every(row=>row.model_theorem==='not-established-by-this-runner'&&row.compiler_proof_authority===false));
 check('Trusted mixed bundle archive stays unavailable to the browser',(await fetch(base+'/evidence/mixed-obligations/examples/archives/loop.etf')).status===404);
 check('Compiled mixed instance stays unavailable to the browser',(await fetch(base+'/evidence/mixed-obligations/execution/loop/instances/0002/Instance.olean')).status===404);
 for(const path of ['/CORE.md','/src/formal/core-terms.bl','/test/core_terms_test.bl','/metatheory/CoreTerms.lean','/metatheory/core-terms-pin.json','/evidence/core-terms/model-check.txt','/evidence/core-terms/examples/summary.json','/evidence/core-terms/execution/accepted.json','/evidence/core-terms/execution/rejected.json','/evidence/core-terms/execution/eager-default/Check.lean','/evidence/core-terms/execution/source-record-contract/Check.lean','/evidence/core-terms/fresh/core-terms-fresh.json','/evidence/core-terms/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared Core term evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const coreResults=await fetch(base+'/evidence/core-terms/execution/accepted.json').then(response=>response.json());
 check('The Core report has 34 all-input proofs and exact contract-question bindings',coreResults.length===34&&coreResults.filter(row=>row.subject.kind==='contract').length===4&&coreResults.every(row=>row.scope==='all-typed-inputs-of-this-contained-core-and-exact-symbolic-outcome'&&row.core_data_model_codec==='reviewed'&&row.compiler_proof_authority===false));
 const coreRejected=await fetch(base+'/evidence/core-terms/execution/rejected.json').then(response=>response.json());
 check('Six changed Core outcome packets were rejected',coreRejected.length===6&&coreRejected.every(row=>row.status==='not-accepted-by-Lean'));
 check('Trusted Core term archive stays unavailable to the browser',(await fetch(base+'/evidence/core-terms/examples/core-terms.etf')).status===404);
 check('Compiled Core term model stays unavailable to the browser',(await fetch(base+'/evidence/core-terms/CoreTerms.olean')).status===404);
 for(const path of ['/CORE-CONTRACTS.md','/src/formal/core-contracts.bl','/metatheory/CoreContract.lean','/evidence/core-contracts/execution/unused-slots/CoreContractCheck.lean','/evidence/core-contracts/execution/accepted.json','/evidence/core-contracts/execution/rejected.json','/evidence/core-contracts/fresh/core-contracts-fresh.json','/evidence/core-contracts/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared Core contract evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const contracts=await fetch(base+'/evidence/core-contracts/execution/accepted.json').then(response=>response.json());
 check('Eight composed Core contract proofs and six admission proofs',contracts.length===8&&contracts.filter(row=>row.axioms.originalCoreHasAdmittedOutcome).length===6&&contracts.every(row=>row.axioms.originalCoreSatisfiesContract&&row.compiler_proof_authority===false));
 check('The vacuous example has no admission proof',contracts.some(row=>row.id==='vacuous'&&row.admission==='witness-not-provided'&&!row.axioms.originalCoreHasAdmittedOutcome));
 check('The quotient example records its standard axiom policy',contracts.some(row=>row.id==='allowed-division'&&row.axiom_policy==='lean-standard'&&row.axioms.originalCoreSatisfiesContract.includes('Classical.choice')));
 const freshContracts=await fetch(base+'/evidence/core-contracts/fresh/core-contracts-fresh.json').then(response=>response.json());
 check('The transferred named-error contract rechecks with zero proof search or native sessions',freshContracts.rows.some(row=>row.id==='named-errors'&&row.status==='checked-data-connection')&&Object.values(freshContracts['checking-window']).every(count=>count===0));
 check('Trusted Core contract archive stays unavailable to the browser',(await fetch(base+'/evidence/core-contracts/examples/core-contracts.etf')).status===404);
 check('Compiled Core contract proof stays unavailable to the browser',(await fetch(base+'/evidence/core-contracts/execution/unused-slots/CoreContractCheck.olean')).status===404);
 for(const path of ['/TRANSLATION.md','/src/formal/core-translations.bl','/metatheory/CoreTranslation.lean','/evidence/core-translations/execution/optimizer-preserves-failure/CoreTranslationCheck.lean','/evidence/core-translations/execution/accepted.json','/evidence/core-translations/execution/rejected.json','/evidence/core-translations/fresh/core-translations-fresh.json','/evidence/core-translations/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared Core translation evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const translations=await fetch(base+'/evidence/core-translations/execution/accepted.json').then(response=>response.json());
 check('Nine exact Core translations check both error catalogues and both outcomes',translations.length===9&&translations.every(row=>row.axioms.beforeErrorsCovered&&row.axioms.afterErrorsCovered&&row.axioms.originalCoreOutcomesEqual&&Object.keys(row.imported_olean_sha256).length===3&&row.compiler_proof_authority===false));
 check('Signed quotient uses the explicitly recorded standard axiom policy',translations.some(row=>row.id==='signed-quotient'&&row.axioms.originalCoreOutcomesEqual.includes('Classical.choice'))&&translations.filter(row=>row.axiom_policy==='choice-free').length===8);
 const changedTranslations=await fetch(base+'/evidence/core-translations/execution/rejected.json').then(response=>response.json());
 check('A changed precondition and a different checked after tree fail composition',changedTranslations.length===2&&changedTranslations.every(row=>row.status==='not-accepted-by-Lean'));
 const freshTranslations=await fetch(base+'/evidence/core-translations/fresh/core-translations-fresh.json').then(response=>response.json());
 check('All original translations reconnect after transfer',freshTranslations.rows.length===9&&freshTranslations.rows.every(row=>row.status==='checked-data-connection'&&row['changed-precondition']==='rejected'));
 check('Trusted Core translation archive stays unavailable to the browser',(await fetch(base+'/evidence/core-translations/examples/core-translations.etf')).status===404);
 check('Compiled Core translation proof stays unavailable to the browser',(await fetch(base+'/evidence/core-translations/execution/optimizer-preserves-failure/CoreTranslationCheck.olean')).status===404);
 for(const path of ['/LOOPS.md','/src/formal/core-loops.bl','/metatheory/CoreLoop.lean','/metatheory/LoopTotal.lean','/evidence/core-loops/execution/countdown/CoreLoopCheck.lean','/evidence/core-loops/execution/accepted.json','/evidence/core-loops/execution/rejected.json','/evidence/core-loops/fresh/core-loops-fresh.json','/evidence/core-loops/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared Core loop evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const loops=await fetch(base+'/evidence/core-loops/execution/accepted.json').then(response=>response.json());
 check('Seven exact loop return theorems have no iteration bound',loops.length===7&&loops.every(row=>row.iteration_bound===null&&row.axioms.originalCoreLoopReturns.includes('Classical.choice')&&Object.keys(row.imported_olean_sha256).length===3&&row.compiler_proof_authority===false));
 const changedLoops=await fetch(base+'/evidence/core-loops/execution/rejected.json').then(response=>response.json());
 check('A changed rank and postcondition fail the exact loop question check',changedLoops.length===2&&changedLoops.every(row=>row.status==='not-accepted-by-Lean'));
 const freshLoops=await fetch(base+'/evidence/core-loops/fresh/core-loops-fresh.json').then(response=>response.json());
 check('All original loops reconnect after transfer',freshLoops.rows.length===7&&freshLoops.rows.every(row=>row.status==='checked-data-connection'&&row['changed-precondition']==='rejected'));
 check('Trusted Core loop archive stays unavailable to the browser',(await fetch(base+'/evidence/core-loops/examples/core-loops.etf')).status===404);
 check('Compiled Core loop proof stays unavailable to the browser',(await fetch(base+'/evidence/core-loops/execution/countdown/CoreLoopCheck.olean')).status===404);
 for(const path of ['/RECORD-HANDLERS.md','/src/formal/core-actors.bl','/metatheory/ActorTrace.lean','/evidence/core-actors/execution/bank/CoreActorCheck.lean','/evidence/core-actors/execution/bank/premises/ActorPremises.lean','/evidence/core-actors/execution/accepted.json','/evidence/core-actors/execution/rejected.json','/evidence/core-actors/fresh/core-actors-fresh.json','/evidence/core-actors/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared Core actor evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const actors=await fetch(base+'/evidence/core-actors/execution/accepted.json').then(response=>response.json());
 check('Six protocols and seven handlers have checked admitted traces with no trace bound',actors.length===6&&actors.reduce((count,row)=>count+row.handler_count,0)===7&&actors.every(row=>row.trace_bound===null&&row.axioms.originalHandlerTracesSafe&&row.axioms.failureRetainsState&&Object.keys(row.premise_packets).length===1+2*row.handler_count&&row.compiler_proof_authority===false));
 const changedActors=await fetch(base+'/evidence/core-actors/execution/rejected.json').then(response=>response.json());
 check('Widened admission and changed invariant fail the exact actor question check',changedActors.length===2&&changedActors.every(row=>row.status==='not-accepted-by-Lean'));
 const freshActors=await fetch(base+'/evidence/core-actors/fresh/core-actors-fresh.json').then(response=>response.json());
 check('Every original actor subject reconnects after transfer',freshActors.rows.length===6&&freshActors.rows.every(row=>row.status==='checked-data-connection'&&row['changed-initial']==='rejected'));
 check('Trusted Core actor archive stays unavailable to the browser',(await fetch(base+'/evidence/core-actors/examples/core-actors.etf')).status===404);
 check('Compiled Core actor proof stays unavailable to the browser',(await fetch(base+'/evidence/core-actors/execution/bank/CoreActorCheck.olean')).status===404);
 for(const path of ['/RUNTIME-OBSERVATIONS.md','/src/formal/core-observations.bl','/evidence/core-observations/execution/bank/CoreObservedTrace.lean','/evidence/core-observations/execution/bank-linked/CoreObservedTrace.lean','/evidence/core-observations/execution/accepted.json','/evidence/core-observations/execution/rejected.json','/evidence/core-observations/fresh/core-observations-fresh.json','/evidence/core-observations/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared recorded Core trace evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const observed=await fetch(base+'/evidence/core-observations/execution/accepted.json').then(response=>response.json());
 const byId=Object.fromEntries(observed.map(row=>[row.id,row]));
 check('Seven recorded runs and the linked bank theorem have exact Core witnesses',observed.length===8&&observed.every(row=>row.status==='checked-recorded-core-trace'&&row.checked_prefixes===row.events+1&&row.execution_authenticity==='observer-trusted')&&byId['full-idle'].checked_prefixes===65&&byId['bank-linked'].all_traces_safety_packet&&byId['bank-linked'].axioms['CoreObservedTrace.recordedSafe4']);
 check('Faithful traces retain two different forms of unsafe prefix',byId.failure.recorded_safety==='unsafe'&&byId.failure.first_failure_at===2&&byId['unsafe-return'].first_invariant_violation_at===1);
 const rejectedObservations=await fetch(base+'/evidence/core-observations/execution/rejected.json').then(response=>response.json());
 check('Seven resealed false step and invariant claims fail in Lean',rejectedObservations.length===7&&rejectedObservations.every(row=>row.status==='not-accepted-by-Lean'));
 const freshObservations=await fetch(base+'/evidence/core-observations/fresh/core-observations-fresh.json').then(response=>response.json());
 check('All receipts reconnect after transfer and reject a changed receipt identity',freshObservations.rows.length===7&&freshObservations.rows.every(row=>row.status==='checked-data-connection'&&row['changed-receipt']==='rejected'));
 check('Trusted observation archive stays unavailable to the browser',(await fetch(base+'/evidence/core-observations/examples/core-observations.etf')).status===404);
 check('Compiled observation proof stays unavailable to the browser',(await fetch(base+'/evidence/core-observations/execution/bank/CoreObservedTrace.olean')).status===404);
 for(const path of ['/src/formal/core-counterexamples.bl','/src/formal/core-counterexample-examples.bl','/evidence/core-counterexamples/execution/overdraft-oxiz/CoreCounterexampleCheck.lean','/evidence/core-counterexamples/execution/overdraft-oxiz/trace/CoreObservedTrace.lean','/evidence/core-counterexamples/execution/accepted.json','/evidence/core-counterexamples/execution/rejected.json','/evidence/core-counterexamples/fresh/core-counterexamples-fresh.json','/evidence/core-counterexamples/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared native Core counterexample evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 for(const path of ['/SDK-INTERFACE.md','/sdk-src/system/formal.bl','/sdk-src/oracle.bl','/sdk-src/formal/query.bl','/sdk-src/formal/logic.bl','/evidence/sdk-interface/focused-checks.txt','/evidence/sdk-interface/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared SDK interface source or evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const sdkQualification=await fetch(base+'/evidence/sdk-interface/qualification.json').then(response=>response.json());
 check('SDK qualification retains exact artifact public checks and theory coverage',sdkQualification.checkpoint===28&&sdkQualification.checks.focused_assertions===86&&sdkQualification.paired_questions===187&&sdkQualification.compiler_proof_authority===false);
 check('Original SDK qualification retains first failure and historical process scope',sdkQualification.candidate_1.assertions_failed===8&&sdkQualification.scope.includes('complete typed query effect in the calling process')&&sdkQualification.remaining.includes('automatic oracle handler inheritance across processes'));
 for(const path of ['/ANSWER-INTEGRITY.md','/sdk-src/formal/answer.bl','/sdk-src/formal/evaluate.bl','/src/formal/answer-examples.bl','/answers-check.bl','/evidence/answer-integrity/examples.json','/evidence/answer-integrity/baseline-checks.txt','/evidence/answer-integrity/focused-checks.txt','/evidence/answer-integrity/regression-checks.txt','/evidence/answer-integrity/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared answer source or evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const answers=await fetch(base+'/evidence/answer-integrity/qualification.json').then(response=>response.json());
 check('Typed answer qualification retains baseline exact SDK and passing regressions',answers.checkpoint===29&&answers.baseline.checks.failed===27&&answers.checks.focused_assertions===220&&answers.checks.regression_assertions===7086&&answers.unchanged_paired_questions===187&&answers.compiler_proof_authority===false);
 check('Ground equality availability remains explicit',JSON.stringify(answers.additional_native_verdicts)===JSON.stringify({z3:['proved','proved','proved'],oxiz:['unsupported','proved','proved']}));
 for(const path of ['/NATIVE-CONTEXTS.md','/sdk-src/formal/backend.bl','/src/formal/native-context-examples.bl','/native-contexts-check.bl','/evidence/native-contexts/examples.json','/evidence/native-contexts/baseline-checks.txt','/evidence/native-contexts/candidate-1-focused-checks.txt','/evidence/native-contexts/focused-checks.txt','/evidence/native-contexts/regression-checks.txt','/evidence/native-contexts/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared native context source or evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const ownerQualification=await fetch(base+'/evidence/native-contexts/qualification.json').then(response=>response.json());
 check('Native context qualification retains baseline candidate issue and passing exact SDK checks',ownerQualification.checkpoint===30&&ownerQualification.baseline.checks.failed===20&&ownerQualification.candidate_1.assertions_failed===3&&ownerQualification.checks.focused_assertions===356&&ownerQualification.checks.regression_assertions===7086&&ownerQualification.unchanged_paired_questions===187&&ownerQualification.compiler_proof_authority===false);
 const ownerExamples=await fetch(base+'/evidence/native-contexts/examples.json').then(response=>response.json());
 check('Both native examples retain truthful questions portable data and exact execution revisions',ownerExamples.rows.length===2&&ownerExamples.rows.every(row=>row.raw['portable-query']['solver-status']==='not-run'&&row.raw['after-reset']==='refuted'&&row.forgotten['question-is-portable']&&row.forgotten['retained-assumptions']===1&&row.restored['mirror-revision']===0&&row.restored['owner-revision']===1&&row.revision['rejected-exchange-native-checks']===0));
 const counterexamples=await fetch(base+'/evidence/core-counterexamples/execution/accepted.json').then(response=>response.json());
 check('Both engines have twelve composed original query and unsafe trace proofs',counterexamples.length===12&&counterexamples.every(row=>row.status==='checked-original-query-and-unsafe-core-run'&&row.checked_prefixes===row.events+1&&row.axioms['CoreCounterexampleCheck.originalCounterexampleRuns']&&!row.axioms['CoreCounterexampleCheck.originalCounterexampleRuns'].includes('Classical.choice')));
 check('Extra opaque observations retain explicit completion',counterexamples.some(row=>row.discovery.engine==='oxiz'&&row.extra_observation_bindings>0&&row.completion_origins['explicit-replay-completion']>0));
 const changedCounterexamples=await fetch(base+'/evidence/core-counterexamples/execution/rejected.json').then(response=>response.json());
 check('Individually valid mismatched query and trace proofs fail final composition',changedCounterexamples.length===3&&changedCounterexamples.every(row=>row.status==='not-accepted-by-Lean'&&row.query_witness==='checked'&&row.unsafe_trace==='checked'));
 const freshCounterexamples=await fetch(base+'/evidence/core-counterexamples/fresh/core-counterexamples-fresh.json').then(response=>response.json());
 check('All twelve original native discoveries reconnect after transfer',freshCounterexamples.rows.length===12&&freshCounterexamples.rows.every(row=>row.status==='checked-data-connection'&&row['changed-query']==='rejected'));
 check('Trusted native counterexample archive stays unavailable to the browser',(await fetch(base+'/evidence/core-counterexamples/examples/core-counterexamples.etf')).status===404);
 check('Compiled native counterexample proof stays unavailable to the browser',(await fetch(base+'/evidence/core-counterexamples/execution/overdraft-oxiz/CoreCounterexampleCheck.olean')).status===404);
 for(const path of ['/SPECIALIZATION.md','/src/formal/specialization.bl','/test/specialization_test.bl','/specialization-check.bl','/specialization-recheck.bl','/evidence/specialization/examples/specialization.json','/evidence/specialization/fresh/specialization-fresh.json','/evidence/specialization/checks.txt','/evidence/specialization/qualification.json','/evidence/specialization/model-qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared specialization evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/ELABORATION.md','/src/formal/elaboration.bl','/test/elaboration_test.bl','/elaboration-check.bl','/elaboration-recheck.bl','/evidence/elaboration/examples/elaboration.json','/evidence/elaboration/fresh/elaboration-fresh.json','/evidence/elaboration/checks.txt','/evidence/elaboration/qualification.json','/evidence/elaboration/model-qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared elaboration evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/HYGIENE.md','/sdk-src/formal/anf-inputs.bl','/test/hygiene_test.bl','/hygiene-check.bl','/evidence/hygiene/baseline/probe.json','/evidence/hygiene/repaired/hygiene.json','/evidence/hygiene/checks.txt','/evidence/hygiene/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared hygiene evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/EFFECTS.md','/sdk-src/effect.bl','/src/formal/effect-examples.bl','/evidence/effects/examples.json','/evidence/effects/focused-checks.txt','/evidence/effects/runtime-checks.txt','/evidence/effects/capacity-checks.txt','/evidence/effects/regression-checks.txt','/evidence/effects/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared handler evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/PACKAGED-WORKER.md','/packaged-worker-check.bl','/evidence/packaged-worker/examples.json','/evidence/packaged-worker/portable-examples.json','/evidence/packaged-worker/native-artifact.json','/evidence/packaged-worker/portable-runtime-artifact.json','/evidence/packaged-worker/portable-observation-note.json','/evidence/packaged-worker/focused-checks.txt','/evidence/packaged-worker/regression-checks.txt','/evidence/packaged-worker/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared packaged worker evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/SESSION-LIFETIME.md','/evidence/session-lifetime/baseline-checks.txt','/evidence/session-lifetime/focused-checks.txt','/evidence/session-lifetime/regression-checks.txt','/evidence/session-lifetime/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared session lifetime evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/TEMPORAL.md','/sdk-src/formal/temporal.bl','/temporal-check.bl','/temporal-laws-export.bl','/sdk-examples/datom/time/07-uncertain.bl','/sdk-examples/datom/time/08-chronolog.bl','/evidence/temporal/examples.json','/evidence/temporal/focused-temporal-checks.txt','/evidence/temporal/law-execution/intersection-symmetry/Check.lean','/evidence/temporal/law-execution/shift-preserves-duration/Check.lean','/evidence/temporal/law-execution/empty-spans-same-points/Check.lean','/evidence/temporal/law-execution/accepted.json','/evidence/temporal/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared temporal source or evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/VERITAS-TERMS.md','/CALLABLE-CUSTODY.md','/sdk-src/formal/runtime-values.bl','/sdk-src/formal/coverage.bl','/sdk-src/veritas/ledger.bl','/veritas-terms-check.bl','/veritas-ledger-check.bl','/evidence/veritas-terms/examples.json','/evidence/veritas-terms/focused-current-checks.txt','/evidence/veritas-terms/qualification.json']){
  const r=await fetch(base+path);const body=await r.text();
  check('Declared Veritas interface or evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/RESPONSE-CONTRACTS.md','/response-contracts-check.bl','/response-contracts-ledger.bl','/sdk-src/formal/response.bl','/sdk-src/formal/response-runtime.bl','/sdk-src/formal/ground.bl','/sdk-src/formal/integer-optimize.bl','/sdk-src/veritas/mock.bl','/sdk-src/veritas/fault.bl','/evidence/response-contracts/examples.json','/evidence/response-contracts/ledger-read.json','/evidence/response-contracts/focused-current-checks.txt','/evidence/response-contracts/regression-current-checks.txt','/evidence/response-contracts/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared response interface or evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/ANSWER-BINDING.md','/answer-binding-check.bl','/sdk-src/formal/logic.bl','/sdk-src/veritas/ledger.bl','/evidence/answer-binding/baseline-checks.txt','/evidence/answer-binding/candidate-1/ledger-write-checks.txt','/evidence/answer-binding/examples.json','/evidence/answer-binding/ledger-read.json','/evidence/answer-binding/focused-checks.txt','/evidence/answer-binding/regression-checks.txt','/evidence/answer-binding/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared answer-binding interface or evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/COMPILER-LINEARITY.md','/PREPARATION.md','/compiler-linearity-probe.bl','/compiler-linearity-normalization-probe.bl','/evidence/compiler-linearity/proof-probe.json','/evidence/compiler-linearity/normalization-probe.json','/evidence/compiler-linearity/baseline-checks.txt']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared preparation design or probe is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/sdk-src/formal/affine.bl','/sdk-src/formal/preparation.bl','/sdk-src/formal/certificate.bl','/sdk-src/system/linear.bl','/query-preparation-check.bl','/query-preparation-ledger.bl','/evidence/query-preparation/examples.json','/evidence/query-preparation/ledger-read.json','/evidence/query-preparation/focused-checks.txt','/evidence/query-preparation/preceding-focused-checks.txt','/evidence/query-preparation/regression-checks.txt','/evidence/query-preparation/verdict-baseline-checks.txt','/evidence/query-preparation/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared query preparation source or evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/SOURCE-PROPERTIES.md','/sdk-src/formal/source.bl','/sdk-src/formal/anf-function.bl','/sdk-src/formal/source-runtime.bl','/sdk-src/veritas/property.bl','/source-properties-check.bl','/evidence/source-properties/examples.json','/evidence/source-properties/focused-checks.txt','/evidence/source-properties/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared source-property interface or evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 check('Trusted temporal law archive stays unavailable to the browser',(await fetch(base+'/evidence/temporal/laws.etf')).status===404);
 check('Compiled temporal theorem stays unavailable to the browser',(await fetch(base+'/evidence/temporal/law-execution/intersection-symmetry/Check.olean')).status===404);
}catch(error){report.fatal={message:error.message,stack:error.stack};check('Audit completed',false,{error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();
 report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(c=>c.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,failed:report.checks.filter(c=>!c.passed),screenshots:report.screenshots.length}));
 if(!report.passed)process.exitCode=1;
}
