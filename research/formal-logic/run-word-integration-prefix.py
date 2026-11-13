"""Serial initial SDK gates, with the owner retained until its actual exit is observed."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration'
pin = json.loads((E / 'sdk-candidate.json').read_text())
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for source in [Path(__file__), P / 'run-word-integration-checks.py']:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
completed = []
for stage in ['preflight', 'preflight-controls', 'focused', 'legacy']:
    assert json.loads((E / 'sdk-candidate.json').read_text()) == pin
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in sources.items())
    state = {'status': 'running', 'stage': stage, 'completed': completed, 'sdk_pin': pin,
             'source_sha256': sources, 'code_commit': commit, 'project_pin_selected': False}
    (E / 'prefix-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run([sys.executable, str(P / 'run-word-integration-checks.py'), stage], cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'prefix-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='passed', completed=completed, exit_code=0)
(E / 'prefix-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'prefix-passed', 'completed': completed, 'project_pin_selected': False}))
