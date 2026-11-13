"""Rerun the real control mode, then qualify the unchanged SDK and prior gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-graph'


def read(path):
    return json.loads(path.read_text())


pin = read(E / 'sdk-candidate.json')
previous = read(E / 'batch-state.json')
assert previous['status'] == 'failed' and previous['stage'] == 'qualification'
review = read(E / 'before-reader-control-dispatch/review.json')
assert review['sdk_pin'] == pin and review['status'] == 'qualification-rejected'
assert not (E / 'qualification.json').exists()
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
for name, digest in read(E / 'build-linkage.json')['runtime_source_sha256'].items():
    assert hashlib.sha256((R / name).read_bytes()).hexdigest() == digest, name
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
completed = [stage for stage in previous['completed'] if stage != 'managed-reader-controls']
for stage, arguments in [('managed-reader-controls', ['run-managed-graph.py', 'managed-reader-controls']),
                         ('qualification', ['qualify-managed-graph.py'])]:
    command = [sys.executable, str(P / arguments[0]), *arguments[1:]]
    state = {'schema': 'enchant.formal.managed-batch.v1', 'stage': stage, 'status': 'running',
             'recorded_utc': datetime.now(timezone.utc).isoformat(), 'completed': completed,
             'code_commit': commit, 'recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'project_pin_promoted': False, 'command': command,
             'repair': 'third-argument list dispatch; no SDK rebuild or completed reader replay'}
    (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
    code = subprocess.run(command, cwd=R).returncode
    if code == 0 and stage == 'managed-reader-controls':
        try:
            controls = read(E / 'managed-reader-controls.json')
            assert controls['schema'] == 'enchant.formal.managed-graph-reader-controls.v1'
            assert len(controls['controls']) == 10 and all(row['status'] == 'refused' for row in controls['controls'])
        except Exception:
            state.update(status='failed', exit_code=1, reason='actual control-mode calibration failed')
            (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
            raise
    if code:
        state.update(status='failed', exit_code=code)
        (E / 'batch-state.json').write_text(json.dumps(state, indent=2) + '\n')
        raise SystemExit(code)
    completed.append(stage)
(E / 'batch-state.json').write_text(json.dumps(
    {'schema': 'enchant.formal.managed-batch.v1', 'status': 'completed', 'exit_code': 0,
     'completed': completed, 'project_pin_promoted': False,
     'recorded_utc': datetime.now(timezone.utc).isoformat()}, indent=2) + '\n')
