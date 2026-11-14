"""Apply committed explanatory sources after SDK selection, leaving results to BL."""
from datetime import datetime, timezone
import hashlib,json,re,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-presentation';C=P/'evidence/scalar-integration'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pin=read(P/'sdk-pin.json');plan=read(P/'proposals/scalar-dossier-plan.json')
assert read(C/'qualification.json')['status']=='passed' and read(C/'qualification.json')['sdk_pin']==pin
assert read(C/'promotion.json')['selected']==pin==plan['candidate_sdk_pin']
assert plan['status']=='proposal-awaiting-complete-sdk-qualification-and-selection'
doc=P/'ATLAS.bl.org';assert sha(doc)==plan['baseline_document_sha256']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
inputs=[Path(__file__),doc,P/'proposals/scalar-dossier-plan.json',*[P/'proposals'/n for n in plan['source_proposals']]]
digests={}
for p in inputs:
 n=str(p.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==p.read_bytes();digests[n]=sha(p)
before=doc.read_text();assert len(re.findall(r'^#\+begin_src beam-lisp\b',before,re.M))==91
section=(P/'proposals/scalar-dossier-section.org').read_text();assert '#+RESULTS' not in section
pattern=r'^\*\* Small proofs and careful text interfaces\n.*?(?=^\*\* Keep every assumption with the question\n)'
assert len(re.findall(pattern,before,re.M|re.S))==1
after=re.sub(pattern,lambda _:section.rstrip()+'\n\n',before,count=1,flags=re.M|re.S)
anchor='           [formal.effect-examples :as effect-examples]))'
assert after.count(anchor)==1
after=after.replace(anchor,'           [formal.finite-word-certificate :as finite-word] [formal.request-evidence :as request-evidence]\n           [formal.scalar-text :as scalar-text] [formal.data :as formal-data]\n'+anchor)
blocks=[]
for name in plan['new_cells']:
 cell=(P/'proposals'/('scalar-dossier-word-cell.bl' if name=='story-word-evidence' else 'scalar-dossier-text-cell.bl')).read_text()
 assert '#+RESULTS' not in cell and ':id '+name not in before
 blocks.append('#+begin_src beam-lisp :id '+name+'\n'+cell.rstrip()+'\n#+end_src\n\n')
anchor='#+begin_src beam-lisp :id story-word-request\n';assert after.count(anchor)==1
after=after.replace(anchor,''.join(blocks)+anchor)
# The older byte example keeps its word-only semantics, with the current mixed
# durable-record cohort labelled accurately. No historical result is retagged.
after=after.replace('receipt (json/decode (File/read! "research/formal-logic/evidence/word-integration/records-qualification.json"))',
                    'receipt (json/decode (File/read! "research/formal-logic/evidence/scalar-integration/records-qualification.json"))')
after=after.replace(':saved-word-records (get receipt "records")',':saved-word-text-records (get receipt "records")')
results=r'^#\+RESULTS:[^\n]*\n(?::[^\n]*(?:\n|$))*'
assert re.findall(results,before,re.M)==re.findall(results,after,re.M)
assert len(re.findall(r'^#\+begin_src beam-lisp\b',after,re.M))==93
doc.write_text(after)
producer=P/'dossier/formal/research-evidence.bl';producer_before=sha(producer)
producer.write_bytes((P/'proposals/scalar-research-evidence.bl').read_bytes())
report={'schema':'bl.scalar-dossier-source-application.v1','status':'source-applied-awaiting-real-writer',
 'recorded_utc':datetime.now(timezone.utc).isoformat(),'sdk_pin':pin,'code_commit':commit,'input_source_sha256':digests,
 'document_before_sha256':plan['baseline_document_sha256'],'document_after_sha256':sha(doc),'cells':93,'new_cells':plan['new_cells'],
 'producer_before_sha256':producer_before,'producer_after_sha256':sha(producer),'results_authored':False,
 'existing_result_spans_preserved':True,'dossier_qualified':False,'compiler_proof_authority':False}
(E/'dossier-source-application.json').write_text(json.dumps(report,indent=2)+'\n')
plan.update(status=report['status'],live_document_modified=True,application_receipt='../evidence/scalar-presentation/dossier-source-application.json')
(P/'proposals/scalar-dossier-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cells':93,'results_authored':False}))
