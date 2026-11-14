"""Two fresh readers of candidate-only obligations on the exact green projection."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,tempfile,time
P=Path(__file__).resolve().parent;R=P.parent.parent
E=P/'evidence/obligation-integration-prototype/packets';E.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
Q=P/'evidence/obligation-integration-prototype/all';qualified=read(Q/'qualification.json')
assert qualified['status']=='passed'
pin=read(P/'sdk-pin.json');assert qualified['base_sdk_pin']==pin
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
for name,digest in qualified['source_pin']['source_sha256'].items():assert sha(R/name)==digest,name
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
files=[Path(__file__),P/'obligation-packet-producer.bl',P/'obligation-packet-reader.bl']
digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'pure_qualification_sha256':sha(Q/'qualification.json'),'base_sdk_pin':pin})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
root=Path(tempfile.mkdtemp(prefix='formal-obligation-cold-'));imports=root/'imports';imports.mkdir()
mapping={};copied=[]
for row in qualified['projections']:
 saved=Q/row['saved'];assert sha(saved)==row['projected_sha256']
 if not row['saved'].startswith('projected/imports/'):continue
 old=re.search(r'\(ns\s+([^\s)]+)',(R/row['source']).read_text()).group(1)
 new=re.search(r'\(ns\s+([^\s)]+)',saved.read_text()).group(1)
 mapping[old]=new
 destination=imports/(new.replace('.','/')+'.bl');destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(saved,destination)
 copied.append({'source':str(saved.relative_to(R)),'sha256':sha(destination)})
for source in files[1:]:
 text=source.read_text()
 for old,new in sorted(mapping.items(),key=lambda p:-len(p[0])):
  for pattern in [r'(\(ns\s+)'+re.escape(old)+r'(?=\s|\))',r'(\[)'+re.escape(old)+r'(?=\s|\])']:
   text=re.sub(pattern,lambda m:m.group(1)+new,text)
 (root/source.name).write_text(text);(E/source.name).write_text(text)
write('projection-inputs.json',copied)
commands=[];exits=[]
try:
 for stage in ['producer','reader-1','reader-2']:
  cwd=root/stage;cwd.mkdir();xdg=cwd/'xdg';xdg.mkdir(mode=0o700)
  role='producer' if stage=='producer' else 'reader'
  arguments=[str(E/'corpus.json')]+([] if stage=='producer' else [str(E/(stage+'.json'))])
  command=['timeout','--kill-after=15','900','env','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
   'XDG_RUNTIME_DIR='+str(xdg),'BEAM_LISP_PATH='+str(imports),pin['sdk']+'/bin/bl','--cold','-p',str(imports),
   'run',str(root/('obligation-packet-'+role+'.bl')),'--',*arguments]
  commands.append({'stage':stage,'command':command});write('commands.json',commands)
  start=time.monotonic()
  with (E/(stage+'.txt')).open('w') as out:code=subprocess.run(command,cwd=cwd,stdout=out,stderr=subprocess.STDOUT).returncode
  exits.append({'stage':stage,'exit_code':code,'elapsed_seconds':time.monotonic()-start});write('exits.json',exits)
  assert code==0,(E/(stage+'.txt')).read_text()[-6000:]
finally:
 shutil.rmtree(root)
 write('cleanup.json',{'private_runtime_retired':not root.exists()})
assert all(sha(R/n)==digest for n,digest in digests.items())
assert sha(Q/'qualification.json')==read(E/'source-pin.json')['pure_qualification_sha256']
for stage in ['reader-1','reader-2']:
 result=read(E/(stage+'.json'));assert result['status']=='passed' and result['fresh-full-checks']==8
 assert result['limited-checks']==8 and result['native-exchanges']==result['oracle-calls']==0
 assert result['manual-schema-preload'] is False and result['warmed-atoms-stable'] is True
write('qualification.json',{'schema':'bl.obligation-cold-projection.v1','status':'passed','base_sdk_pin':pin,
 'source_pin':read(E/'source-pin.json'),'candidate_packets':4,'fresh_readers':2,'fresh_full_checks':16,
 'limited_checks':16,'native_exchanges':0,'oracle_calls':0,'manual_schema_preload':False,
 'runtime_retired':not root.exists(),'in_sdk':False,'compiler_proof_authority':False})
print(json.dumps({'status':'passed','candidate_packets':4,'fresh_readers':2,'in_sdk':False}))
