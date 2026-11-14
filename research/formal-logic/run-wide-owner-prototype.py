"""Qualify an exact namespace projection beside the SDK; never replace SDK routes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,re,shutil,subprocess,sys,tempfile,time
P=Path(__file__).resolve().parent;R=P.parent.parent;D=P/'prototypes/wide-owner'
phase=sys.argv[1];assert phase in ('pure','native-smoke','native')
E=P/'evidence/wide-owner-prototype'/phase;E.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):(E/name).write_text(json.dumps(value,indent=2)+'\n')
pin=read(P/'sdk-pin.json');qualified=read(P/'evidence/obligation-integration/qualification.json')
assert qualified['status']=='passed' and qualified['sdk_pin']==pin
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
modules={name:'formal.wide-batch.'+name.split('formal.',1)[1] for name in [
 'formal.backend','formal.coordinates','formal.evaluate','formal.graph-execution','formal.graph-question',
 'formal.graph-terms','formal.graph-replay','formal.logic','formal.point-profile','formal.request',
 'formal.request-answer','formal.request-point','formal.request-record','formal.query','formal.question-graph',
 'formal.request-header','formal.vacuity-policy','formal.assumptions','formal.finite-feasibility',
 'formal.graph-integer-certificate','formal.proof-strategy','formal.feasibility','formal.obligation-policy',
 'formal.request-runtime','formal.resources.word','formal.resources.text','formal.resources.typed',
 'formal.scalar-text','formal.scalar-text-value','formal.finite-word-certificate','formal.request-evidence',
 'formal.retained-question','formal.retained-composition']}
modules.update({'veritas.ledger':'formal.wide-batch.ledger','oracle':'formal.wide-batch.oracle'})
paths={}
for name in modules:
 relative=Path(name.replace('.','/')+'.bl');override=D/relative
 paths[name]=override if override.exists() else Path(pin['source'])/'priv/lib'/relative
 assert paths[name].is_file(),name
files=[Path(__file__),*sorted(D.rglob('*.bl')),*sorted((P/'src').rglob('*.bl'))]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for path in files:
 name=str(path.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==path.read_bytes();digests[name]=sha(path)
base={name:{'source':str(path),'sha256':sha(path)} for name,path in paths.items()}
pure=None
if phase!='pure':
 pure=read(P/'evidence/wide-owner-prototype/pure/qualification.json')
 assert pure['status']=='passed' and pure['source_pin']['module_inputs']==base
 assert pure['qualified_runtime_sdk']==pin and pure['native_exchanges']==0
 assert sha(D/'wide-owner-pure-check.bl')==pure['source_pin']['source_sha256'][str((D/'wide-owner-pure-check.bl').relative_to(R))]
 if phase=='native':
  smoke=P/'evidence/wide-owner-prototype/native-smoke';smoke_q=read(smoke/'qualification.json')
  assert smoke_q['status']=='passed' and smoke_q['questions']==9 and smoke_q['raw_status_differences']==0
  assert smoke_q['qualified_runtime_sdk']==pin and smoke_q['source_pin']['module_inputs']==base
  for gate in [smoke,smoke/'reader-one',smoke/'reader-two',P/'evidence/wide-owner-prototype/narrow-regressions']:
   receipt=read(gate/'qualification.json');assert receipt['status']=='passed'
   terminal=read(gate/'owner-terminal.json');terminal=terminal.get('state',terminal)
   assert terminal['SubState']=='exited' and terminal['MainPID']=='0'
   assert terminal['Result']=='success' and terminal['ExecMainStatus']=='0'
   if gate!=smoke:
    assert receipt['sdk_pin']==pin
    assert receipt['source_pin']['producer_qualification_sha256']==sha(smoke/'qualification.json')
  assert read(smoke/'reader-one/qualification.json')['packets']==read(smoke/'reader-two/qualification.json')['packets']==20
 assert not (E/'packets').exists(),'Archive the previous run before another native attempt.'
 (E/'packets').mkdir()
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'qualified_runtime_sdk':pin,
 'module_inputs':base,'in_sdk':False,'sdk_produced':False})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
root=Path(tempfile.mkdtemp(prefix='formal-wide-owner-'));cwd=root/'consumer';cwd.mkdir();xdg=root/'xdg';xdg.mkdir(mode=0o700)
imports=root/'imports';checks=root/'checks';imports.mkdir();checks.mkdir();projections=[]
def project(source,destination):
 text=source.read_text();changes=[]
 for old,new in sorted(modules.items(),key=lambda item:-len(item[0])):
  for pattern in [r'(\(ns\s+)'+re.escape(old)+r'(?=\s|\))',r'(\[)'+re.escape(old)+r'(?=\s|\])']:
   text,count=re.subn(pattern,lambda match:match.group(1)+new,text)
   if count:changes.append({'pattern':pattern,'namespace':new,'count':count})
 # Preserve the ordinary root alias at explicit formerly-unaliased requires.
 text,count=re.subn(r'\[formal\.wide-batch\.oracle\s*\]', '[formal.wide-batch.oracle :as oracle]',text)
 if count:changes.append({'alias':'oracle','count':count})
 destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(text)
 saved=E/'projected'/destination.relative_to(root);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_text(text)
 projections.append({'source':str(source),'source_sha256':sha(source),'transformations':changes,
                     'projected_sha256':sha(destination),'saved':str(saved.relative_to(E))})
for name,path in paths.items():project(path,imports/(modules[name].replace('.','/')+'.bl'))
test_name='wide-owner-pure-check.bl' if phase=='pure' else 'wide-owner-native-check.bl'
test=checks/test_name;project(D/test_name,test)
write('projection.json',projections)
ceiling='1500' if phase=='pure' else ('1500' if phase=='native-smoke' else '21600')
command=['timeout','--kill-after=15',ceiling,'env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 'XDG_RUNTIME_DIR='+str(xdg),'BL_TEST_TIMEOUT='+str(int(ceiling)-60),
 'FORMAL_WIDE_OWNER_OUTPUT='+str(E/'observations.json'),pin['sdk']+'/bin/bl','--cold',
 '-p',str(imports),'-p',str(P/'src'),'test',str(test)]
if phase!='pure':
 pos=command.index(pin['sdk']+'/bin/bl')
 command[pos:pos]=['FORMAL_WIDE_OWNER_SAMPLE='+('smoke' if phase=='native-smoke' else 'all'),
  'FORMAL_WIDE_OWNER_BASELINE='+str(P/'evidence/obligation-integration/native.json'),
  'FORMAL_WIDE_OWNER_PACKETS='+str(E/'packets')]
write('command.json',command);(E/'qualification.json').unlink(missing_ok=True);(E/'observations.json').unlink(missing_ok=True)
started=time.monotonic()
try:
 with (E/'checks.txt').open('w') as stream:code=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(root)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'complete_green_summary':green,'elapsed_seconds':time.monotonic()-started,'private_runtime_retired':not root.exists()})
assert code==0 and green,log[-7000:]
namespace='formal.wide-owner-pure-check' if phase=='pure' else 'formal.wide-owner-native-check'
counts=re.findall(r'✓\s+'+re.escape(namespace)+r'\s+(\d+) passed',log)
assert len(counts)==1 and int(counts[0])>=(400 if phase=='pure' else 200)
assert all(sha(R/name)==digest for name,digest in digests.items())
assert all(sha(Path(row['source']))==row['source_sha256'] and sha(E/row['saved'])==row['projected_sha256'] for row in projections)
observed=read(E/'observations.json');assert observed['sdk']==pin['sdk']
if phase!='pure':
 expected=9 if phase=='native-smoke' else 187
 assert len(observed['entered-tests'])==4 and len(observed['rows'])==expected
 assert len(observed['packets'])==2*expected+2
 assert observed['in-sdk'] is False and observed['compiler-proof-authority'] is False
 for packet in observed['packets']:
  path=E/'packets'/packet['file'];assert path.is_file() and sha(path)==packet['sha256']
 differences=[]
 for row in observed['rows']:
  assert len(row['outcomes'])==2
  for outcome in row['outcomes']:
   assert outcome['point-replay']=='not-installed' and outcome['logical-conclusion']['status']=='not-established'
   assert outcome['consumer-conclusion']['status']!='accepted'
   if outcome['status-changed']:differences.append({'id':row['id'],**outcome})
 write('native-status-differences.json',differences)
 write('qualification.json',{'schema':'bl.wide-owner-native-prototype.v1','status':'passed','phase':phase,
  'recorded_utc':datetime.now(timezone.utc).isoformat(),'qualified_runtime_sdk':pin,'source_pin':read(E/'source-pin.json'),
  'pure_qualification_sha256':sha(P/'evidence/wide-owner-prototype/pure/qualification.json'),
  'assertions':int(counts[0]),'questions':expected,'paired_backend_requests':2*expected,
  'candidate_packets':len(observed['packets']),'raw_status_differences':len(differences),
  'in_sdk':False,'sdk_produced':False,'projection_sha256':sha(E/'projection.json'),
  'observations_sha256':sha(E/'observations.json'),'compiler_proof_authority':False,
  'scope':'Actual paired native owners through the projected common request/evidence interface, exact baseline subject and worker/library identity, explicit native claim and unavailable replay, retained array assumptions, fresh complete requests, changed-context refusal and expiring effect leases. Packets retain candidates only. Broader native corpus, narrow regressions, fresh candidate readers and immutable SDK integration are separate gates.'})
 print(json.dumps({'status':'passed','phase':phase,'questions':expected,'assertions':int(counts[0]),'raw_status_differences':len(differences)}))
 raise SystemExit(0)
assert len(observed['entered-tests'])==7
assert type(observed['native-exchanges']) is int and observed['native-exchanges']==observed['oracle-calls']==0
assert observed['in-sdk'] is False and len(observed['native-windows'])==6
assert all(type(row['native-exchanges']) is int and row['native-exchanges']==row['oracle-calls']==0 for row in observed['native-windows'])
rows=next(row['result'] for row in observed['observations'] if row['case']=='corpus');assert len(rows)==187
candidate=next(row['result'] for row in observed['observations'] if row['case']=='unreplayed-candidate')
assert candidate['answer-check']['verdict']=='candidate' and candidate['answer-check']['point-replay']=='not-installed'
assert candidate['logical-conclusion']['status']=='not-established' and candidate['conclusion']['status']!='accepted'
write('qualification.json',{'schema':'bl.wide-owner-pure-prototype.v1','status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'qualified_runtime_sdk':pin,'source_pin':read(E/'source-pin.json'),'assertions':int(counts[0]),'questions':187,
 'native_exchanges':0,'oracle_calls':0,'native_exchange_scope':'six recorded operational test windows','in_sdk':False,'sdk_produced':False,'projection_sha256':sha(E/'projection.json'),
 'observations_sha256':sha(E/'observations.json'),'compiler_proof_authority':False,
 'scope':'Explicit namespace/import projection using the common request API shape beside the unchanged SDK. All retained theory vocabularies, precise operational descriptor admission, unprivileged coordinates, candidate-only reopening, refused cross-profile certificates, resource refusals and unchanged ignored provenance. Native owner execution, narrow regression checks, fresh readers and immutable SDK integration remain separate gates.'})
print(json.dumps({'status':'passed','questions':187,'assertions':int(counts[0]),'in_sdk':False,'sdk_produced':False}))
