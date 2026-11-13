"""Qualify a declared one-module overlay; never label it a produced SDK."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/retained-question-prototype'
E.mkdir(exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

pin = read(P / 'sdk-pin.json')
assert read(P / 'evidence/numeric-semantics/qualification.json')['sdk_pin'] == pin
assert read(P / 'evidence/numeric-semantics/qualification.json')['status'] == 'passed'
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
module = R / 'priv/lib/formal/retained-question.bl'
sources = [module, P / 'retained-question-check.bl', Path(__file__), P / 'sdk-pin.json']
digests = {}
for path in sources:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'base_sdk_pin': pin,
                          'overlay': ['priv/lib/formal/retained-question.bl'], 'sdk_produced': False})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
runtime = Path(tempfile.mkdtemp(prefix='formal-retained-question-'))
imports = runtime / 'imports'
(imports / 'formal').mkdir(parents=True)
shutil.copyfile(module, imports / 'formal/retained-question.bl')
xdg = runtime / 'xdg'
xdg.mkdir(mode=0o700)
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-retained-question-prototype-check-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(runtime), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=600', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(xdg), 'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           'BEAM_LISP_PATH=' + str(imports), pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports),
           'test', str(P / 'retained-question-check.bl')]
write('command.json', command)
(E / 'qualification.json').unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
write('exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
                    'runtime_retired': not runtime.exists()})
log = (E / 'checks.txt').read_text()
assert code == 0 and '1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log, log[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
write('qualification.json', {
    'schema': 'bl.retained-question-prototype-qualification.v1', 'status': 'passed',
    'recorded_utc': datetime.now(timezone.utc).isoformat(), 'source_pin': read(E / 'source-pin.json'),
    'command_sha256': sha(E / 'command.json'), 'log_sha256': sha(E / 'checks.txt'),
    'exit': read(E / 'exit.json'), 'base_sdk_pin': pin, 'sdk_produced': False,
    'compiler_proof_authority': False,
    'scope': 'Explicit one-module prototype overlay, pure graph composition and complete point meaning; compatibility against the unchanged selected SDK owner on both native backends. This is not integrated retained-request execution or a qualified replacement SDK.'})
print(json.dumps({'status': 'passed', 'sdk_produced': False}))
