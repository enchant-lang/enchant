"""Exercise real browser saves on an owned artifact fixture, then retire its host."""
import hashlib,json,shutil,socket,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/obligation-presentation/research-browser'
E.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(E/n).write_text(json.dumps(v,indent=2)+'\n')
pin=read(P/'sdk-pin.json');kit=read(P/'evidence/obligation-presentation/kit-state.json');tools=read(P/'evidence/observation-semantics/browser-tools.json')
assert read(P/'evidence/obligation-integration/qualification.json')['sdk_pin']==pin
assert read(P/'evidence/obligation-presentation/dossier-check-exit.json')['exit_code']==0
for t in tools.values():assert subprocess.check_output(['nix-store','--query','--hash',t['package']],text=True).strip()==t['nar_hash']
files=[Path(__file__),P/'obligation-research-browser.mjs',P/'browser-driver.mjs',P/'review-serve.bl',*sorted((P/'dossier').rglob('*.bl')),
       P/'dossier/research-evidence.js',P/'src/formal/review-host.bl',P/'src/formal/presentation.bl']
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();digests={}
for f in files:
 n=str(f.relative_to(R));assert subprocess.check_output(['git','show',commit+':'+n],cwd=R)==f.read_bytes();digests[n]=sha(f)
fixture=Path(tempfile.mkdtemp(prefix='formal-research-browser-',dir=R/'.bl'));runtime=Path(tempfile.mkdtemp(prefix='formal-research-browser-runtime-'))
paths=['evidence/obligation-integration/qualification.json','evidence/obligation-integration/previous-scalar-readers-qualification.json','evidence/obligation-dossier-cases/qualification.json','evidence/obligation-dossier-cases/cases.json','evidence/graph-search-prototype/qualification.json','evidence/graph-search-prototype/observations.json','evidence/graph-choice-prototype/qualification.json','evidence/graph-choice-prototype/observations.json','evidence/choice-extension-model/qualification.json','sdk-pin.json','evidence/scalar-integration/qualification.json','evidence/scalar-integration/records-qualification.json',
       'evidence/scalar-integration/native-comparison.json','evidence/scalar-integration/corpus.json','evidence/scalar-integration/reader-one.json',
       'evidence/scalar-integration/reader-two.json','dossier/formal/research-evidence.bl','dossier/formal/research-view.bl',
       'dossier/research-evidence.js','elements/word-answer-evidence.bl.org',
       'evidence/word-integration/qualification.json','evidence/word-integration/records-qualification.json',
       'evidence/word-integration/native-comparison.json','evidence/word-integration/corpus.json','evidence/word-integration/reader-one.json',
       'evidence/word-integration/reader-two.json','evidence/scalar-integration/word-native.json','evidence/scalar-integration/evidence-packets.json','dossier-local.css','presentation.css',
       'evidence/features.json','evidence/native.json','evidence/advanced.json']
for relative in paths:
 dest=fixture/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(P/relative,dest)
(fixture/'ATLAS.bl.org').write_text('#+title: Controlled source-change browser check\n#+design: forest\n* Inspect the recorded evidence\n#+begin_research_element :id word-answer-evidence\nOwned fixture copied from actual qualified obligation evidence.\n#+end_research_element\n')
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
unit='work-formal-obligation-research-browser-host-'+pin['engine_fingerprint'][:12]
request=[pin['sdk']+'/bin/bl','--cold']
for path in [P/'src',P/'dossier',Path(kit['root'])/'bl-org-dossier/kit',Path(kit['root'])/'codebase-review/kit',Path(kit['root'])/'research-elements/kit']:
 request+=['-p',str(path)]
request+=['run',str(P/'review-serve.bl')]
command=['systemd-run','--user','--quiet','--unit='+unit,'--working-directory='+str(R),'--property=MemoryMax=2G',
 '--property=MemorySwapMax=0','--property=RuntimeMaxSec=600','--property=KillMode=control-group','--property=RemainAfterExit=yes',
 '--setenv=PORT='+str(port),'--setenv=XDG_RUNTIME_DIR='+str(runtime),'--setenv=FORMAL_REVIEW_ROOT='+str(fixture),
 '--setenv=FORMAL_REVIEW_KIT_ROOT='+kit['root'],'--setenv=DOSSIER_OWNER=formal-evidence-browser',
 'env','-u','BEAM_LISP_PATH',*request]
write('source-pin.json',{'code_commit':commit,'source_sha256':digests,'sdk_pin':pin,'kit_state_sha256':sha(P/'evidence/obligation-presentation/kit-state.json')})
write('host-command.json',command);write('fixture-owner.json',{'root':str(fixture),'unit':unit,'retirement_condition':'browser scenario completed or failed; preserve actual snapshots and stop the owned host'})
(E/'memory-before.txt').write_text(subprocess.check_output([R/'scripts/bl-mem'],text=True))
subprocess.run(command,check=True);base='http://127.0.0.1:'+str(port);code=None;started=time.monotonic()
try:
 for _ in range(120):
  try:
   with urllib.request.urlopen(base+'/',timeout=2) as r:
    if r.status==200:break
  except Exception:time.sleep(1)
 else:raise RuntimeError('Owned evidence browser host did not become ready')
 raw=subprocess.check_output(['systemctl','--user','show',unit,'--property=ActiveState,SubState,MainPID,ExecMainStartTimestamp,MemoryMax'],text=True)
 state=dict(x.split('=',1) for x in raw.splitlines());assert state['MainPID']!='0' and state['SubState']=='running';write('live-host.json',state)
 browser=['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no','--working-directory='+str(R),
  '--property=MemoryMax=2G','--property=MemorySwapMax=0','--property=RuntimeMaxSec=360','--property=KillMode=control-group',
  '--setenv=FORMAL_BROWSER_EXECUTABLE='+tools['chromium']['executable'],tools['node']['executable'],str(P/'obligation-research-browser.mjs'),base,str(fixture),str(E)]
 write('browser-command.json',browser)
 with (E/'checks.txt').open('w') as out:code=subprocess.run(browser,stdout=out,stderr=subprocess.STDOUT).returncode
finally:
 # Preserve the live unit's real state before retirement. A disappeared
 # transient unit's default dead/success fields are not a terminal receipt.
 before_stop=subprocess.run(['systemctl','--user','show',unit,
  '--property=ActiveState,SubState,MainPID,Result,ExecMainStatus,ExecMainStartTimestamp,ExecMainExitTimestamp'],
  text=True,capture_output=True)
 write('host-before-stop.json',{'returncode':before_stop.returncode,'state':dict(x.split('=',1) for x in before_stop.stdout.splitlines() if '=' in x)})
 stopped=subprocess.run(['systemctl','--user','stop',unit],check=False)
 (E/'host-journal.txt').write_text(subprocess.check_output(['journalctl','--user','-u',unit,'--no-pager','-n','60'],text=True))
 shutil.rmtree(runtime);shutil.rmtree(fixture)
 write('exit.json',{'exit_code':code,'elapsed_seconds':time.monotonic()-started,'runtime_retired':not runtime.exists(),'fixture_retired':not fixture.exists(),'host_stopped':stopped.returncode==0,'host_stop_exit_code':stopped.returncode})
 assert stopped.returncode==0, 'Owned browser host retirement failed'
assert code==0 and read(E/'audit.json')['passed']
assert all(sha(R/n)==digest for n,digest in digests.items())
print(json.dumps({'status':'browser-save-passed','checks':len(read(E/'audit.json')['checks']),'fixture_retired':True}))
