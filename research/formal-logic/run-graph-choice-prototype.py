"""Check the reviewed integer-choice graph extension against the fixed new SDK."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;B=P/'evidence/obligation-integration';E=P/'evidence/graph-choice-prototype';E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(B/'sdk-candidate.json');baseline=read(P/'sdk-pin.json')
assert read(B/'baseline-sdk-pin.json')==baseline
assert read(B/'build-linkage.json')['sdk_pin']==pin and read(B/'focused-exit.json')['exit_code']==0
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
search_q=read(P/'evidence/graph-search-prototype/qualification.json')
assert search_q['status']=='passed' and search_q['sdk_pin']==pin
for n,digest in search_q['source_sha256'].items():assert sha(R/n)==digest,n
prototype=P/'prototypes/graph-choice';search=P/'prototypes/graph-search'
files=[Path(__file__),*sorted(prototype.rglob('*.bl')),*sorted(search.rglob('*.bl'))]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'sdk_pin':pin,'build_linkage_sha256':sha(B/'build-linkage.json')})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
root=Path(tempfile.mkdtemp(prefix='formal-graph-choice-'));cwd=root/'consumer';cwd.mkdir();xdg=root/'xdg';xdg.mkdir(mode=0o700)
command=['timeout','--kill-after=15','1100','env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 'XDG_RUNTIME_DIR='+str(xdg),'FORMAL_GRAPH_CHOICE_OUTPUT='+str(E/'observations.json'),pin['sdk']+'/bin/bl','--cold',
 '-p',str(prototype),'-p',str(search),'test',str(prototype/'graph-choice-check.bl')]
write('command.json',command);(E/'qualification.json').unlink(missing_ok=True);(E/'observations.json').unlink(missing_ok=True)
start=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(root)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'green_summary':green,'elapsed_seconds':time.monotonic()-start,'runtime_retired':not root.exists()})
assert code==0 and green,log[-6000:]
counts=re.findall(r'✓\s+formal.graph-choice-check\s+(\d+) passed',log);assert len(counts)==1 and int(counts[0])>=45
assert all(sha(R/n)==digest for n,digest in digests.items())
observed=read(E/'observations.json');assert observed['sdk']==pin['sdk'] and len(observed['entered-tests'])==8
assert set(observed['entered-tests'])=={'extension','hygiene','provenance','formal-values','budgets','refusals','packets','no-native'}
assert {row['case'] for row in observed['observations']}=={'absolute','nested'}
assert all(row['result']['target-proof-check']['status']=='checked' for row in observed['observations'])
write('qualification.json',{'schema':'bl.graph-choice-prototype.v1','status':'passed','sdk_pin':pin,
 'code_commit':commit,'source_sha256':digests,'assertions':int(counts[0]),'in_sdk':False,'compiler_proof_authority':False,
 'observations_sha256':sha(E/'observations.json'),'scope':'Fresh original graph admission, bounded total integer choice lifting with explicit definitions and collision checks, independent derived-target linear certificate checking, separate original/generated assumption ledgers, operational-only context rewriting preserving shared provenance and ignored formal-value metadata, low allowance refusals and candidate-only reopening. The conservative extension implementation is reviewed, not mechanically proved; its additional trust is explicit. The strategy is not installed in the common SDK dispatcher. No Source/compiler or whole-language totality claim.'})
print(json.dumps({'status':'passed','assertions':int(counts[0]),'in_sdk':False}))
