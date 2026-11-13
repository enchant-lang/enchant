"""Run actual owner, compatibility and indexed-ledger projection gates serially."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration-prototype'
pin = json.loads((P / 'sdk-pin.json').read_text())
pure = json.loads((E / 'pure/qualification.json').read_text())
assert pure['status'] == 'passed' and pure['base_sdk_pin'] == pin
for name, digest in pure['source_pin']['source_sha256'].items():
    assert hashlib.sha256((R / name).read_bytes()).hexdigest() == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
paths = [Path(__file__), P / 'run-word-integration-prototype.py']
digests = {}
for path in paths:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
completed = []
for stage in ('owners', 'legacy', 'ledger'):
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in digests.items())
    state = {'status': 'running', 'stage': stage, 'completed': completed, 'base_sdk_pin': pin,
             'code_commit': commit, 'source_sha256': digests, 'sdk_produced': False}
    (E / 'tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run([sys.executable, str(P / 'run-word-integration-prototype.py'), stage], cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='checks-completed', completed=completed, exit_code=0)
(E / 'tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'checks-completed', 'completed': completed, 'sdk_produced': False}))
