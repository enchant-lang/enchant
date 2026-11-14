"""Run fixed-artifact gates serially, committing completed evidence between dependencies."""
from pathlib import Path
import json,signal,subprocess,sys
P=Path(__file__).resolve().parent;R=P.parent.parent;E=P/'evidence/obligation-integration'
pin=json.loads((E/'sdk-candidate.json').read_text());fingerprint=pin['engine_fingerprint'][:12]
assert json.loads((E/'build-linkage.json').read_text())['sdk_pin']==pin
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert subprocess.check_output(['git','show',commit+':'+str(Path(__file__).relative_to(R))],cwd=R)==Path(__file__).read_bytes()
completed=[];current=None
stages=['preflight','preflight-controls','focused','word-focused','legacy','regression','native','packets',
 'text-packets','evidence-packets','legacy-evidence-packets','obligation-producer','obligation-reader-1','obligation-reader-2']
def state(status,**extra):
 (E/'artifact-prefix-state.json').write_text(json.dumps({'status':status,'current':current,'completed':completed,
   'sdk_pin':pin,'code_commit':commit,**extra},indent=2)+'\n')
def save():
 subprocess.run(['git','add',str(E.relative_to(R))],cwd=R,check=True)
 if subprocess.run(['git','diff','--cached','--quiet','--',str(E.relative_to(R))],cwd=R).returncode:
  subprocess.run(['git','commit','-m','formal: record obligation SDK '+current+' evidence'],cwd=R,check=True,
    stdout=subprocess.DEVNULL)
def interrupted(signum,frame):raise InterruptedError('artifact prefix interrupted')
signal.signal(signal.SIGTERM,interrupted)
try:
 for current in stages:
  state('running');print('artifact gate:',current,flush=True)
  code=subprocess.run([sys.executable,str(P/'run-obligation-integration-checks.py'),current],cwd=R).returncode
  if code:state('failed',exit_code=code);save();raise SystemExit(code)
  completed.append(current);state('running');save()
 current='prior-scalar-readers';state('running');print('artifact gate:',current,flush=True)
 code=subprocess.run([sys.executable,str(P/'run-obligation-previous-scalar-readers.py')],cwd=R).returncode
 if code:state('failed',exit_code=code);save();raise SystemExit(code)
 completed.append(current);state('gates-completed-awaiting-qualification');save()
finally:
 # Child gate units are peers under systemd. Retire only this exact operation's
 # still-active units on interruption; completed --collect children are absent.
 units=['work-formal-obligation-sdk-'+stage+'-'+fingerprint for stage in stages]
 units+=['work-formal-obligation-previous-scalar-'+stage+'-'+fingerprint for stage in ['one','two','controls']]
 stopped=[]
 for unit in units:
  active=subprocess.run(['systemctl','--user','is-active','--quiet',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
  if active:
   subprocess.run(['systemctl','--user','stop',unit],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True);stopped.append(unit)
 (E/'artifact-prefix-cleanup.json').write_text(json.dumps({'owned_active_children_stopped':stopped},indent=2)+'\n')
print(json.dumps({'status':'gates-completed-awaiting-qualification','completed':completed,'sdk':pin['sdk']}))
