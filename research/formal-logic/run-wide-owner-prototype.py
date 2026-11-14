"""Qualify the common wide request source overlay without constructing another SDK."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,re,shutil,subprocess,sys,tempfile,time
P=Path(__file__).resolve().parent;R=P.parent.parent;D=P/'prototypes/wide-owner'
phase=sys.argv[1];assert phase in ('pure',)
E=P/'evidence/wide-owner-prototype'/phase;E.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):(E/name).write_text(json.dumps(value,indent=2)+'\n')
pin=read(P/'sdk-pin.json');qualified=read(P/'evidence/obligation-integration/qualification.json')
assert qualified['status']=='passed' and qualified['sdk_pin']==pin
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
files=[Path(__file__),*sorted(D.rglob('*.bl')),*sorted((P/'src').rglob('*.bl'))]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for path in files:
 name=str(path.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==path.read_bytes();digests[name]=sha(path)
baseline={}
for path in sorted((D/'formal').rglob('*.bl')):
 name=path.relative_to(D);original=Path(pin['source'])/'priv/lib'/name
 baseline[str(name)]=sha(original) if original.exists() else None
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'qualified_runtime_sdk':pin,
 'sdk_library_baseline_sha256':baseline,'in_sdk':False})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
root=Path(tempfile.mkdtemp(prefix='formal-wide-owner-'));cwd=root/'consumer';cwd.mkdir();xdg=root/'xdg';xdg.mkdir(mode=0o700)
command=['timeout','--kill-after=15','1500','env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 'XDG_RUNTIME_DIR='+str(xdg),'FORMAL_WIDE_OWNER_OUTPUT='+str(E/'observations.json'),pin['sdk']+'/bin/bl','--cold',
 '-p',str(D),'-p',str(P/'src'),'test',str(D/'wide-owner-pure-check.bl')]
write('command.json',command);(E/'qualification.json').unlink(missing_ok=True);(E/'observations.json').unlink(missing_ok=True)
started=time.monotonic()
try:
 with (E/'checks.txt').open('w') as stream:code=subprocess.run(command,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(root)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'complete_green_summary':green,'elapsed_seconds':time.monotonic()-started,'private_runtime_retired':not root.exists()})
assert code==0 and green,log[-7000:]
counts=re.findall(r'✓\s+formal.wide-owner-pure-check\s+(\d+) passed',log);assert len(counts)==1 and int(counts[0])>=400
assert all(sha(R/name)==digest for name,digest in digests.items())
observed=read(E/'observations.json');assert observed['sdk']==pin['sdk'] and len(observed['entered-tests'])==7
assert observed['native-exchanges']==observed['oracle-calls']==0 and observed['in-sdk'] is False
rows=next(row['result'] for row in observed['observations'] if row['case']=='corpus');assert len(rows)==187
candidate=next(row['result'] for row in observed['observations'] if row['case']=='unreplayed-candidate')
assert candidate['answer-check']['verdict']=='candidate' and candidate['answer-check']['point-replay']=='not-installed'
assert candidate['logical-conclusion']['status']=='not-established' and candidate['conclusion']['status']!='accepted'
write('qualification.json',{'schema':'bl.wide-owner-pure-prototype.v1','status':'passed','recorded_utc':datetime.now(timezone.utc).isoformat(),
 'qualified_runtime_sdk':pin,'source_pin':read(E/'source-pin.json'),'assertions':int(counts[0]),'questions':187,
 'native_exchanges':0,'oracle_calls':0,'in_sdk':False,'observations_sha256':sha(E/'observations.json'),
 'compiler_proof_authority':False,'scope':'Project source overlay using the existing common request API: all retained theory vocabularies, precise operational descriptor admission, unprivileged coordinates, candidate-only reopening, refused cross-profile certificates, resource refusals and unchanged ignored provenance. Actual native owner execution, narrow regression checks, fresh readers and immutable SDK integration remain separate gates.'})
print(json.dumps({'status':'passed','questions':187,'assertions':int(counts[0]),'in_sdk':False}))
