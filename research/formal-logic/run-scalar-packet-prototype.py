"""Reopen actual projected managed-text packets in a fresh solver-denied VM."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/scalar-integration-prototype/packets'
E.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');basis=P/'evidence/scalar-integration-prototype'
parents={}
for stage in ['pure','owners','legacy']:
 qpath=basis/stage/'qualification.json';q=read(qpath)
 assert q['status']=='passed' and q['base_sdk_pin']==pin
 for n,d in q['source_pin']['source_sha256'].items():assert sha(R/n)==d,n
 parents[stage]=sha(qpath)
corpus=basis/'owners/native.json';observations=read(corpus)['observations'];assert len(observations)==4
assert {r['case'] for r in observations}=={'coordinate','codepoint-contract'}
assert {r['backend'] for r in observations}=={'z3','oxiz'}
for row in observations:
 assert row['source']['identity']['sdk']==pin['sdk'] and row['compiler-proof-authority'] is False
for kind in ['coordinate','codepoint-contract']:
 rows=[r for r in observations if r['case']==kind];assert len(rows)==2
 assert rows[0]['subject-reference']==rows[1]['subject-reference']
files=[Path(__file__),P/'scalar-packet-reader.bl',corpus]
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'base_sdk_pin':pin,'parent_qualifications':parents})
runtime=Path(tempfile.mkdtemp(prefix='formal-scalar-packets-'));imports=runtime/'imports';imports.mkdir();xdg=runtime/'xdg';xdg.mkdir(mode=0o700)
projection=read(basis/'pure/projection.json');modules={};copied=[]
for row in projection:
 if not row['source'].startswith('priv/lib/'):continue
 source=basis/'pure'/row['saved'];assert sha(source)==row['projected_sha256']
 relative=Path(row['saved']).relative_to('projected/imports');target=imports/relative;target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(source,target)
 old=row['source'].removeprefix('priv/lib/').removesuffix('.bl').replace('/','.')
 modules[old]=str(relative).removesuffix('.bl').replace('/','.')
 copied.append({'source':str(source.relative_to(R)),'sha256':sha(source)})
reader=(P/'scalar-packet-reader.bl').read_text()
for old,new in sorted(modules.items(),key=lambda item:-len(item[0])):
 reader=re.sub(r'(\[)'+re.escape(old)+r'(?=\s|\])',lambda m:m.group(1)+new,reader)
target=runtime/'reader.bl';target.write_text(reader);(E/'projected-reader.bl').write_text(reader)
write('projection.json',{'modules':modules,'copied':copied,'reader_sha256':sha(target)})
command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
 '--unit=work-formal-scalar-packet-reader-'+pin['engine_fingerprint'][:12],'--working-directory='+str(runtime),
 '--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=1200','--property=KillMode=control-group',
 '--setenv=XDG_RUNTIME_DIR='+str(xdg),'env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
 pin['sdk']+'/bin/bl','--cold','-p',str(imports),'run',str(target),'--',str(corpus),str(E/'reader.json')]
write('command.json',command);(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
(E/'qualification.json').unlink(missing_ok=True);(E/'reader.json').unlink(missing_ok=True);started=time.monotonic()
try:
 with (E/'checks.txt').open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
finally:shutil.rmtree(runtime)
write('exit.json',{'exit_code':code,'elapsed_seconds':time.monotonic()-started,'runtime_retired':not runtime.exists()})
assert code==0
reader=read(E/'reader.json')
assert reader['status']=='passed' and reader['records']==4 and reader['negative-controls']==4
assert reader['manual-schema-preload'] is False and reader['warmed-atoms-stable'] is True
assert reader['native-exchanges']==reader['oracle-calls']==0 and reader['sdk']==pin['sdk']
assert all(sha(R/n)==d for n,d in digests.items())
write('qualification.json',{'schema':'bl.scalar-packet-projection-qualification.v1','status':'passed','base_sdk_pin':pin,
 'source_pin':read(E/'source-pin.json'),'reader':reader,'reader_sha256':sha(E/'reader.json'),
 'corpus_sha256':sha(corpus),'records':4,'manual_schema_preload':False,'sdk_produced':False,
 'compiler_proof_authority':False,'scope':'Fresh rechecking of four actual managed text packets using explicit namespace projections on the selected word SDK. This is not a qualified production SDK or authenticated execution history.'})
print(json.dumps({'status':'passed','records':4,'native_exchanges':0,'sdk_produced':False}))
