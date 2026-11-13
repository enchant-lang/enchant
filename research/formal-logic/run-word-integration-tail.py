"""Run project regressions and paired native questions serially on the fixed artifact."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration'
pin = json.loads((E / 'sdk-candidate.json').read_text())
assert json.loads((E / 'prefix-state.json').read_text())['status'] == 'passed'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for source in [Path(__file__), P / 'run-word-integration-checks.py']:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = hashlib.sha256(source.read_bytes()).hexdigest()
completed = []
for stage in ('regression', 'native', 'packets'):
    assert json.loads((E / 'sdk-candidate.json').read_text()) == pin
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in digests.items())
    state = {'status': 'running', 'stage': stage, 'completed': completed, 'sdk_pin': pin,
             'code_commit': commit, 'source_sha256': digests, 'project_pin_selected': False}
    (E / 'tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run([sys.executable, str(P / 'run-word-integration-checks.py'), stage], cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='checks-completed', completed=completed, exit_code=0,
             next='Commit actual outputs, then audit the complete qualification before selecting the artifact.')
(E / 'tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'checks-completed', 'completed': completed, 'project_pin_selected': False}))
