"""Qualify the additive oracle map extension beside the unchanged formal projection."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;B=P/'evidence/scalar-integration-prototype/pure';E=B.parent/'oracle'
E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');parent=read(B/'qualification.json')
assert parent['status']=='passed' and parent['base_sdk_pin']==pin
for n,d in parent['source_pin']['source_sha256'].items():assert sha(R/n)==d,n
tests=['test/bl/formal/evidence_oracle_test.bl','test/bl/system/formal_effect_test.bl']
files=[Path(__file__),R/'priv/lib/oracle.bl',*[R/n for n in tests]]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'base_sdk_pin':pin,'formal_projection_qualification_sha256':sha(B/'qualification.json')})
runtime=Path(tempfile.mkdtemp(prefix='formal-oracle-extension-'));imports=runtime/'imports';imports.mkdir();xdg=runtime/'xdg';xdg.mkdir(mode=0o700)
modules={};copied=[]
for row in read(B/'projection.json'):
 if not row['source'].startswith('priv/lib/'):continue
 source=B/row['saved'];assert sha(source)==row['projected_sha256']
 relative=Path(row['saved']).relative_to('projected/imports');target=imports/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 old=row['source'].removeprefix('priv/lib/').removesuffix('.bl').replace('/','.')
 modules[old]=str(relative).removesuffix('.bl').replace('/','.');copied.append({'source':str(source.relative_to(R)),'sha256':sha(source)})
modules['oracle']='formal.scalar-batch.oracle'
def project(source,target):
 text=source.read_text()
 for old,new in sorted(modules.items(),key=lambda item:-len(item[0])):
  for pattern in [r'(\(ns\s+)'+re.escape(old)+r'(?=\s|\))',r'(\[)'+re.escape(old)+r'(?=\s|\])']:
   text=re.sub(pattern,lambda m:m.group(1)+new,text)
 target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
 saved=E/'projected'/target.relative_to(runtime);saved.parent.mkdir(parents=True,exist_ok=True);saved.write_text(text)
 return {'source':str(source.relative_to(R)),'saved':str(saved.relative_to(E)),'sha256':sha(saved)}
projections=[project(R/'priv/lib/oracle.bl',imports/'formal/scalar-batch/oracle.bl')]
paths=[]
for n in tests:
 target=runtime/'checks'/Path(n).name;projections.append(project(R/n,target));paths.append(str(target))
write('projection.json',{'modules':modules,'copied':copied,'new_sources':projections})
command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
 '--unit=work-formal-oracle-extension-'+pin['engine_fingerprint'][:12],'--working-directory='+str(runtime),
 '--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=1200','--property=KillMode=control-group',
 '--setenv=XDG_RUNTIME_DIR='+str(xdg),'env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 pin['sdk']+'/bin/bl','--cold','-p',str(imports),'test',*paths]
write('command.json',command);(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
(E/'qualification.json').unlink(missing_ok=True);started=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(runtime)
log=(E/'checks.txt').read_text();green='2 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'exit_code':code,'green_summary':green,'elapsed_seconds':time.monotonic()-started,'runtime_retired':not runtime.exists()})
assert code==0 and green
counts={n:int(c) for n,c in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed',log)}
assert set(counts)=={'formal.evidence-oracle-test','system.formal-effect-test'}
assert all(sha(R/n)==d for n,d in digests.items())
write('qualification.json',{'schema':'bl.evidence-oracle-extension-projection.v1','status':'passed','base_sdk_pin':pin,
 'source_pin':read(E/'source-pin.json'),'assertion_runs':counts,'assertions':sum(counts.values()),
 'projection_sha256':sha(E/'projection.json'),'sdk_produced':False,'compiler_proof_authority':False,
 'scope':'Additive explicit oracle method acceptance and legacy effect propagation beside the qualified unchanged formal projection. No default compiler/oracle cutover.'})
print(json.dumps({'status':'passed','assertions':sum(counts.values())}))
