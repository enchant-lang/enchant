"""Check the isolated graph integer kernel only after the scalar SDK is fully qualified and selected."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/request-header-prototype'
E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');parent=read(P/'evidence/scalar-integration/qualification.json')
assert parent['status']=='passed' and parent['sdk_pin']==pin
assert read(P/'evidence/scalar-integration/promotion.json')['selected']==pin
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
prototype=P/'prototypes/request-header';files=[Path(__file__),*sorted(prototype.rglob('*.bl'))]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'sdk_pin':pin,
 'parent_qualification_sha256':sha(P/'evidence/scalar-integration/qualification.json')})
runtime=Path(tempfile.mkdtemp(prefix='formal-feasibility-runtime-'));cwd=Path(tempfile.mkdtemp(prefix='formal-feasibility-consumer-'))
command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
 '--unit=work-formal-request-header-'+pin['engine_fingerprint'][:12],'--working-directory='+str(cwd),
 '--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=600','--property=KillMode=control-group',
 '--setenv=XDG_RUNTIME_DIR='+str(runtime),'--setenv=FORMAL_REQUEST_HEADER_OUTPUT='+str(E/'observations.json'),'env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 pin['sdk']+'/bin/bl','--cold','-p',str(prototype),'test',str(prototype/'request-header-check.bl')]
write('command.json',command);(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
(E/'qualification.json').unlink(missing_ok=True)
(E/'observations.json').unlink(missing_ok=True)
started=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(runtime);shutil.rmtree(cwd)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'green_summary':green,'elapsed_seconds':time.monotonic()-started,
 'runtime_retired':not runtime.exists(),'cwd_retired':not cwd.exists()})
assert code==0 and green
counts=re.findall(r'✓\s+formal.request-header-check\s+(\d+) passed',log);assert len(counts)==1 and int(counts[0])>=54
assert all(sha(R/n)==d for n,d in digests.items())
observed=read(E/'observations.json')
assert observed['sdk']==pin['sdk'] and observed['compiler-proof-authority'] is False
assert len(observed['entered-tests'])==6 and set(observed['entered-tests'])=={'accepted','refusals','metadata','not-typed','measurement','no-native'}
assert observed['measurement']['previous-graph-check-invocations']>=6
assert observed['measurement']['single-pass-graph-check-invocations']==1
assert observed['measurement']['universal-speed-claim'] is False
write('qualification.json',{'schema':'bl.request-header-prototype-qualification.v1','status':'passed','sdk_pin':pin,
 'code_commit':commit,'source_sha256':digests,'assertions':int(counts[0]),'in_sdk':False,'in_common_evidence_interface':False,
 'compiler_proof_authority':False,'checked_native_execution':False,'actual_observations_sha256':sha(E/'observations.json'),
 'scope':'One canonical graph check for raw request headers; preserved complete original references and unknown shared metadata; refusal parity with the previous header path; explicit separation from typed admission; calibrated actual graph/check call counts and no native/oracle execution. Does not measure universal speedup, remove other request validation, install a cache authority or change the SDK.'})
print(json.dumps({'status':'passed','assertions':int(counts[0]),'in_sdk':False}))
