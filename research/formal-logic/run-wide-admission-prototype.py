"""Check independent bounded wide typing against all retained native vocabulary."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;B=P/'evidence/obligation-integration';E=P/'evidence/wide-admission-prototype';E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(B/'sdk-candidate.json');selected=read(P/'sdk-pin.json')
assert selected==pin and read(B/'promotion.json')['selected']==pin
assert read(B/'build-linkage.json')['sdk_pin']==pin and read(B/'focused-exit.json')['exit_code']==0
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
prototype=P/'prototypes/wide-admission';files=[Path(__file__),*sorted(prototype.rglob('*.bl')),*sorted((P/'src').rglob('*.bl'))]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'sdk_pin':pin,'build_linkage_sha256':sha(B/'build-linkage.json')})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
root=Path(tempfile.mkdtemp(prefix='formal-wide-admission-'));cwd=root/'consumer';cwd.mkdir();xdg=root/'xdg';xdg.mkdir(mode=0o700)
command=['timeout','--kill-after=15','1100','env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 'XDG_RUNTIME_DIR='+str(xdg),'FORMAL_WIDE_ADMISSION_OUTPUT='+str(E/'observations.json'),pin['sdk']+'/bin/bl','--cold',
 '-p',str(prototype),'-p',str(P/'src'),'test',str(prototype/'wide-admission-check.bl')]
write('command.json',command);(E/'qualification.json').unlink(missing_ok=True);(E/'observations.json').unlink(missing_ok=True)
start=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(root)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'green_summary':green,'elapsed_seconds':time.monotonic()-start,'runtime_retired':not root.exists()})
assert code==0 and green,log[-6000:]
counts=re.findall(r'✓\s+formal.wide-admission-check\s+(\d+) passed',log);assert len(counts)==1 and int(counts[0])>=960
assert all(sha(R/n)==digest for n,digest in digests.items())
observed=read(E/'observations.json');assert observed['sdk']==pin['sdk'] and len(observed['entered-tests'])==7
corpus=next(row['value'] for row in observed['observations'] if row['case']=='corpus')
assert len(corpus['rows'])==187 and all(row['status']=='admitted' for row in corpus['rows'])
assert corpus['native-exchanges']==corpus['oracle-calls']==0
write('qualification.json',{'schema':'bl.wide-admission-prototype.v1','status':'passed','sdk_pin':pin,
 'code_commit':commit,'source_sha256':digests,'assertions':int(counts[0]),'in_sdk':False,'compiler_proof_authority':False,
 'questions':187,'native_exchanges':0,'oracle_calls':0,'observations_sha256':sha(E/'observations.json'),
 'scope':'Separate bounded raw graph/literal/descriptor preflight and fresh generic typing across all 187 retained questions. Typed admission grants no replay interpreter, proof strategy, native execution or backend capability. Unknown provenance remains original graph data. Work charging is an abstract conservative policy, not a proved time/heap bound. The prototype does not yet extend the common SDK request envelope or native owner.'})
print(json.dumps({'status':'passed','assertions':int(counts[0]),'questions':187,'in_sdk':False}))
