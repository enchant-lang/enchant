"""Aggregate completed scalar readers: fifteen common plus one text refusal."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/obligation-integration';D=E/'previous-scalar-readers';B=P/'evidence/scalar-integration'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pin,producer=read(E/'sdk-candidate.json'),read(E/'baseline-sdk-pin.json')
assert read(P/'sdk-pin.json')==producer
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
assert read(B/'records-qualification.json')['sdk_pin']==producer
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();relative=str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git','show',commit+':'+relative],cwd=R)==Path(__file__).read_bytes()
results=[];executions=[]
recipe='research/formal-logic/run-obligation-previous-scalar-readers.py'
for stage in ['one','two','controls']:
 source=read(D/(stage+'-source-pin.json'));exit=read(D/(stage+'-exit.json'));result=read(D/(stage+'.json'))
 assert source['sdk_pin']==pin and source['recorded_producer_sdk_pin']==producer
 assert exit['exit_code']==0 and exit['runtime_retired'] and exit['consumer_cwd_retired']
 for name,digest in source['source_sha256'].items():
  historical=subprocess.check_output(['git','show',source['code_commit']+':'+name],cwd=R)
  assert hashlib.sha256(historical).hexdigest()==digest,name
  # A reporting-only orchestration fix does not rewrite the actual executed
  # driver. Preserve its old commit/hash; all logical inputs remain exact.
  if name!=recipe:assert sha(R/name)==digest,name
 assert result['sdk']==pin['sdk'] and result['recorded-producer-sdk']==producer['sdk']
 assert result['sdk-only'] and result['research-import-path'] is False and result['source-payload-execution'] is False
 assert result['solver-exchanges']==result['oracle-calls']==0
 assert result['checked-native-execution'] is False and result['compiler-proof-authority'] is False
 command=read(D/(stage+'-command.json'));assert pin['sdk']+'/bin/bl' in command and '--cold' in command and '-p' not in command
 for flag in ['--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=1200','--property=KillMode=control-group']:assert flag in command
 assert (D/(stage+'-command.json')).stat().st_mtime_ns<=(D/(stage+'.json')).stat().st_mtime_ns<=(D/(stage+'-exit.json')).stat().st_mtime_ns
 executions.append({'stage':stage,'source_pin':source,'exit':exit,'command_sha256':sha(D/(stage+'-command.json')),
  'log_sha256':sha(D/(stage+'-checks.txt')),'result_sha256':sha(D/(stage+'.json'))})
 results.append(result)
one,two,controls=results
assert one['process']!=two['process'] and one['cwd']!=two['cwd']
assert one['rows']==two['rows']==read(B/'reader-one.json')['rows'] and len(one['rows'])==20
assert one['ledger'] is None and two['ledger'] is None
expected={'record-request-reference','record-subject-reference','claimed-trust','claimed-compiler-authority','changed-context-state',
 'changed-retained-assumptions','changed-recorded-backend','changed-adapter-with-recomputed-references','claimed-local-owner',
 'changed-caller-origin','claimed-checked-certificate','floating-answer-version','unknown-checking-policy','numeric-policy-downgrade','extra-record-field'}
assert len(controls['controls'])==15 and {row['id'] for row in controls['controls']}==expected
assert all(row['status']=='refused' for row in controls['controls'])
extra=controls['scalar-controls'];assert extra['word-only-downgrade']=='refused'
assert len(extra['invalid-text-points'])==3 and all(row['verdict']=='invalid-point' for row in extra['invalid-text-points'])
assert controls['rehashed-invalid-coordinate']=='independently-invalid' and controls['edited-history']=='recorded-only'
report={'schema':'bl.obligation-sdk-previous-scalar-readers.v1','status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'sdk_pin':pin,'recorded_producer_sdk_pin':producer,'records':20,'fresh_sdk_only_readers':2,
 'refusal_controls':16,'common_refusal_controls':15,'text_policy_refusal_controls':1,'independently_invalid_text_controls':3,
 'solver_exchanges':0,'oracle_calls':0,'executions':executions,'reporter':{'code_commit':commit,'path':relative,'sha256':sha(Path(__file__))},
 'artifact_sha256':{f.name:sha(f) for f in D.iterdir() if f.is_file()},'checked_native_execution':False,'compiler_proof_authority':False,
 'scope':'Two actual fresh SDK-only readers of twenty prior scalar/word packets plus sixteen refusals and three independently invalid text points. This reporter repairs only the final count aggregation; exact executed driver commits, logical inputs, exits and outputs are retained. Retired durable stores were not recreated or reopened; producer labels authenticate no native execution.'}
(E/'previous-scalar-readers-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'passed','records':20,'fresh_readers':2,'refusal_controls':16,'invalid_text_controls':3,'replayed_checks_reused':True}))
