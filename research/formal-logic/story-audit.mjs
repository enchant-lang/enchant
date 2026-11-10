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
const report={schema:'enchant.formal.guided-review-audit.v1',base,started:new Date().toISOString(),checks:[],screenshots:[],scope:'Live presentation, recorded data, source-backed views and kit interactions. No production semantic change.'};
async function shot(name){await call({op:'screenshot',path:join(output,name+'.png')});report.screenshots.push(name+'.png');}
try{
 await call({op:'open',width:1440,height:1000,mobile:false});
 for(const size of [{name:'phone',width:390,height:844,mobile:true},{name:'desktop',width:1440,height:1000,mobile:false}]){
  await call({op:'viewport',...size});await navigate('/#s-the-big-idea');await wait("!!document.querySelector('#s-the-big-idea')");
  const top=await evaluate("({title:document.title,w:document.documentElement.clientWidth,sw:document.documentElement.scrollWidth,failed:document.querySelectorAll('.cell.failed,.ms-errors,.review-errors,.cl-errors,.lt-errors').length})");
  check(size.name+': readable page width',top.sw<=top.w+2,top);check(size.name+': no failed cells or declarations',top.failed===0,top);
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
  check(size.name+': contract chapter explains the return promise and one admitted input',await evaluate("document.body.innerText.includes('A must-return policy rules out the raised case')&&document.body.innerText.includes('x = 4')"));
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
  check(size.name+': contract cell records its input and exact policy replay',composed.includes(':admitted-x 4')&&composed.includes(':declared-inputs 4')&&composed.includes(':witness-inputs 2')&&composed.includes(':must-return true')&&composed.includes(':changed-policy :rejected')&&composed.includes(':kernel-execution :not-run'));
  await evaluate("document.querySelector('#cell-story-core-contract-composition').scrollIntoView({block:'center'})");
  await shot(size.name+'-core-contract-data');
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
 for(const path of ['/metatheory/Core.lean','/evidence/metatheory/qualification.json','/evidence/contracts/qualification.json','/src/formal/certificate.bl','/LOOPS.md','/evidence/loops/examples.json','/evidence/loops/qualification.json','/evidence/loops/model-qualification.json','/TRANSLATION.md','/src/formal/translation.bl','/src/formal/optimize.bl','/src/formal/result.bl','/src/formal/api.bl','/evidence/translation/qualification.json','/evidence/translation/examples.json','/PROTOCOLS.md','/src/formal/protocol.bl','/src/formal/protocol-run.bl','/evidence/protocol/model-qualification.json','/evidence/protocol/examples.json','/evidence/protocol/qualification.json','/BOUNDED-TRACES.md','/src/formal/protocol-trace.bl','/evidence/protocol-traces/examples.json','/evidence/protocol-traces/qualification.json','/evidence/protocol-traces/model-qualification.json']){
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
 for(const path of ['/INTRINSICS.md','/src/formal/intrinsics.bl','/src/formal/elaborate.bl','/test/intrinsics_test.bl','/evidence/intrinsics/intrinsics-probe.json','/evidence/intrinsics/checks.txt','/evidence/intrinsics/fresh-replay.json','/evidence/intrinsics/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared callee-identity evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/CONTEXTS.md','/DATA-IDENTITY.md','/src/formal/context.bl','/src/formal/identity.bl','/src/formal/contract.bl','/test/context_test.bl','/test/identity_test.bl','/context-check.bl','/evidence/contexts/probe.json','/evidence/contexts/checks.txt','/evidence/contexts/examples.json','/evidence/contexts/fresh-replay.json','/evidence/contexts/qualification.json','/evidence/contexts/canonical-fixtures.json','/evidence/contexts/original-byte-reproduction.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared binding/identity evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/SELECTED-SOURCE.md','/src/formal/selected.bl','/src/formal/source.bl','/test/selected_test.bl','/test/source_test.bl','/evidence/source-selection/checks.txt','/evidence/source-selection/selected-third-check.txt','/evidence/source-selection/examples/selected-examples.json','/evidence/source-selection/fresh/selected-fresh-replay.json','/evidence/source-selection/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared selected Source evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 check('Trusted selected Source ETF archive stays unavailable to the browser',(await fetch(base+'/evidence/source-selection/examples/selected-examples.etf')).status===404);
 for(const path of ['/SELECTED-RUNTIME.md','/src/formal/selected-artifact.bl','/src/formal/selected-runtime.bl','/test/selected_runtime_test.bl','/selected-runtime-recheck.bl','/evidence/selected-runtime/examples/original-selected.json','/evidence/selected-runtime/fresh/original-selected-fresh.json','/evidence/selected-runtime/checks.txt','/evidence/selected-runtime/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared original selected runtime evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 check('Trusted original selected runtime ETF archive stays unavailable to the browser',(await fetch(base+'/evidence/selected-runtime/examples/original-selected.etf')).status===404);
 for(const path of ['/CONNECTIONS.md','/src/formal/connection.bl','/test/connection_test.bl','/connections-check.bl','/connections-recheck.bl','/evidence/connections/examples/connections.json','/evidence/connections/fresh/connections-fresh.json','/evidence/connections/checks.txt','/evidence/connections/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared connection evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/REFUTATION-KERNEL.md','/src/formal/refutation.bl','/test/refutation_test.bl','/refutation-check.bl','/refutation-recheck.bl','/metatheory/Refutation.lean','/metatheory/refutation-pin.json','/evidence/refutation-kernel/model-check-3.txt','/evidence/refutation-kernel/bridge-check.txt','/evidence/refutation-kernel/execution/accepted.json','/evidence/refutation-kernel/execution/rejected.json','/evidence/refutation-kernel/examples/weighted.json','/evidence/refutation-kernel/execution/weighted/Check.lean','/evidence/refutation-kernel/execution/weighted/result.json','/evidence/refutation-kernel/fresh/refutation-fresh.json','/evidence/refutation-kernel/checks.txt','/evidence/refutation-kernel/qualification.json']){
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
 for(const path of ['/WITNESSES.md','/src/formal/query.bl','/src/formal/witness.bl','/src/formal/witness-examples.bl','/test/query_test.bl','/test/witness_test.bl','/witness-check.bl','/witness-recheck.bl','/metatheory/Witness.lean','/metatheory/witness-pin.json','/evidence/witnesses/model-check.txt','/evidence/witnesses/examples/summary.json','/evidence/witnesses/examples/nonlinear.json','/evidence/witnesses/execution/accepted.json','/evidence/witnesses/execution/rejected.json','/evidence/witnesses/execution/nonlinear/Check.lean','/evidence/witnesses/execution/nonlinear/result.json','/evidence/witnesses/bridge-check.txt','/evidence/witnesses/fresh/witnesses-fresh.json','/evidence/witnesses/checks.txt','/evidence/witnesses/qualification.json']){
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
 for(const path of ['/CORE-CONTRACTS.md','/src/formal/core-contracts.bl','/metatheory/CoreContract.lean','/evidence/core-contracts/execution/unused-slots/CoreContractCheck.lean','/evidence/core-contracts/execution/accepted.json','/evidence/core-contracts/execution/rejected.json','/evidence/core-contracts/qualification.json']){
  const response=await fetch(base+path),body=await response.text();
  check('Declared Core contract evidence is readable: '+path,response.status===200&&body.length>50&&(/text\/plain|application\/json/).test(response.headers.get('content-type')));
 }
 const contracts=await fetch(base+'/evidence/core-contracts/execution/accepted.json').then(response=>response.json());
 check('Eight composed Core contract proofs and six admission proofs',contracts.length===8&&contracts.filter(row=>row.axioms.originalCoreHasAdmittedOutcome).length===6&&contracts.every(row=>row.axioms.originalCoreSatisfiesContract&&row.compiler_proof_authority===false));
 check('The vacuous example has no admission proof',contracts.some(row=>row.id==='vacuous'&&row.admission==='witness-not-provided'&&!row.axioms.originalCoreHasAdmittedOutcome));
 check('The quotient example records its standard axiom policy',contracts.some(row=>row.id==='allowed-division'&&row.axiom_policy==='lean-standard'&&row.axioms.originalCoreSatisfiesContract.includes('Classical.choice')));
 check('Trusted Core contract archive stays unavailable to the browser',(await fetch(base+'/evidence/core-contracts/examples/core-contracts.etf')).status===404);
 check('Compiled Core contract proof stays unavailable to the browser',(await fetch(base+'/evidence/core-contracts/execution/unused-slots/CoreContractCheck.olean')).status===404);
 for(const path of ['/SPECIALIZATION.md','/src/formal/specialization.bl','/test/specialization_test.bl','/specialization-check.bl','/specialization-recheck.bl','/evidence/specialization/examples/specialization.json','/evidence/specialization/fresh/specialization-fresh.json','/evidence/specialization/checks.txt','/evidence/specialization/qualification.json','/evidence/specialization/model-qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared specialization evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/ELABORATION.md','/src/formal/elaboration.bl','/test/elaboration_test.bl','/elaboration-check.bl','/elaboration-recheck.bl','/evidence/elaboration/examples/elaboration.json','/evidence/elaboration/fresh/elaboration-fresh.json','/evidence/elaboration/checks.txt','/evidence/elaboration/qualification.json','/evidence/elaboration/model-qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared elaboration evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
 for(const path of ['/HYGIENE.md','/src/formal/anf-inputs.bl','/test/hygiene_test.bl','/hygiene-check.bl','/evidence/hygiene/baseline/probe.json','/evidence/hygiene/repaired/hygiene.json','/evidence/hygiene/checks.txt','/evidence/hygiene/qualification.json']){
  const r=await fetch(base+path),body=await r.text();
  check('Declared hygiene evidence is readable: '+path,r.status===200&&body.length>50&&(/text\/plain|application\/json/).test(r.headers.get('content-type')));
 }
}catch(error){report.fatal={message:error.message,stack:error.stack};check('Audit completed',false,{error:error.message});}
finally{
 await call({op:'stop'}).catch(()=>{});helper.stdin.end();
 report.finished=new Date().toISOString();report.passed=!report.fatal&&report.checks.every(c=>c.passed);
 await writeFile(join(output,'audit.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,failed:report.checks.filter(c=>!c.passed),screenshots:report.screenshots.length}));
 if(!report.passed)process.exitCode=1;
}
