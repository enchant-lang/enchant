"""Run committed notebook inputs and the real writer serially, before unchanged checking."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/obligation-presentation'
pin = json.loads((P / 'sdk-pin.json').read_text())
qualification = json.loads((P / 'evidence/obligation-integration/qualification.json').read_text())
assert qualification['status'] == 'passed' and qualification['sdk_pin'] == pin
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
paths = [Path(__file__), P / 'run-obligation-presentation.py']
digests = {}
for path in paths:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
completed = []
for stage in ('inputs', 'cells'):
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in digests.items())
    state = {'status': 'running', 'stage': stage, 'completed': completed, 'sdk_pin': pin,
             'code_commit': commit, 'source_sha256': digests}
    (E / 'prefix-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run([sys.executable, str(P / 'run-obligation-presentation.py'), stage], cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'prefix-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='writer-completed-awaiting-independent-check', completed=completed, exit_code=0)
(E / 'prefix-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': state['status'], 'completed': completed}))
