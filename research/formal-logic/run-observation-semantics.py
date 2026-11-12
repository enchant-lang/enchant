"""Serial checks against the one immutable shared-observation candidate."""
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
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
stage = sys.argv[1]
names = ['priv/lib/formal/query.bl', 'priv/lib/formal/value.bl', str(Path(__file__).relative_to(R))]
project = False
if stage == 'sdk-focused':
    names += ['test/bl/formal/observation_test.bl']
    request = ['test', str(R / names[-1])]
elif stage == 'native':
    names += ['test/bl/formal/observation_native_test.bl']
    request = ['test', str(R / names[-1])]
elif stage == 'graph-focused':
    project = True
    names += ['research/formal-logic/src/formal/term-forest.bl',
              'research/formal-logic/src/formal/term-forest-evaluate.bl',
              'research/formal-logic/src/formal/question-forest.bl',
              'research/formal-logic/src/formal/graph-reader.bl',
              'research/formal-logic/src/formal/graph-observations.bl',
              'research/formal-logic/test/term_forest_evaluate_test.bl',
              'research/formal-logic/test/graph_observations_test.bl',
              'research/formal-logic/test/question_forest_test.bl',
              'research/formal-logic/test/graph_reader_test.bl']
    request = ['test', *[str(R / name) for name in names[-4:]]]
elif stage == 'observation-corpus':
    project = True
    names += ['research/formal-logic/src/formal/term-forest.bl',
              'research/formal-logic/src/formal/term-forest-evaluate.bl',
              'research/formal-logic/src/formal/question-forest.bl',
              'research/formal-logic/src/formal/graph-reader.bl',
              'research/formal-logic/src/formal/graph-observations.bl',
              'research/formal-logic/src/formal/point-fixtures.bl',
              'research/formal-logic/src/formal/advanced-cases.bl',
              'research/formal-logic/src/formal/feature-cases.bl',
              'research/formal-logic/src/formal/native-cases.bl',
              'research/formal-logic/graph-observations-check.bl']
    request = ['run', str(R / names[-1]), '--', str(E / 'observation-corpus.json')]
elif stage == 'paired-native-corpus':
    project = True
    names += ['research/formal-logic/graph-consumers-check.bl',
              'research/formal-logic/src/formal/advanced-cases.bl',
              'research/formal-logic/src/formal/feature-cases.bl',
              'research/formal-logic/src/formal/native-cases.bl']
    request = ['run', str(P / 'graph-consumers-check.bl'), '--', str(E / 'paired-native-corpus.json')]
elif stage == 'sdk-regression':
    names += ['test/bl/formal/graph_ops_test.bl', 'test/bl/formal/graph_context_test.bl',
              'test/bl/veritas/graph_ledger_test.bl', 'test/bl/formal/data_graph_test.bl',
              'test/bl/formal/point_test.bl', 'test/bl/formal/float_points_test.bl']
    request = ['test', *[str(R / name) for name in names[-6:]]]
elif stage == 'live-regression':
    names += ['priv/lib/live/app.bl', 'test/bl/live/app_test.bl']
    request = ['test', str(R / names[-1])]
elif stage == 'regression':
    project = True
    previous = json.loads((P / 'evidence/graph-consumers/regression-command.json').read_text())
    files = previous[previous.index('test') + 1:]
    names += files
    request = ['test', *[str(R / name) for name in files]]
else:
    raise ValueError(stage)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for name in names:
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    sources[name] = hashlib.sha256(body).hexdigest()
for name in ['priv/lib/formal/query.bl', 'priv/lib/formal/value.bl']:
    assert sources[name] == hashlib.sha256((Path(pin['source']) / name).read_bytes()).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-observation-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-observation-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=' + ('3600' if stage == 'paired-native-corpus' else '900'), '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime)]
if stage == 'native':
    command += ['--setenv=ENCHANT_OBSERVATION_RECEIPT=' + str(E / 'native.json')]
if stage == 'regression':
    (E / 'regression').mkdir(exist_ok=True)
    command += ['--setenv=ENCHANT_FORMAL_EVIDENCE_ROOT=' + str(E / 'regression')]
command += ['env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
            str(Path(pin['sdk']) / 'bin/bl'), '--cold']
if project:
    command += ['-p', str(P / 'src')]
command += request
(E / (stage + '-exit.json')).unlink(missing_ok=True)
output_names = {'native': 'native.json', 'observation-corpus': 'observation-corpus.json',
                'paired-native-corpus': 'paired-native-corpus.json'}
if stage in output_names:
    (E / output_names[stage]).unlink(missing_ok=True)
(E / (stage + '-source-pin.json')).write_text(json.dumps({'code_commit': commit, 'source_sha256': sources, 'sdk_pin': pin}, indent=2) + '\n')
(E / (stage + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
try:
    started = time.monotonic()
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
(E / (stage + '-exit.json')).write_text(json.dumps({'exit_code': code, 'runtime_retired': not runtime.exists(),
                                                 'consumer_cwd_retired': not cwd.exists(),
                                                 'elapsed_seconds': time.monotonic() - started}, indent=2) + '\n')
print(json.dumps({'stage': stage, 'exit_code': code}))
raise SystemExit(code)
