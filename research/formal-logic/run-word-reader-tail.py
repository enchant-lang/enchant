"""Run current word, preceding retained and earlier managed consumers in order."""
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
assert read(P / 'sdk-pin.json') == read(E / 'baseline-sdk-pin.json')
assert read(E / 'capture-exit.json')['postconditions_passed']
assert read(E / 'capture-exit.json')['exit_code'] == 0
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
files = [Path(__file__), P / 'run-word-record-readers.py', P / 'run-word-records.py', P / 'word-reader.bl',
         P / 'run-word-prior-retained-readers.py', P / 'prior-retained-reader.bl',
         P / 'run-word-previous-readers.py', P / 'numeric-previous-reader.bl',
         P / 'qualify-word-records.py', E / 'corpus.json', E / 'corpus-ledger.json']
digests = {}
for path in files:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git','show',commit+':'+name],cwd=R) == path.read_bytes()
    digests[name] = sha(path)
completed = []
for stage, script in [('word-readers','run-word-record-readers.py'),
                      ('prior-retained-readers','run-word-prior-retained-readers.py'),
                      ('earlier-managed-readers','run-word-previous-readers.py'),
                      ('word-record-qualification','qualify-word-records.py')]:
    assert all(sha(R / name)==digest for name,digest in digests.items())
    state = {'status':'running','stage':stage,'completed':completed,'sdk_pin':pin,'code_commit':commit,'source_sha256':digests}
    (E / 'reader-tail-state.json').write_text(json.dumps(state,indent=2)+'\n')
    code = subprocess.run([sys.executable,str(P / script)],cwd=R).returncode
    if code:
        state.update(status='failed',exit_code=code)
        (E / 'reader-tail-state.json').write_text(json.dumps(state,indent=2)+'\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='passed',completed=completed,exit_code=0)
(E / 'reader-tail-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps({'status':'readers-passed','selected':False}))
