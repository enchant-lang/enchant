"""Qualify one fixed policy-aware SDK; retain inherited versus newly replayed scope."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/obligation-integration'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin,baseline=read(E/'sdk-candidate.json'),read(E/'baseline-sdk-pin.json')
assert read(P/'sdk-pin.json')==baseline
parent=read(P/'evidence/scalar-integration/qualification.json')
assert parent['status']=='passed' and parent['sdk_pin']==baseline
sdk=Path(pin['sdk']);metadata=read(sdk/'artifact.json');old=read(Path(baseline['sdk'])/'artifact.json')
assert sha(sdk/'artifact.json')==pin['descriptor_sha256']
linkage=read(E/'build-linkage.json');assert linkage['status']=='bound' and linkage['sdk_pin']==pin
assert len(linkage['source_sha256'])==731 and len(linkage['source_changes'])==13
for name,digest in linkage['source_sha256'].items():
 assert sha(R/name)==sha(Path(pin['source'])/name)==sha(Path(metadata['source'])/name)==sha(sdk/'lib/beam_lisp-0.1.0'/name)==digest,name
for name in ('platform','formalWorker'):assert metadata[name]==old[name]
floor=read(P/'evidence/numeric-semantics/compiler-floor-install.json');assert len(floor['after'])==141
for name,digest in floor['after'].items():
 assert sha(R/'priv/bootstrap/seed'/name)==sha(Path(metadata['compiler'])/'seed'/name)==sha(sdk/'image/priv/bootstrap/seed'/name)==digest
inherited=['priv/boot/rt.bl','priv/host/num.bl','priv/host/decimal.bl','priv/lib/decimal.bl','priv/lib/system/smt.bl',
 'priv/lib/js/rt.mjs','priv/lib/js/leaves.mjs','priv/lib/js/host-leaves.mjs','priv/lib/veritas/ledger.bl','priv/lib/formal/request-record.bl']
for name in inherited:assert sha(Path(baseline['source'])/name)==linkage['source_sha256'][name]
stages={};runs={}
for stage in ['preflight','preflight-controls','focused','word-focused','legacy','regression','native','packets',
 'text-packets','evidence-packets','legacy-evidence-packets','obligation-producer','obligation-reader-1','obligation-reader-2']:
 source=read(E/(stage+'-source-pin.json'));result=read(E/(stage+'-exit.json'));command=read(E/(stage+'-command.json'))
 assert source['sdk_pin']==pin and result['exit_code']==0 and result['runtime_retired'] and result['consumer_cwd_retired'],stage
 for name,digest in source['source_sha256'].items():
  assert sha(R/name)==digest,name
  assert hashlib.sha256(subprocess.check_output(['git','show',source['code_commit']+':'+name],cwd=R)).hexdigest()==digest
 for flag in ['--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=KillMode=control-group']:
  assert flag in command
 assert '--property=RuntimeMaxSec='+('3600' if stage=='native' else '1200') in command
 if stage not in ('preflight','preflight-controls'):assert pin['sdk']+'/bin/bl' in command and '--cold' in command
 log=(E/(stage+'-checks.txt')).read_text()
 if stage in ('focused','word-focused','legacy','regression'):
  count={'focused':11,'word-focused':12,'legacy':5,'regression':31}[stage]
  rows={name:int(total) for name,total in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed',log)}
  assert len(rows)==count and f'{count} file(s) passed, 0 failed, 0 incoherent' in log and result['complete_green_test_summary'] is True
  runs[stage]=rows
 stages[stage]={'source_pin':source,'exit':result,'command_sha256':sha(E/(stage+'-command.json')),'log_sha256':sha(E/(stage+'-checks.txt'))}
assert runs['focused']['formal.obligation-evidence-test']>=120
assert runs['focused']['formal.graph-integer-certificate-test']==54 and runs['focused']['formal.finite-feasibility-test']==35
for stage in ('word-focused','legacy','regression'):assert runs[stage]==parent['assertion_runs'][stage]
preflight=read(E/'source-preflight.json');assert preflight['root']==pin['source'] and preflight['runtime']==pin['sdk'] and preflight['selected-count']==612
for name in ('source-errors','target-dependency-errors','require-cycles','sources_changed_during_analysis'):assert preflight[name]==[]
assert preflight['selector_changed_during_analysis'] is False and preflight['driver_changed_during_analysis'] is False
assert 'SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E/'preflight-controls-checks.txt').read_text()
for stage in ('obligation-reader-1','obligation-reader-2'):
 result=read(E/(stage+'.json'));assert result['status']=='passed' and result['sdk']==pin['sdk']
 assert result['fresh-full-checks']==8 and result['limited-checks']==8
 assert result['manual-schema-preload'] is False and result['warmed-atoms-stable'] is True
 assert result['native-exchanges']==result['oracle-calls']==0
for stage in ('evidence-packets','legacy-evidence-packets'):
 result=read(E/(stage+'.json'));assert result['status']=='passed' and result['sdk']==pin['sdk']
 assert result['packets']==2 and result['fresh-checks']==6 and result['negative-controls']==6
 assert result['native-exchanges']==result['oracle-calls']==0 and result['warmed-atoms-stable'] is True
previous=read(E/'previous-scalar-readers-qualification.json')
assert previous['status']=='passed' and previous['sdk_pin']==pin and previous['recorded_producer_sdk_pin']==baseline
assert previous['records']==20 and previous['fresh_sdk_only_readers']==2 and previous['refusal_controls']==16
assert previous['independently_invalid_text_controls']==3 and previous['solver_exchanges']==previous['oracle_calls']==0
assert read(E/'packets.json')['records']==12
text=read(E/'text-packets.json');assert text['status']=='passed' and text['records']==4 and text['negative-controls']==4
assert text['native-exchanges']==text['oracle-calls']==0 and len(text['domain-observations'])==5
native=read(E/'native.json');before={row['id']:row for row in read(P/'evidence/scalar-integration/native.json')['rows']}
assert len(native['rows'])==len(before)==187;differences=[]
for row in native['rows']:
 prior=before[row['id']];assert row['roots']==prior['roots'] and row['standard-identity']==prior['standard-identity']
 for engine in ('z3','oxiz'):
  current,oldrow=row[engine],prior[engine];assert current['identity']['sdk']==pin['sdk']
  for key in ('worker-sha256','library-sha256'):assert current['identity'][key]==oldrow['identity'][key]
  for key in ('solver-status','verdict','phase','observation-basis'):
   if current.get(key)!=oldrow.get(key):differences.append({'id':row['id'],'engine':engine,'field':key,'before':oldrow.get(key),'after':current.get(key)})
  if current['validation'].get('status')!=oldrow['validation'].get('status'):differences.append({'id':row['id'],'engine':engine,'field':'validation.status'})
write('native-differences.json',differences);assert not differences,differences
assert subprocess.check_output([R/'scripts/prepare-checkout-sdk','--fingerprint'],text=True).strip()==pin['engine_fingerprint']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert subprocess.check_output(['git','show',commit+':'+str(Path(__file__).relative_to(R))],cwd=R)==Path(__file__).read_bytes()
write('qualification.json',{'schema':'bl.obligation-integration-sdk.v1','status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'sdk_pin':pin,'baseline_sdk_pin':baseline,'project_pin_selected':False,'build_linkage_sha256':sha(E/'build-linkage.json'),
 'parent_qualification_sha256':sha(P/'evidence/scalar-integration/qualification.json'),'stages':stages,'assertion_runs':runs,
 'assertion_executions':sum(sum(rows.values()) for rows in runs.values()),'native_questions':187,'native_outcome_differences':differences,
 'source_preflight_namespaces':612,'previous_scalar_readers_qualification_sha256':sha(E/'previous-scalar-readers-qualification.json'),
 'obligation_packets':4,'fresh_obligation_readers':2,'obligation_full_checks':16,'obligation_limited_checks':16,
 'old_v1_evidence_packets':2,'inherited_unchanged_sources':inherited,'compiler_floor_files':141,
 'compiler_proof_authority':False,'goal_complete':False,'qualifier':{'code_commit':commit,'sha256':sha(Path(__file__))},
 'scope':'Exact runtime/artifact qualification of closed vacuity policy, single-pass request headers, finite and graph linear integer proof dispatch, original-background derivation, separate premise evidence, policy-aware conclusions and candidate-only versioned carriers. Actual current and prior packet readers are listed above. Older scalar durable ledger qualification and earlier producer generations remain inherited historical evidence through unchanged ledger/record implementation bytes; their retired stores are not recreated or claimed as reopened here. Source/compiler preservation and mechanical BL checker soundness remain separate obligations.'})
print(json.dumps({'status':'passed','assertion_executions':sum(sum(rows.values()) for rows in runs.values()),'goal_complete':False}))
