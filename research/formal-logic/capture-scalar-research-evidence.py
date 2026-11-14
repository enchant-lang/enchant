"""Save the actual source-backed word evidence view as a product-owned Org record."""
import hashlib,json,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-presentation/research'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');q=read(E/'qualification.json');kit=read(P/'evidence/scalar-presentation/kit-state.json')
assert q['status']=='passed' and q['sdk_pin']==pin
for name,digest in q['source_sha256'].items():assert sha(R/name)==digest
script=P/'dossier/research-evidence-capture.bl';target=P/'elements/word-answer-evidence.bl.org'
assert target.is_file()
prior=target.read_bytes()
assert len(re.findall(rb'^#\+begin_research_element\b',prior,re.M))==1
baseline=read(P/'evidence/word-presentation/research/capture-exit.json')
assert sha(target)==baseline['snapshot_sha256']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();files=[Path(__file__),script];digests={}
for f in files:
 name=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+name],cwd=R)==f.read_bytes();digests[name]=sha(f)
runtime=Path(tempfile.mkdtemp(prefix='formal-evidence-capture-runtime-'));cwd=Path(tempfile.mkdtemp(prefix='formal-evidence-capture-cwd-'))
request=[pin['sdk']+'/bin/bl','--cold','-p',str(P/'dossier'),'-p',str(Path(kit['root'])/'research-elements/kit'),
         'run',str(script),'--',str(P),str(target)]
command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
 '--unit=work-formal-research-capture-'+pin['engine_fingerprint'][:12],'--working-directory='+str(cwd),
 '--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=600','--property=KillMode=control-group',
 '--setenv=XDG_RUNTIME_DIR='+str(runtime),'env','-u','BEAM_LISP_PATH',*request]
write('capture-source-pin.json',{'sdk_pin':pin,'code_commit':commit,'source_sha256':digests,'producer_qualification_sha256':sha(E/'qualification.json')})
write('capture-command.json',command);(E/'capture-memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True));started=time.monotonic()
try:
 with (E/'capture-checks.txt').open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(runtime);shutil.rmtree(cwd)
write('capture-exit.json',{'exit_code':code,'elapsed_seconds':time.monotonic()-started,'runtime_retired':not runtime.exists(),'cwd_retired':not cwd.exists(),
 'target':str(target),'snapshot_sha256':sha(target) if target.exists() else None,
 'prior_snapshot_sha256':hashlib.sha256(prior).hexdigest(),'prior_bytes_preserved':target.exists() and target.read_bytes().startswith(prior)})
assert code==0 and target.exists()
assert target.read_bytes().startswith(prior) and len(re.findall(rb'^#\+begin_research_element\b',target.read_bytes(),re.M))==2
assert all(sha(R/name)==digest for name,digest in digests.items())
assert ':snapshot :saved' in (E/'capture-checks.txt').read_text()
print(json.dumps({'status':'snapshot-saved','path':str(target),'snapshot_sha256':sha(target),'browser_save_qualified':False}))
