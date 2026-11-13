"""One capped, exact-SDK check at a time for scalar resource enforcement."""
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
E = P / 'evidence/bounded-point'
E.mkdir(exist_ok=True)
stage = sys.argv[1]
pin = json.loads((P / 'sdk-pin.json').read_text())
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
if stage == 'focused':
    files = ['bounded_point_test.bl', 'term_forest_evaluate_test.bl', 'term_forest_test.bl',
             'graph_reader_test.bl', 'graph_observations_test.bl', 'question_forest_test.bl']
    request = ['test', *[str(P / 'test' / name) for name in files]]
elif stage == 'example':
    files = []
    request = ['run', str(P / 'bounded-point-example.bl'), '--', str(E / 'example.json')]
else:
    raise ValueError(stage)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [*(P / 'src').rglob('*.bl'), *[P / 'test' / name for name in files],
           P / 'sdk-pin.json', Path(__file__)]
if stage == 'example':
    sources.append(P / 'bounded-point-example.bl')
digests = {}
for source in sorted(sources):
    name = str(source.relative_to(R))
    body = source.read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    digests[name] = hashlib.sha256(body).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-budget-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-budget-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--expand-environment=no', '--working-directory=' + str(cwd),
           '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime),
           'env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           str(Path(pin['sdk']) / 'bin/bl'), '--cold', '-p', str(P / 'src'), *request]
(E / (stage + '-exit.json')).unlink(missing_ok=True)
if stage == 'example':
    (E / 'example.json').unlink(missing_ok=True)
(E / (stage + '-source-pin.json')).write_text(json.dumps(
    {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin}, indent=2) + '\n')
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
