"""Capture the nine real consumer/premise cases as source evidence for the dossier."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;B=P/'evidence/obligation-integration';E=P/'evidence/obligation-dossier-cases';E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(B/'sdk-candidate.json');q=read(B/'qualification.json');assert q['status']=='passed' and q['sdk_pin']==pin
assert read(P/'sdk-pin.json') in [pin,read(B/'baseline-sdk-pin.json')]
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in [Path(__file__),P/'obligation-dossier-cases.bl']:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'sdk_pin':pin,'runtime_qualification_sha256':sha(B/'qualification.json')})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
root=Path(tempfile.mkdtemp(prefix='formal-obligation-dossier-'));xdg=root/'xdg';xdg.mkdir(mode=0o700)
command=['timeout','--kill-after=15','1100','env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 'XDG_RUNTIME_DIR='+str(xdg),'FORMAL_OBLIGATION_DOSSIER_CASES='+str(E/'cases.json'),pin['sdk']+'/bin/bl','--cold',
 'test',str(P/'obligation-dossier-cases.bl')]
write('command.json',command);(E/'qualification.json').unlink(missing_ok=True);(E/'cases.json').unlink(missing_ok=True)
start=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,cwd=root,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(root)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'green_summary':green,'elapsed_seconds':time.monotonic()-start,'private_runtime_retired':not root.exists()})
assert code==0 and green,log[-5000:]
counts=re.findall(r'✓\s+formal.obligation-dossier-cases\s+(\d+) passed',log);assert len(counts)==1 and int(counts[0])>=41
assert all(sha(R/n)==digest for n,digest in digests.items())
cases=read(E/'cases.json');assert cases['schema']=='bl.obligation-dossier-cases.v1' and cases['sdk']==pin['sdk']
assert len(cases['rows'])==9 and {row['consumer'] for row in cases['rows']}=={'allow','report','reject'}
assert {row['background'] for row in cases['rows']}=={'witnessed','inconsistent','not-established'}
assert all(row['result']['proof-check']['status']=='checked' for row in cases['rows'])
assert cases['backend-fork']['result']['conclusion']['status']=='accepted'
assert cases['native-exchanges']==cases['oracle-calls']==0 and cases['compiler-proof-authority'] is False
write('qualification.json',{'schema':'bl.obligation-dossier-cases.v1','status':'passed','sdk_pin':pin,'source_pin':read(E/'source-pin.json'),
 'assertions':int(counts[0]),'rows':9,'backend_fork_checks':1,'native_exchanges':0,'oracle_calls':0,'cases_sha256':sha(E/'cases.json'),
 'compiler_proof_authority':False,'scope':'Nine actual pure word proof/premise/policy checks and one adapter-independent certificate reuse, with complete candidate packets and separately labelled producer checking allowances. This source evidence is for inspection; saved result fields and producer allowances are not checking authority. Renderer and browser qualification follow separately.'})
print(json.dumps({'status':'passed','rows':9,'assertions':int(counts[0]),'native_exchanges':0}))
