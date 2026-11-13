"""Compare the old inventory, then check its explicit-profile SDK delegate.

This does not edit the project or select an SDK. Run serially after the core
qualification. The pre-delegation comparison must precede the source change.
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
C = P / 'evidence/managed-graph'
E = P / 'evidence/managed-integration'
E.mkdir(exist_ok=True)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


stage = sys.argv[1]
assert stage in ('inventory', 'adapter', 'facade')
core = read(C / 'qualification.json')
pin = read(C / 'sdk-candidate.json')
assert core['status'] == 'passed' and core['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
for name, digest in read(C / 'build-linkage.json')['runtime_source_sha256'].items():
    assert sha(R / name) == digest

delegate = 'research/formal-logic/src/formal/question-forest.bl'
before = core['stages']['paired-native-corpus']['source_pin']
if stage == 'inventory':
    # Exact original implementation, not a project alias compared with itself.
    assert sha(R / delegate) == before['source_sha256'][delegate]
    names = ['research/formal-logic/question-inventory-integration.bl']
    output = E / 'inventory.json'
    request = ['run', str(R / names[0]), '--', str(output)]
else:
    comparison = read(E / 'inventory.json')
    assert comparison['exact-inventories'] == 187
    assert comparison['native-exchanges'] == comparison['managed-query-calls'] == 0
    assert sha(R / delegate) != before['source_sha256'][delegate]
    if stage == 'adapter':
        files = ('rational_preflight_test.bl', 'numeric_point_test.bl', 'numeric_execution_trace_test.bl',
                 'bounded_point_test.bl', 'term_forest_evaluate_test.bl', 'term_forest_test.bl',
                 'graph_reader_test.bl', 'graph_observations_test.bl', 'question_forest_test.bl')
        names = ['research/formal-logic/test/' + name for name in files]
    else:
        names = ['research/formal-logic/test/' + name for name in
                 ('graph_facade_test.bl', 'facade_test.bl', 'api_test.bl')]
        names += ['test/bl/system/formal_answer_test.bl', 'test/bl/system/formal_oracle_test.bl',
                  'test/bl/system/formal_effect_test.bl', 'test/bl/veritas/ledger_test.bl']
    output = None
    request = ['test', *[str(R / name) for name in names]]

names += [str(path.relative_to(R)) for path in (P / 'src').rglob('*.bl')]
names += [str(Path(__file__).relative_to(R))]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for name in sorted(set(names)):
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    sources[name] = hashlib.sha256(body).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-managed-integration-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-managed-integration-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-managed-integration-' + stage + '-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', pin['sdk'] + '/bin/bl',
           '--cold', '-p', str(P / 'src'), *request]
write(E / (stage + '-source-pin.json'), {'code_commit': commit, 'source_sha256': sources, 'sdk_pin': pin,
      'core_qualification_sha256': sha(C / 'qualification.json')})
write(E / (stage + '-command.json'), command)
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / (stage + '-exit.json')).unlink(missing_ok=True)
if output:
    output.unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
write(E / (stage + '-exit.json'), {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
      'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists()})
print(json.dumps({'stage': stage, 'exit_code': code}), flush=True)
raise SystemExit(code)
