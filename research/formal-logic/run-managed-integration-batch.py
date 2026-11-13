"""Serial post-delegation checks; no SDK selection or live activation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-integration'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
completed = ['inventory']
for stage, arguments in [('adapter', ['run-managed-integration.py', 'adapter']),
                         ('facade', ['run-managed-integration.py', 'facade']),
                         ('qualification', ['qualify-managed-integration.py'])]:
    command = [sys.executable, str(P / arguments[0]), *arguments[1:]]
    state = {'schema': 'enchant.formal.managed-integration-batch.v1', 'status': 'running', 'stage': stage,
             'completed': completed, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
             'code_commit': commit, 'recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'project_pin_promoted': False, 'command': command}
    (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run(command, cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
(E / 'batch-state.json').write_text(json.dumps(
    {'schema': 'enchant.formal.managed-integration-batch.v1', 'status': 'completed', 'completed': completed,
     'exit_code': 0, 'recorded_utc': datetime.now(timezone.utc).isoformat(), 'project_pin_promoted': False}, indent=2) + '\n')
