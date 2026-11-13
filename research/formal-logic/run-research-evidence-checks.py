"""Check the actual qualified-word evidence producer, native Org and pure renderer."""
import hashlib,json,os,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parent.parent
E=P/'evidence/word-presentation/research'
E.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');q=read(P/'evidence/word-integration/qualification.json');kit=read(P/'evidence/word-presentation/kit-state.json')
assert q['status']=='passed' and q['sdk_pin']==pin
assert read(P/'evidence/word-integration/promotion.json')['selected']==pin
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
for name,digest in kit['rendering_source_sha256'].items():assert sha(Path(kit['root'])/name)==digest
files=[Path(__file__),*sorted((P/'dossier').rglob('*.bl')),*sorted((P/'dossier').glob('*.js'))]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for path in files:
 name=str(path.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==path.read_bytes();digests[name]=sha(path)
runtime=Path(tempfile.mkdtemp(prefix='formal-research-runtime-'));cwd=Path(tempfile.mkdtemp(prefix='formal-research-cwd-'));store=cwd/'elements.bl.org'
imports=[P/'dossier',Path(kit['root'])/'research-elements/kit',Path(kit['root'])/'bl-org-dossier/kit']
request=[pin['sdk']+'/bin/bl','--cold']
for path in imports:request+=['-p',str(path)]
request+=['test',str(P/'dossier/research-evidence-check.bl')]
command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
 '--unit=work-formal-research-evidence-'+pin['engine_fingerprint'][:12], '--working-directory='+str(cwd),
 '--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=600','--property=KillMode=control-group',
 '--setenv=XDG_RUNTIME_DIR='+str(runtime),'--setenv=FORMAL_EVIDENCE_ROOT='+str(P),'--setenv=FORMAL_EVIDENCE_STORE='+str(store),
 'env','-u','BEAM_LISP_PATH',*request]
write('source-pin.json',{'sdk_pin':pin,'code_commit':commit,'source_sha256':digests,'kit_state_sha256':sha(P/'evidence/word-presentation/kit-state.json')})
write('command.json',command);(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
(E/'qualification.json').unlink(missing_ok=True);start=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
 if store.exists():(E/'actual-snapshots.bl.org').write_bytes(store.read_bytes())
finally:shutil.rmtree(runtime);shutil.rmtree(cwd)
log=(E/'checks.txt').read_text();green='1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'process_exit_code':code,'complete_green_test_summary':green,'elapsed_seconds':time.monotonic()-start,'runtime_retired':not runtime.exists(),'cwd_retired':not cwd.exists()})
assert code==0 and green
assert all(sha(R/name)==digest for name,digest in digests.items())
counts=re.findall(r'✓\s+formal.research-evidence-check\s+(\d+) passed',log);assert len(counts)==1
write('qualification.json',{'status':'passed','schema':'bl.formal-research-evidence-checks.v1','sdk_pin':pin,'assertions':int(counts[0]),
 'source_sha256':digests,'code_commit':commit,'kit_commit':kit['commit'],'browser_save_qualified':False,
 'scope':'Actual qualified artifact traversal, located/dated supported facts, explicit pending facts, strict installed renderer, native Org snapshots and stale-basis preservation. Actual host/browser save and dossier qualification remain separate.',
 'compiler_proof_authority':False,'artifact_sha256':{n:sha(E/n) for n in ['checks.txt','exit.json','source-pin.json','actual-snapshots.bl.org']}})
print(json.dumps({'status':'passed','assertions':int(counts[0]),'browser_save_qualified':False}))
