"""Observe the exact live core supervisor, then run one read-only comparison.

Launch this under its own durable service. It starts no BL process while the
core supervisor exists and is active. Failure, changed invocation or incomplete
qualification stops the follow-through; it never edits source or promotes a pin.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
C = P / 'evidence/managed-graph'
E = P / 'evidence/managed-integration'
E.mkdir(exist_ok=True)
unit = 'work-formal-managed-batch-4-resume-20261113.service'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state():
    raw = subprocess.check_output(['systemctl', '--user', 'show', unit,
          '--property=LoadState,ActiveState,SubState,MainPID,InvocationID,Result,ExecMainCode,ExecMainStatus'], text=True)
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def record(status, **extra):
    data = {'schema': 'enchant.formal.managed-after-core.v1', 'status': status,
            'recorded_utc': datetime.now(timezone.utc).isoformat(), 'unit': unit,
            'sdk_pin': pin, 'source_pin': source_pin, 'initial_state': initial,
            'project_pin_promoted': False, **extra}
    (E / 'after-core-state.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps({'status': status, **extra}), flush=True)


pin = read(C / 'sdk-candidate.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
source_pin = {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))}
initial = state()
assert initial['LoadState'] == 'loaded' and initial['ActiveState'] == 'active'
assert initial['SubState'] == 'running' and int(initial['MainPID']) > 0 and initial['InvocationID']
assert not (C / 'qualification.json').exists(), 'Never adopt a pre-existing qualification as a new completion.'
record('waiting', observed_state=initial)
while True:
    observed = state()
    if observed['LoadState'] == 'not-found':
        # A missing transient handle establishes stopped, not passed. The
        # newly generated complete qualification chain below is still required.
        break
    if observed['InvocationID'] != initial['InvocationID']:
        record('failed', reason='core-supervisor-invocation-changed', observed_state=observed)
        raise SystemExit(1)
    if observed['ActiveState'] not in ('active', 'activating', 'deactivating'):
        if not (observed['ActiveState'] == 'inactive' and observed['MainPID'] == '0'
                and observed['Result'] == 'success' and observed['ExecMainCode'] == '1'
                and observed['ExecMainStatus'] == '0'):
            record('failed', reason='core-supervisor-did-not-exit-successfully', observed_state=observed)
            raise SystemExit(1)
        break
    time.sleep(15)

try:
    batch = read(C / 'batch-state.json')
    qualification = read(C / 'qualification.json')
    assert batch['status'] == 'completed' and batch['exit_code'] == 0
    assert batch['completed'][-1] == 'qualification'
    assert qualification['status'] == 'passed' and qualification['sdk_pin'] == pin
    for stage, check in qualification['stages'].items():
        result = read(C / (stage + '-exit.json'))
        assert result == check['exit'] and result['exit_code'] == 0
        assert result['runtime_retired'] and result['consumer_cwd_retired']
    record('running-inventory', terminal_state=observed,
           core_qualification_sha256=sha(C / 'qualification.json'))
    code = subprocess.run([sys.executable, str(P / 'run-managed-integration.py'), 'inventory'], cwd=R).returncode
    record('completed' if code == 0 else 'failed', exit_code=code, terminal_state=observed,
           core_qualification_sha256=sha(C / 'qualification.json'))
    raise SystemExit(code)
except Exception as error:
    record('failed', reason=str(error), terminal_state=observed)
    raise
