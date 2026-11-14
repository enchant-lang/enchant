"""One actual capped gate on the fixed scalar-text/evidence SDK candidate."""
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
E = P / 'evidence/scalar-integration'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

stage, = sys.argv[1:]
pin, baseline = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
sdk = Path(pin['sdk'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
linkage = read(E / 'build-linkage.json')
assert linkage['status'] == 'bound' and linkage['sdk_pin'] == pin
for name, digest in linkage['source_sha256'].items():
    assert sha(R / name) == digest == sha(sdk / 'lib/beam_lisp-0.1.0' / name)
files, project, ceiling = [], False, 1200
if stage == 'word-focused':
    files = ['test/bl/formal/managed_graph_test.bl', 'test/bl/formal/retained_configuration_test.bl',
             'research/formal-logic/retained-question-check.bl', 'research/formal-logic/retained-composition-check.bl',
             'test/bl/formal/request_test.bl', 'research/formal-logic/retained-answer-check.bl',
             'research/formal-logic/retained-request-check.bl',
             'test/bl/formal/word_graph_test.bl', 'test/bl/formal/word_request_test.bl',
             'test/bl/formal/word_owner_test.bl', 'test/bl/formal/word_owner_admission_test.bl',
             'test/bl/formal/request_lookup_test.bl']
elif stage == 'focused':
    files = ['test/bl/formal/scalar_text_graph_test.bl', 'test/bl/formal/scalar_text_resource_test.bl',
             'test/bl/formal/scalar_text_interface_test.bl', 'test/bl/formal/scalar_text_owner_test.bl',
             'test/bl/formal/finite_word_certificate_test.bl', 'test/bl/formal/request_evidence_test.bl',
             'test/bl/formal/evidence_effect_test.bl', 'test/bl/formal/evidence_oracle_test.bl']
elif stage == 'legacy':
    files = ['test/bl/formal/shared_evaluator_test.bl', 'test/bl/formal/graph_admission_test.bl',
             'test/bl/formal/graph_keys_test.bl', 'test/bl/formal/graph_ops_test.bl', 'test/bl/formal/graph_context_test.bl']
elif stage == 'regression':
    project = True
    old = read(P / 'evidence/numeric-semantics/regression-command.json')
    files = [str(Path(name).relative_to(R)) if Path(name).is_absolute() else name for name in old[old.index('test') + 1:]]
    assert len(files) == 31
elif stage == 'packets':
    files = ['research/formal-logic/word-packet-reader.bl']
elif stage == 'text-packets':
    files = ['research/formal-logic/scalar-packet-reader.bl']
elif stage == 'evidence-packets':
    files = ['research/formal-logic/evidence-packet-reader.bl']
elif stage == 'native':
    project, ceiling = True, 3600
    files = ['research/formal-logic/graph-consumers-check.bl']
elif stage in ('preflight', 'preflight-controls'):
    pass
else:
    raise ValueError(stage)
names = list(linkage['source_changes']) + files + [str(Path(__file__).relative_to(R))]
if project:
    names += [str(path.relative_to(R)) for path in sorted((P / 'src').rglob('*.bl'))]
if stage in ('word-focused', 'packets'):
    names += ['research/formal-logic/evidence/retained-request/corpus.json']
if stage == 'text-packets':
    names += [str((E / 'text-native.json').relative_to(R))]
if stage == 'evidence-packets':
    names += [str((E / 'bundle-corpus.json').relative_to(R))]
names += (['scripts/sdk-preflight', 'scripts/sdk-preflight.bl'] if stage == 'preflight'
          else ['test/scripts/sdk_preflight.py'] if stage == 'preflight-controls' else [])
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for name in sorted(set(names)):
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    digests[name] = sha(R / name)
runtime = Path(tempfile.mkdtemp(prefix='formal-scalar-gate-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-scalar-gate-consumer-'))
if files:
    request = [str(sdk / 'bin/bl'), '--cold'] + (['-p', str(P / 'src')] if project else [])
    if stage == 'packets':
        request += ['run', str(R / files[0]), '--', str(P / 'evidence/retained-request/corpus.json'), str(E / 'packets.json')]
    elif stage in ('text-packets', 'evidence-packets'):
        corpus = E / ('text-native.json' if stage == 'text-packets' else 'bundle-corpus.json')
        request += ['run', str(R / files[0]), '--', str(corpus), str(E / (stage + '.json'))]
    elif stage == 'native':
        request += ['run', str(R / files[0]), '--', str(E / 'native.json')]
    else:
        request += ['test', *[str(R / name) for name in files]]
elif stage == 'preflight':
    request = [sys.executable, str(R / 'scripts/sdk-preflight'), '--sdk', str(sdk), '--root', pin['source'],
               '--out', str(E / 'source-preflight.json')]
else:
    request = [sys.executable, str(R / 'test/scripts/sdk_preflight.py'), '--sdk', str(sdk)]
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-scalar-sdk-' + stage + '-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime)]
if stage == 'regression':
    (E / 'regression').mkdir(exist_ok=True)
    command += ['--setenv=ENCHANT_FORMAL_EVIDENCE_ROOT=' + str(E / 'regression')]
command += ['--setenv=INDEXED_LEDGER_CORPUS=' + str(P / 'evidence/retained-request/corpus.json')]
if stage == 'focused':
    command += ['--setenv=SCALAR_OWNER_OUTPUT=' + str(E / 'text-native.json'),
                '--setenv=TEXT_NATIVE_OUTPUT=' + str(E / 'term-native.json'),
                '--setenv=WORD_EXHAUSTION_NATIVE_OUTPUT=' + str(E / 'word-native.json'),
                '--setenv=EVIDENCE_BUNDLE_OUTPUT=' + str(E / 'bundle-corpus.json')]
command += ['env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', *request]
write(stage + '-source-pin.json', {'code_commit': commit, 'sdk_pin': pin, 'source_sha256': digests})
write(stage + '-command.json', command)
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / (stage + '-exit.json')).unlink(missing_ok=True)
if stage == 'native':
    (E / 'native.json').unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
assert all(sha(R / name) == digest for name, digest in digests.items())
process_code, green = code, None
if files and stage not in ('native', 'packets', 'text-packets', 'evidence-packets'):
    log = (E / (stage + '-checks.txt')).read_text()
    green = f'{len(files)} file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
    if not green and code == 0:
        code = 1
write(stage + '-exit.json', {'exit_code': code, 'process_exit_code': process_code, 'complete_green_test_summary': green,
      'elapsed_seconds': time.monotonic() - started, 'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists()})
print(json.dumps({'stage': stage, 'exit_code': code}), flush=True)
raise SystemExit(code)
