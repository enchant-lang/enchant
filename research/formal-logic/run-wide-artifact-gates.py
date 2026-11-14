"""Run one candidate's gates serially; retain real terminal states before cleanup.

The enclosing service owns the whole sequence. Children have PartOf= that owner,
individual memory/deadline caps, and RemainAfterExit until their state is saved.
No build, SDK selection or retry is performed here.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, signal, subprocess, sys, time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/wide-integration'
owner, *stages = sys.argv[1:]
allowed = ['preflight', 'pure', 'narrow', 'compatibility', 'legacy', 'regression',
           'native', 'reader-one', 'reader-two', 'word-packets', 'text-packets',
           'proof-packets', 'obligation-packets']
assert owner.startswith('work-formal-wide-') and owner.endswith('.service')
assert stages and len(stages) == len(set(stages)) and all(stage in allowed for stage in stages)
pin = json.loads((E / 'sdk-candidate.json').read_text())
assert json.loads((E / 'build-linkage.json').read_text())['sdk_pin'] == pin
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
inputs = [Path(__file__), P / 'run-wide-integration-checks.py']
digests = {}
for path in inputs:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
completed, current, child = [], None, None

def read_state(unit):
    raw = subprocess.check_output(['systemctl', '--user', 'show', unit,
        '--property=LoadState,ActiveState,SubState,MainPID,ExecMainPID,Result,ExecMainCode,ExecMainStatus,ExecMainStartTimestamp,ExecMainExitTimestamp,InvocationID'], text=True)
    return dict(line.split('=', 1) for line in raw.splitlines())

assert read_state(owner)['MainPID'] == str(os.getpid()), 'Require the actual enclosing service owner.'
def record(status, **extra):
    (E / 'artifact-prefix-state.json').write_text(json.dumps({
        'schema': 'bl.wide-artifact-gates.v1', 'status': status,
        'owner': owner, 'current': current, 'child': child, 'completed': completed,
        'sdk_pin': pin, 'code_commit': commit, 'source_sha256': digests,
        'recorded_utc': datetime.now(timezone.utc).isoformat(), **extra}, indent=2) + '\n')

def save():
    path = str(E.relative_to(R))
    subprocess.run(['git', 'add', path], cwd=R, check=True)
    if subprocess.run(['git', 'diff', '--cached', '--quiet', '--', path], cwd=R).returncode:
        subprocess.run(['git', 'commit', '-qm', 'formal: retain wide SDK ' + str(current) + ' gate evidence'], cwd=R, check=True)

def interrupted(signum, frame):
    raise InterruptedError('wide artifact gates interrupted')

signal.signal(signal.SIGTERM, interrupted)
try:
    for current in stages:
        assert json.loads((E / 'sdk-candidate.json').read_text()) == pin
        assert all(hashlib.sha256((R / name).read_bytes()).hexdigest() == digest for name, digest in digests.items())
        directory = E / current
        assert not (directory / 'qualification.json').exists(), 'Do not repeat a qualified gate.'
        child = 'work-formal-wide-' + current + '-' + pin['engine_fingerprint'][:12] + '.service'
        assert read_state(child)['LoadState'] == 'not-found', 'Do not reuse another live or retained unit.'
        ceiling = 21720 if current == 'native' else 7320 if current.startswith('reader-') else 3720
        command = ['systemd-run', '--user', '--quiet', '--unit=' + child,
            '--property=RemainAfterExit=yes', '--property=PartOf=' + owner,
            '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
            '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
            '--working-directory=' + str(R), sys.executable,
            str(P / 'run-wide-integration-checks.py'), current]
        record('starting', command=command)
        print('wide SDK gate:', current, flush=True)
        subprocess.run(command, cwd=R, check=True)
        while True:
            actual = read_state(child)
            record('running', child_state=actual)
            if actual['SubState'] in ('exited', 'failed', 'dead') and actual['MainPID'] == '0':
                assert actual['ExecMainExitTimestamp'], actual
                break
            assert actual['ActiveState'] in ('active', 'activating'), actual
            time.sleep(5)
        directory.mkdir(exist_ok=True)
        (directory / 'owner-command.json').write_text(json.dumps(command, indent=2) + '\n')
        (directory / 'owner-terminal.json').write_text(json.dumps({'unit': child, 'state': actual}, indent=2) + '\n')
        (directory / 'owner-journal.txt').write_text(subprocess.check_output(
            ['journalctl', '--user', '-u', child, '--no-pager', '-o', 'short-iso'], text=True))
        subprocess.run(['systemctl', '--user', 'stop', child], check=True)
        child = None
        assert actual['SubState'] == 'exited' and actual['Result'] == 'success' and actual['ExecMainStatus'] == '0', actual
        q = json.loads((directory / 'qualification.json').read_text())
        assert q['status'] == 'passed' and q['sdk_pin'] == pin
        completed.append(current)
        record('gate-completed'); save()
    record('gates-completed-awaiting-qualification'); save()
except BaseException as error:
    record('failed', error=str(error))
    if child:
        actual = read_state(child)
        record('failed', error=str(error), child_before_cleanup=actual)
        subprocess.run(['systemctl', '--user', 'stop', child], check=True)
    save()
    raise
print(json.dumps({'status': 'gates-completed-awaiting-qualification', 'completed': completed}))
