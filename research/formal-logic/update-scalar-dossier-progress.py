"""Publish measured progress prose without altering any executable/result span."""
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-presentation';C=P/'evidence/scalar-integration'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
phase=sys.argv[1] if len(sys.argv)>1 else 'native'
assert phase in ['native','records']
plan_path=P/'proposals/scalar-dossier-plan.json';plan=read(plan_path)
assert plan['status']=='proposal-awaiting-complete-sdk-qualification-and-selection'
assert read(P/'sdk-pin.json')==read(C/'baseline-sdk-pin.json')
for stage in ['focused','word-focused','legacy','regression']:
 result=read(C/(stage+'-exit.json'));assert result['exit_code']==0 and result['complete_green_test_summary'] is True
assert read(C/'native-comparison.json')['questions']==187 and read(C/'native-comparison.json')['differences']==[]
assert read(C/'text-packets.json')['checks']==52 and read(C/'text-packets.json')['status']=='passed'
assert read(C/'evidence-packets.json')['fresh-checks']==6 and read(C/'evidence-packets.json')['status']=='passed'
doc=P/'ATLAS.bl.org';assert sha(doc)==plan['baseline_document_sha256']
before=doc.read_text()
title='Qualified prototypes; runtime integration in progress' if phase=='native' else 'The runtime candidate has passed its native audit'
pattern=r'^#\+begin_note :title "'+re.escape(title)+r'"\n.*?^#\+end_note\n'
assert len(re.findall(pattern,before,re.M|re.S))==1
note='''#+begin_note :title "The runtime candidate has passed its native audit"
The candidate SDK is built and has passed 11,705 assertions. All 187 paired Z3/OxiZ questions retain their preceding results and solver binaries. Fresh SDK-only readers have reopened twelve older word packets, four text packets and two certificate bundles; the text gate passed 52 checks and the bundle gate ran six fresh finite checks, with no solver or oracle calls.

Twenty new word/text records and an actual durable ledger are now being captured. Two fresh durable readers and older-generation compatibility checks still have to pass before selection. The executable examples and saved comparison on this page retain the qualified word SDK checkpoint; the new runtime is not selected yet.

Read [[file:evidence/scalar-integration/native-comparison.json][the actual paired audit]], [[file:evidence/scalar-integration/text-packets.json][the cold text controls]], [[file:evidence/scalar-integration/evidence-packets.json][the cold proof checks]] and [[file:VACUITY-SEMANTICS-REVIEW.md][the semantic review of conditional proof and premise feasibility]]. The pending [[file:FINITE-FEASIBILITY-PROTOTYPE.md][feasibility]] and [[file:FINITE-OBLIGATION-PROTOTYPE.md][policy composition]] experiments have not run.
#+end_note
'''
if phase=='records':
 records=read(C/'records-qualification.json')
 assert records['status']=='passed' and records['records']==20 and records['fresh_sdk_only_readers']==2
 assert records['refusal_controls']==16 and records['independently_invalid_text_controls']==3
 assert records['normalizer_calls_per_selected_lookup']==1 and records['solver_exchanges']==records['oracle_calls']==0
 assert read(C/'corpus-ledger-retirement.json')['retired'] is True
 note='''#+begin_note :title "The runtime candidate has passed its durable readers"
The candidate SDK has passed 11,705 assertions and its full 187-question paired native audit. Two fresh SDK-only processes have now reopened all twenty actual word/text packets and durable ledger rows with zero solver or oracle calls. Selected lookups normalized one payload exactly once; warmed replay introduced no further atoms. Sixteen refusal controls and three independently invalid text-point controls passed. The owned ledger was hashed and retired after these checks.

Three older saved generations are now being replayed with their original producer identities. Those compatibility gates still have to pass before SDK selection. The executable examples and saved comparison on this page retain the qualified word SDK checkpoint; its recorded results have not been rewritten as candidate results.

Read [[file:evidence/scalar-integration/records-qualification.json][the actual durable-reader qualification]], [[file:evidence/scalar-integration/text-packets.json][the cold text controls]], [[file:evidence/scalar-integration/evidence-packets.json][the cold proof checks]], [[file:VACUITY-SEMANTICS-REVIEW.md][the vacuity semantic review]] and [[file:STRING-REPRESENTATION-REVIEW.md][the exact native String carrier review]]. The pending [[file:FINITE-FEASIBILITY-PROTOTYPE.md][feasibility]], [[file:FINITE-OBLIGATION-PROTOTYPE.md][policy composition]] and [[file:GRAPH-INTEGER-PROTOTYPE.md][graph integer checker]] experiments have not run.
#+end_note
'''
after=re.sub(pattern,lambda _:note,before,count=1,flags=re.M|re.S)
for p in [r'^#\+begin_src beam-lisp\b[^\n]*\n.*?^#\+end_src[^\n]*',r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*',r'^#\+name:[^\n]*\n(?:\|[^\n]*(?:\n|$))*']:
 assert re.findall(p,before,re.M|re.S)==re.findall(p,after,re.M|re.S)
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();name=str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==Path(__file__).read_bytes()
prior=sha(doc);doc.write_text(after);plan['baseline_document_sha256']=sha(doc)
plan['progress_document_sha256']=sha(doc);plan_path.write_text(json.dumps(plan,indent=2)+'\n')
report={'status':'progress-prose-updated-awaiting-next-full-presentation-checkpoint','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'phase':phase,
 'document_before_sha256':prior,'document_sha256':sha(doc),'cell_count':91,'executable_cells_unchanged':True,'saved_results_unchanged':True,
 'results_authored':False,'selected_sdk_pin':read(P/'sdk-pin.json'),'candidate_sdk_pin':read(C/'sdk-candidate.json'),
 'native_comparison_sha256':sha(C/'native-comparison.json'),'text_packets_sha256':sha(C/'text-packets.json'),
 'evidence_packets_sha256':sha(C/'evidence-packets.json'),'candidate_runtime_selected':False,
 'recipe':{'code_commit':commit,'path':name,'sha256':sha(Path(__file__))}}
if phase=='records':report['records_qualification_sha256']=sha(C/'records-qualification.json')
(E/('progress-source-application.json' if phase=='native' else 'records-progress-source-application.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cells_unchanged':91,'results_authored':False}))
