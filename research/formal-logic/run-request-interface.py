"""Serial checks for staged portable language request integration.

Launch this driver in a durable systemd supervisor when it may span turns.
It refuses to overlap the existing managed-owner native/reader supervisor.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/request-interface'
E.mkdir(exist_ok=True)
stage = sys.argv[1]
assert stage == 'focused'
active = subprocess.run(['systemctl', '--user', 'show', 'work-formal-managed-qualification-20261113.service',
                         '-p', 'MainPID', '-p', 'SubState'], capture_output=True, text=True, check=True)
state = dict(line.split('=', 1) for line in active.stdout.splitlines() if '=' in line)
assert state.get('MainPID', '0') == '0', 'The managed-owner corpus/reader chain is still running; do not overlap checks.'
pin = json.loads((P / 'evidence/managed-graph/sdk-candidate.json').read_text())
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [Path(__file__), *(P / 'managed-interface').rglob('*.bl')]
digests = {}
for source in sources:
    name = str(source.relative_to(R))
    body = source.read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    digests[name] = hashlib.sha256(body).hexdigest()
cwd = Path(tempfile.mkdtemp(prefix='formal-request-consumer-'))
runtime = Path(tempfile.mkdtemp(prefix='formal-request-runtime-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', pin['sdk'] + '/bin/bl', '--cold',
           '-p', str(P / 'managed-interface'), 'test', str(P / 'managed-interface/test/request_preview_test.bl')]
(E / (stage + '-source-pin.json')).write_text(json.dumps({'code_commit': commit, 'source_sha256': digests,
       'sdk_pin': pin, 'live_project_pin_changed': False}, indent=2) + '\n')
(E / (stage + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / (stage + '-exit.json')).unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as output:
        code = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, cwd=R).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
(E / (stage + '-exit.json')).write_text(json.dumps({'exit_code': code, 'runtime_retired': not runtime.exists(),
       'consumer_cwd_retired': not cwd.exists(), 'elapsed_seconds': time.monotonic() - started}, indent=2) + '\n')
print(json.dumps({'stage': stage, 'exit_code': code}), flush=True)
raise SystemExit(code)
