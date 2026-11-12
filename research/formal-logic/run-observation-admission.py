"""Serial source and SDK-only durable-consumer gates for the observation SDK."""
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
E = P / 'evidence/observation-semantics'
pin = json.loads((E / 'sdk-candidate.json').read_text())
sdk = Path(pin['sdk'])
assert hashlib.sha256((sdk / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
stage = sys.argv[1]
names = [str(Path(__file__).relative_to(R))]
output = None
if stage == 'preflight':
    names += ['scripts/sdk-preflight', 'scripts/sdk-preflight.bl']
    output = E / 'source-preflight.json'
    request = [str(R / 'scripts/sdk-preflight'), '--sdk', str(sdk), '--root', pin['source'], '--out', str(output)]
elif stage == 'preflight-controls':
    names += ['scripts/sdk-preflight', 'scripts/sdk-preflight.bl', 'test/scripts/sdk_preflight.py']
    request = ['python3', str(R / names[-1]), '--sdk', str(sdk)]
elif stage in ('writer', 'consumer-one', 'consumer-two'):
    script = 'graph-ledger-writer.bl' if stage == 'writer' else 'graph-ledger-consumer.bl'
    names += ['research/formal-logic/' + script]
    output = E / (stage + '.json')
    store = E / 'durable-ledger'
    if stage == 'writer':
        assert not store.exists() and not Path(str(store) + '.blobs').exists(), 'writer needs a fresh owned store'
    else:
        assert store.is_dir() and json.loads((E / 'writer-exit.json').read_text())['exit_code'] == 0
    request = ['env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
               str(sdk / 'bin/bl'), '--cold', 'run', str(P / script), '--', str(store), str(output)]
else:
    raise ValueError(stage)

commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for name in names:
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    sources[name] = hashlib.sha256(body).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-observation-admission-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-observation-admission-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=' + ('720' if stage == 'preflight-controls' else '900'),
           '--property=KillMode=control-group', '--setenv=XDG_RUNTIME_DIR=' + str(runtime), *request]
(E / (stage + '-exit.json')).unlink(missing_ok=True)
if output:
    output.unlink(missing_ok=True)
(E / (stage + '-source-pin.json')).write_text(json.dumps(
    {'code_commit': commit, 'source_sha256': sources, 'sdk_pin': pin}, indent=2) + '\n')
(E / (stage + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
(E / (stage + '-exit.json')).write_text(json.dumps(
    {'exit_code': code, 'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists(),
     'elapsed_seconds': time.monotonic() - started}, indent=2) + '\n')
print(json.dumps({'stage': stage, 'exit_code': code}))
raise SystemExit(code)
