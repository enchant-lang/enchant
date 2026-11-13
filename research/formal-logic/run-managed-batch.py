"""One durable, serial SDK qualification batch; no project/live promotion.

Launch under a retained systemd supervisor, not a turn-scoped shell session.
Each substantive build/check has its own cap and must terminate before the
next starts. Any failure stops the chain and preserves its actual evidence.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-graph'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
steps = [('source-preflight', ['run-managed-graph.py', 'source-preflight']),
         ('sdk-build', ['build-managed-graph-sdk.py']),
         ('build-linkage', ['record-managed-graph-build.py'])]
steps += [(stage, ['run-managed-graph.py', stage]) for stage in (
    'sdk-preflight', 'sdk-focused', 'format-focused', 'profile-sorts', 'key-probe',
    'sdk-preflight-controls', 'sdk-regression', 'project-focused', 'facade', 'regression',
    'paired-native-corpus', 'managed-native-corpus', 'managed-reader-one', 'managed-reader-two',
    'managed-reader-controls', 'request-ledger-write', 'request-ledger-reader-one',
    'request-ledger-reader-two', 'request-ledger-controls')]
steps += [('qualification', ['qualify-managed-graph.py'])]
completed = []
for stage, arguments in steps:
    command = [sys.executable, str(P / arguments[0]), *arguments[1:]]
    state = {'schema': 'enchant.formal.managed-batch.v1', 'stage': stage, 'status': 'running',
             'recorded_utc': datetime.now(timezone.utc).isoformat(), 'completed': completed,
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
    {'schema': 'enchant.formal.managed-batch.v1', 'status': 'completed', 'exit_code': 0,
     'completed': completed, 'project_pin_promoted': False,
     'recorded_utc': datetime.now(timezone.utc).isoformat()}, indent=2) + '\n')
