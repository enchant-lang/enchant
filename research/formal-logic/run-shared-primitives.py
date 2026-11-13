"""Serial qualification of the shared SDK primitive candidate."""
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
E = P / 'evidence/shared-primitives'
E.mkdir(exist_ok=True)
stage = sys.argv[1]
pin = json.loads((P / 'sdk-pin.json' if stage == 'source-preflight' else E / 'sdk-candidate.json').read_text())
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
names = [str(Path(__file__).relative_to(R))]
project = False
output = None
if stage in ('source-preflight', 'sdk-preflight'):
    names += ['scripts/sdk-preflight', 'scripts/sdk-preflight.bl']
    root = str(R) if stage == 'source-preflight' else pin['source']
    output = E / (stage + '.json')
    request = [str(R / 'scripts/sdk-preflight'), '--sdk', pin['sdk'], '--root', root, '--out', str(output)]
elif stage == 'sdk-preflight-controls':
    names += ['scripts/sdk-preflight', 'scripts/sdk-preflight.bl', 'test/scripts/sdk_preflight.py']
    request = ['python3', str(R / names[-1]), '--sdk', pin['sdk']]
elif stage == 'sdk-focused':
    names += ['test/bl/formal/shared_evaluator_test.bl']
    request = ['test', str(R / names[-1])]
    output = E / 'sdk-traces.json'
elif stage in ('project-focused', 'adapter-integration'):
    project = True
    names += ['research/formal-logic/test/' + name for name in (
        'rational_preflight_test.bl', 'numeric_point_test.bl', 'numeric_execution_trace_test.bl',
        'bounded_point_test.bl', 'term_forest_evaluate_test.bl', 'term_forest_test.bl',
        'graph_reader_test.bl', 'graph_observations_test.bl', 'question_forest_test.bl')]
    request = ['test', *[str(R / name) for name in names[1:]]]
elif stage == 'general-corpus':
    project = True
    names += ['research/formal-logic/term-forest-evaluation-check.bl']
    output = E / 'general-corpus.json'
    request = ['run', str(R / names[-1]), '--', str(output)]
elif stage == 'direct-corpus':
    project = True
    names += ['research/formal-logic/shared-primitives-corpus.bl']
    output = E / 'direct-corpus.json'
    request = ['run', str(R / names[-1]), '--', str(output)]
elif stage == 'transport':
    names += ['research/formal-logic/shared-primitives-transport.bl']
    output = E / 'transport.json'
    request = ['run', str(R / names[-1]), '--', str(output)]
elif stage in ('reader-one', 'reader-two'):
    names += ['research/formal-logic/shared-primitives-reader.bl']
    output = E / (stage + '.json')
    assert (E / 'direct-corpus.json').is_file()
    request = ['run', str(R / names[-1]), '--', str(E / 'direct-corpus.json'), str(output)]
elif stage == 'paired-native-corpus':
    project = True
    names += ['research/formal-logic/graph-consumers-check.bl']
    output = E / 'paired-native-corpus.json'
    request = ['run', str(R / names[-1]), '--', str(output)]
elif stage == 'sdk-regression':
    names += ['test/bl/formal/observation_test.bl', 'test/bl/formal/graph_ops_test.bl',
              'test/bl/formal/graph_context_test.bl', 'test/bl/veritas/graph_ledger_test.bl',
              'test/bl/formal/data_graph_test.bl', 'test/bl/formal/point_test.bl',
              'test/bl/formal/float_points_test.bl']
    request = ['test', *[str(R / name) for name in names[1:]]]
elif stage == 'regression':
    project = True
    previous = json.loads((P / 'evidence/graph-consumers/regression-command.json').read_text())
    names += previous[previous.index('test') + 1:]
    request = ['test', *[str(R / name) for name in names[1:]]]
elif stage == 'facade':
    project = True
    names += ['research/formal-logic/test/' + name for name in ('graph_facade_test.bl', 'facade_test.bl', 'api_test.bl')]
    names += ['test/bl/system/formal_answer_test.bl', 'test/bl/system/formal_oracle_test.bl',
              'test/bl/system/formal_effect_test.bl', 'test/bl/veritas/ledger_test.bl']
    request = ['test', *[str(R / name) for name in names[1:]]]
else:
    raise ValueError(stage)
if project:
    names += [str(path.relative_to(R)) for path in (P / 'src').rglob('*.bl')]
names += [str(path.relative_to(R)) for path in (R / 'priv/lib/formal').rglob('*.bl')]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for name in sorted(set(names)):
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    sources[name] = hashlib.sha256(body).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-shared-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-shared-consumer-'))
ceiling = 3600 if stage == 'paired-native-corpus' else (720 if stage == 'sdk-preflight-controls' else 900)
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime)]
if stage == 'sdk-focused':
    command += ['--setenv=ENCHANT_SHARED_PRIMITIVE_TRACE=' + str(output)]
if stage == 'regression':
    (E / 'regression').mkdir(exist_ok=True)
    command += ['--setenv=ENCHANT_FORMAL_EVIDENCE_ROOT=' + str(E / 'regression')]
if stage not in ('source-preflight', 'sdk-preflight', 'sdk-preflight-controls'):
    command += ['env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
                pin['sdk'] + '/bin/bl', '--cold']
    if project:
        command += ['-p', str(P / 'src')]
command += request
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
print(json.dumps({'stage': stage, 'exit_code': code}), flush=True)
raise SystemExit(code)
