"""Serialize regression/native/cold compatibility gates, then actual word capture."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pin = read(E / 'sdk-candidate.json')
assert read(E / 'prefix-state.json')['status'] == 'passed'
terminal = read(E / 'retry-owner-terminal.json')['observation']
assert terminal['MainPID'] == '0' and terminal['ExecMainStatus'] == '0' and terminal['ExecMainExitTimestamp']
assert read(P / 'sdk-pin.json') == read(E / 'baseline-sdk-pin.json')
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
files = [Path(__file__),P / 'run-word-integration-tail.py',P / 'run-word-integration-checks.py',
         P / 'run-word-records.py', P / 'word-corpus.bl']
digests = {}
for path in files:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git','show',commit+':'+name],cwd=R) == path.read_bytes()
    digests[name] = sha(path)
completed = []
for stage,script,args in [('runtime-gates','run-word-integration-tail.py',[]),('word-capture','run-word-records.py',['capture'])]:
    assert all(sha(R / name)==digest for name,digest in digests.items())
    state = {'status':'running','stage':stage,'completed':completed,'sdk_pin':pin,'code_commit':commit,'source_sha256':digests}
    (E / 'rest-state.json').write_text(json.dumps(state,indent=2)+'\n')
    code = subprocess.run([sys.executable,str(P / script),*args],cwd=R).returncode
    if code:
        state.update(status='failed',exit_code=code)
        (E / 'rest-state.json').write_text(json.dumps(state,indent=2)+'\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='captured-awaiting-committed-fresh-reader-inputs',completed=completed,exit_code=0)
(E / 'rest-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({'status':state['status'],'selected':False}))
