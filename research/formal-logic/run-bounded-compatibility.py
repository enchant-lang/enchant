"""Recheck the general profile after sharing its traversal with budgeted points."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/bounded-point'
pin = json.loads((P / 'sdk-pin.json').read_text())
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [*(P / 'src').rglob('*.bl'), P / 'term-forest-evaluation-check.bl', P / 'sdk-pin.json', Path(__file__)]
digests = {}
for source in sorted(sources):
    name = str(source.relative_to(R))
    body = source.read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    digests[name] = hashlib.sha256(body).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-budget-compatibility-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-budget-compatibility-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--expand-environment=no', '--working-directory=' + str(cwd),
           '--property=MemoryMax=4G', '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=900',
           '--property=KillMode=control-group', '--setenv=XDG_RUNTIME_DIR=' + str(runtime),
           'env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(P / 'src'),
           'run', str(P / 'term-forest-evaluation-check.bl'), '--', str(E / 'compatibility.json')]
for name in ('compatibility.json', 'compatibility-exit.json'):
    (E / name).unlink(missing_ok=True)
(E / 'compatibility-source-pin.json').write_text(json.dumps(
    {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin}, indent=2) + '\n')
(E / 'compatibility-command.json').write_text(json.dumps(command, indent=2) + '\n')
(E / 'compatibility-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
started = time.monotonic()
try:
    with (E / 'compatibility-checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
(E / 'compatibility-exit.json').write_text(json.dumps(
    {'exit_code': code, 'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists(),
     'elapsed_seconds': time.monotonic() - started}, indent=2) + '\n')
print(json.dumps({'stage': 'compatibility', 'exit_code': code}))
raise SystemExit(code)
