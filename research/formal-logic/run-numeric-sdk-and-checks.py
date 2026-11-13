"""Prepare one numeric SDK, then run its serial gates in a durable owner.

Completion here means gates executed, never project selection or a theorem.
The final source/artifact/result audit remains separate.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
names = [Path(__file__), P / 'build-numeric-sdk.py', P / 'run-numeric-batch.py',
         P / 'run-numeric-checks.py', P / 'run-numeric-semantics.py']
sources = {}
for source in names:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    sources[name] = hashlib.sha256(source.read_bytes()).hexdigest()
completed = []
for stage, script in [('sdk-preparation', 'build-numeric-sdk.py'), ('candidate-gates', 'run-numeric-batch.py')]:
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in sources.items())
    command = [sys.executable, str(P / script)]
    state = {'schema': 'bl.numeric-sdk-preparation-and-checks.v1', 'status': 'running',
             'stage': stage, 'completed': completed, 'code_commit': commit, 'source_sha256': sources,
             'recorded_utc': datetime.now(timezone.utc).isoformat(), 'command': command,
             'project_pin_selected': False, 'compiler_proof_authority': False}
    (E / 'preparation-and-checks-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run(command, cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'preparation-and-checks-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
state.update(status='checks-completed', completed=completed, exit_code=0,
             next='Audit the actual candidate gates before selecting this SDK or updating the live host.')
(E / 'preparation-and-checks-state.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps({'status': 'checks-completed', 'project_pin_selected': False}), flush=True)
