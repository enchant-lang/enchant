"""Durable serial input validation and real document result writing.

Stops after actual results are written. Review/commit those results before the
separate unchanged check and host/browser activation; never synthesize results.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-presentation'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
completed = []
for stage in ('inputs', 'cells'):
    command = [sys.executable, str(P / 'run-managed-presentation.py'), stage]
    state = {'schema': 'enchant.formal.managed-dossier-writing.v1', 'status': 'running', 'stage': stage,
             'completed': completed, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
             'code_commit': commit, 'recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'command': command, 'host_activation': False}
    (E / 'writing-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run(command, cwd=R).returncode
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'writing-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
log = (E / 'dossier-cells-checks.txt').read_text()
assert '88 cells, 0 cell errors' in log
(E / 'writing-state.json').write_text(json.dumps(
    {'schema': 'enchant.formal.managed-dossier-writing.v1', 'status': 'completed', 'completed': completed,
     'exit_code': 0, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
     'next': 'Review and commit actual results, then run unchanged checking before activation.',
     'host_activation': False}, indent=2) + '\n')
