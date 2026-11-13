"""Wait for the existing owner, then audit and check the separate arithmetic model.

This owner starts no duplicate SDK or corpus, and never selects a project SDK.
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
E = P / 'evidence/numeric-semantics'
unit, = sys.argv[1:]
assert unit == 'work-formal-numeric-sdk2-regression-native-20261113.service'
pin = json.loads((E / 'sdk-candidate.json').read_text())
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
paths = [Path(__file__), P / 'qualify-numeric-semantics.py', P / 'run-floor-modulus-model.py',
         P / 'metatheory/FloorModulus.lean',
         *sorted((P / 'metatheory/floor-modulus-controls').glob('*.lean'))]
digests = {}
for path in paths:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
state = {'schema': 'bl.numeric-postcheck-owner.v1', 'status': 'waiting-for-original-owner',
         'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin, 'dependency': unit,
         'project_pin_selected': False, 'compiler_proof_authority': False}


def record(**fields):
    state.update(fields, recorded_utc=datetime.now(timezone.utc).isoformat())
    (E / 'postchecks-state.json').write_text(json.dumps(state, indent=2) + '\n')


def unchanged():
    assert json.loads((E / 'sdk-candidate.json').read_text()) == pin
    assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in digests.items())


try:
    while True:
        unchanged()
        raw = subprocess.check_output(['systemctl', '--user', 'show', unit, '-p', 'ActiveState',
            '-p', 'SubState', '-p', 'MainPID', '-p', 'Result', '-p', 'ExecMainCode',
            '-p', 'ExecMainStatus', '-p', 'ExecMainExitTimestamp', '-p', 'InvocationID'], text=True)
        actual = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
        record(dependency_state=actual)
        if actual['SubState'] == 'exited' and actual['MainPID'] == '0':
            assert actual['Result'] == 'success' and actual['ExecMainStatus'] == '0'
            assert actual['ExecMainExitTimestamp'], 'Require actual completion, not an absent-unit stub.'
            break
        assert actual['ActiveState'] == 'active' and actual['SubState'] == 'running' and actual['MainPID'] != '0', actual
        time.sleep(15)
    batch = json.loads((E / 'batch-state.json').read_text())
    assert batch['status'] == 'checks-completed' and batch['sdk_pin'] == pin
    for stage, script in [('qualification', 'qualify-numeric-semantics.py'),
                          ('floor-modulus-model', 'run-floor-modulus-model.py')]:
        unchanged()
        command = [sys.executable, str(P / script)]
        record(status='running', stage=stage, command=command)
        started = time.monotonic()
        with (E / (stage + '-owner-checks.txt')).open('w') as stream:
            code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
        record(stage_exit_code=code, stage_elapsed_seconds=time.monotonic() - started)
        if code:
            raise subprocess.CalledProcessError(code, command)
    record(status='completed', next='Review exact qualification and model outputs before SDK selection and executed dossier refresh.')
except BaseException as error:
    record(status='failed', error=str(error))
    raise
