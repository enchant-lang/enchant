"""Queue one independent language-interface check after the live core chain.

This supervisor polls the actual service, not a lock or progress file. A
failed/missing prerequisite is not treated as completion. No BL starts here
until the retained core supervisor exits normally with all remaining receipts.
"""
import json
from pathlib import Path
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/request-interface'
C = P / 'evidence/managed-graph'
unit = 'work-formal-managed-qualification-20261113.service'
pin = json.loads((E / 'sdk-pin.json').read_text())
while True:
    result = subprocess.check_output(['systemctl', '--user', 'show', unit, '-p', 'LoadState', '-p', 'ActiveState',
                  '-p', 'SubState', '-p', 'MainPID', '-p', 'Result', '-p', 'ExecMainCode', '-p', 'ExecMainStatus'], text=True)
    state = dict(line.split('=', 1) for line in result.splitlines() if '=' in line)
    assert state['LoadState'] == 'loaded', 'Original supervisor is missing; no check was started.'
    if state['MainPID'] == '0':
        assert state['SubState'] == 'exited' and state['Result'] == 'success'
        assert state['ExecMainCode'] == '1' and state['ExecMainStatus'] == '0'
        break
    time.sleep(3)
assert json.loads((C / 'sdk-candidate.json').read_text()) == pin
for stage in ('paired-native-corpus', 'managed-native-corpus', 'managed-reader-one', 'managed-reader-two', 'managed-reader-controls'):
    receipt = json.loads((C / (stage + '-exit.json')).read_text())
    assert receipt['exit_code'] == 0 and receipt['runtime_retired'] and receipt['consumer_cwd_retired']
assert json.loads((C / 'durable-supervisor-state.json').read_text())['status'] == 'completed'
(E / 'prerequisite-supervisor.json').write_text(json.dumps({'unit': unit, 'terminal': state,
    'sdk_pin': pin, 'scope': 'Actual terminal service and all check cleanup receipts; no overlap with its BL jobs.'}, indent=2) + '\n')
raise SystemExit(subprocess.run(['python3', str(P / 'run-request-interface.py'), 'focused'], cwd=R).returncode)
