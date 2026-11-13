"""Check cold packet vocabulary, then the owner/legacy/ledger tail, serially."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration-prototype'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in [Path(__file__), P / 'run-word-packet-prototype.py', P / 'run-word-prototype-tail.py']:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
completed = []
for stage, recipe in [('packets', 'run-word-packet-prototype.py'), ('owner-legacy-ledger', 'run-word-prototype-tail.py')]:
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in digests.items())
    state = {'status': 'running', 'stage': stage, 'completed': completed, 'code_commit': commit,
             'source_sha256': digests, 'sdk_produced': False}
    (E / 'schema-tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run([sys.executable, str(P / recipe)], cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'schema-tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='checks-completed', completed=completed, exit_code=0)
(E / 'schema-tail-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'checks-completed', 'completed': completed, 'sdk_produced': False}))
