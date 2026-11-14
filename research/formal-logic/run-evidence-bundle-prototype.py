"""Qualify the isolated evidence bundle and one fresh solver-denied reader."""
import hashlib,json,re,shutil,subprocess,tempfile,time
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/evidence-bundle-prototype'
E.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');parent=read(P/'evidence/word-integration/qualification.json')
word=read(P/'evidence/word-exhaustion-prototype/qualification.json')
assert parent['status']==word['status']=='passed' and parent['sdk_pin']==word['sdk_pin']==pin
assert read(P/'evidence/word-integration/promotion.json')['selected']==pin
assert sha(Path(pin['sdk'])/'artifact.json')==pin['descriptor_sha256']
for n,d in word['source_sha256'].items():assert sha(R/n)==d
prototype=P/'prototypes/evidence-bundle';word_root=P/'prototypes/word-exhaustion'
files=[Path(__file__),*sorted(prototype.rglob('*.bl')),word_root/'formal/word-exhaustion.bl']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
write('source-pin.json',{'sdk_pin':pin,'code_commit':commit,'source_sha256':digests,
 'parent_qualification_sha256':sha(P/'evidence/word-integration/qualification.json'),
 'word_checker_qualification_sha256':sha(P/'evidence/word-exhaustion-prototype/qualification.json')})
for name in ['qualification.json','corpus.json','reader.json','corpus.json.coverage.json']:(E/name).unlink(missing_ok=True)
def run(name,args):
 runtime=Path(tempfile.mkdtemp(prefix='formal-evidence-runtime-'));cwd=Path(tempfile.mkdtemp(prefix='formal-evidence-consumer-'))
 command=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
  '--unit=work-formal-evidence-'+name+'-'+pin['engine_fingerprint'][:12],'--working-directory='+str(cwd),
  '--property=MemoryMax=4G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=600','--property=KillMode=control-group',
  '--setenv=XDG_RUNTIME_DIR='+str(runtime),'--setenv=EVIDENCE_BUNDLE_OUTPUT='+str(E/'corpus.json'),
  'env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',pin['sdk']+'/bin/bl','--cold',
  '-p',str(prototype),'-p',str(word_root),*args]
 write(name+'-command.json',command);(E/(name+'-memory-before.txt')).write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
 started=time.monotonic()
 try:
  with (E/(name+'-checks.txt')).open('w') as out:code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT).returncode
 finally:shutil.rmtree(runtime);shutil.rmtree(cwd)
 write(name+'-exit.json',{'exit_code':code,'elapsed_seconds':time.monotonic()-started,'runtime_retired':not runtime.exists(),'cwd_retired':not cwd.exists()})
 assert code==0,(name,code)
 return (E/(name+'-checks.txt')).read_text()
log=run('producer',['test',str(prototype/'evidence-bundle-check.bl')])
assert '1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
counts=re.findall(r'✓\s+formal.evidence-bundle-check\s+(\d+) passed',log);assert len(counts)==1
coverage=read(E/'corpus.json.coverage.json')
assert set(coverage)=={'proof-and-point-results-have-separate-meanings','binding-closed-data-and-producer-flags',
 'reserve-the-whole-checking-strategy-before-invocation','saved-data-is-rechecked-under-the-readers-allowance',
 'record-both-real-native-claims-with-independent-checks'} and len(coverage)==5
assert int(counts[0])>=47
corpus=read(E/'corpus.json');assert len(corpus['rows'])==2
assert {r['backend'] for r in corpus['rows']}=={'z3','oxiz'}
for row in corpus['rows']:
 assert row['identity']['sdk']==pin['sdk'] and row['result']['answer-check']['verdict']=='solver-claim'
 assert row['result']['proof-check']['points-checked']==8 and row['result']['conclusion']['kind']=='conditional-entailment'
run('reader',['run',str(prototype/'evidence-bundle-reader.bl'),'--',str(E/'corpus.json'),str(E/'reader.json')])
reader=read(E/'reader.json')
assert reader['status']=='passed' and reader['sdk']==pin['sdk'] and reader['packets']==2 and reader['fresh-checks']==6
assert reader['negative-controls']==6 and reader['native-exchanges']==reader['oracle-calls']==0 and reader['warmed-atoms-stable'] is True
assert all(sha(R/n)==d for n,d in digests.items())
artifacts=['source-pin.json','producer-command.json','producer-checks.txt','producer-exit.json','corpus.json','corpus.json.coverage.json',
 'reader-command.json','reader-checks.txt','reader-exit.json','reader.json']
write('qualification.json',{'schema':'bl.evidence-bundle-prototype-qualification.v1','status':'passed','sdk_pin':pin,
 'code_commit':commit,'source_sha256':digests,'assertions':int(counts[0]),'executed_test_names':coverage,'fresh_reader':reader,
 'artifact_sha256':{n:sha(E/n) for n in artifacts},'in_sdk':False,'in_default_oracle':False,
 'compiler_proof_authority':False,'checked_native_execution':False,
 'scope':'A closed original-request-bound evidence bundle, independent axes for existing answers and a fixed finite word certificate strategy, conservative caller-controlled proof reservation, actual native comparison and fresh portable rechecking. No mechanical soundness, physical cost theorem, default effect integration or compiler authority.'})
print(json.dumps({'status':'passed','assertions':int(counts[0]),'fresh_reader_negative_controls':6}))
