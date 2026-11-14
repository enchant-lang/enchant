"""Select only the exact qualified obligation SDK; never rebuild during selection."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/obligation-integration'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pin,baseline=read(E/'sdk-candidate.json'),read(E/'baseline-sdk-pin.json')
assert read(P/'sdk-pin.json')==baseline
q=read(E/'qualification.json')
assert q['status']=='passed' and q['sdk_pin']==pin and q['baseline_sdk_pin']==baseline and q['project_pin_selected'] is False
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
assert q['native_questions']==187 and q['native_outcome_differences']==[]
assert q['fresh_obligation_readers']==2 and q['obligation_packets']==4 and q['old_v1_evidence_packets']==2
assert sha(E/'build-linkage.json')==q['build_linkage_sha256']
assert sha(E/'previous-scalar-readers-qualification.json')==q['previous_scalar_readers_qualification_sha256']
for name,digest in read(E/'build-linkage.json')['source_sha256'].items():assert sha(R/name)==digest
for stage,result in q['stages'].items():
 for name,digest in result['source_pin']['source_sha256'].items():assert sha(R/name)==digest
 assert sha(E/(stage+'-checks.txt'))==result['log_sha256']
 assert sha(E/(stage+'-command.json'))==result['command_sha256']
assert subprocess.check_output([R/'scripts/prepare-checkout-sdk','--fingerprint'],text=True).strip()==pin['engine_fingerprint']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();relative=str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+relative],cwd=R)==Path(__file__).read_bytes()
assert not (E/'promotion.json').exists()
(E/'selection-previous-sdk-pin.json').write_bytes((P/'sdk-pin.json').read_bytes())
(P/'sdk-pin.json').write_text(json.dumps(pin,indent=2)+'\n')
(E/'promotion.json').write_text(json.dumps({'schema':'bl.obligation-sdk-promotion.v1','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'before':baseline,'selected':pin,'qualification_sha256':sha(E/'qualification.json'),
 'recipe':{'code_commit':commit,'path':relative,'sha256':sha(Path(__file__))},
 'goal_complete':False,'dossier_refresh_pending':True,'compiler_proof_authority':False,
 'scope':'Qualified project SDK selection. The existing live dossier and its immutable scalar source projection remain a historical checkpoint until the separate writer/check/browser activation.'},indent=2)+'\n')
print(json.dumps({'status':'selected','sdk':pin['sdk'],'goal_complete':False,'dossier_refresh_pending':True}))
