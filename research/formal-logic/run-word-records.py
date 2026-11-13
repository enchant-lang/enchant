"""Capture real records, then reopen packets and a durable ledger in fresh SDK processes."""
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
E = P / 'evidence/word-integration'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

stage, = sys.argv[1:]
assert stage in ('capture', 'reader-one', 'reader-two', 'reader-controls')
pin, baseline = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert read(E / 'focused-exit.json')['exit_code'] == 0
linkage = read(E / 'build-linkage.json')
assert linkage['status'] == 'bound' and linkage['sdk_pin'] == pin
for name, digest in linkage['source_sha256'].items():
    assert sha(R / name) == digest == sha(Path(pin['sdk']) / 'lib/beam_lisp-0.1.0' / name)
script = P / ('word-corpus.bl' if stage == 'capture' else 'word-reader.bl')
corpus = E / 'corpus.json'
output = corpus if stage == 'capture' else E / (stage + '.json')
inputs = [Path(__file__), script, E / 'sdk-candidate.json', E / 'baseline-sdk-pin.json', E / 'build-linkage.json']
if stage != 'capture':
    assert read(E / 'capture-exit.json')['exit_code'] == 0 and read(E / 'capture-exit.json')['postconditions_passed']
    assert sha(corpus) == read(E / 'capture-exit.json')['output_sha256']
    inputs += [corpus, E / 'corpus-ledger.json']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for source in inputs:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = sha(source)
write(stage + '-source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin})
runtime = Path(tempfile.mkdtemp(prefix='formal-word-record-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-word-record-consumer-'))
if stage == 'capture':
    ledger_root = Path(tempfile.mkdtemp(prefix='formal-word-corpus-', dir=R / '.bl'))
    ledger_path = ledger_root / 'ledger'
    write('corpus-ledger.json', {'root': str(ledger_root), 'path': str(ledger_path), 'owner_stage': stage,
                                'retirement_condition': 'both actual fresh readers and controls qualified', 'sdk_pin': pin})
    arguments = [str(output), str(ledger_path)]
else:
    owned = read(E / 'corpus-ledger.json')
    ledger_root, ledger_path = Path(owned['root']), Path(owned['path'])
    assert owned['sdk_pin'] == pin and ledger_root.parent == R / '.bl' and ledger_root.name.startswith('formal-word-corpus-')
    assert ledger_path == ledger_root / 'ledger' and ledger_path.is_dir()
    arguments = [str(corpus), str(output), 'controls' if stage.endswith('controls') else 'read', str(E / 'sdk-candidate.json')]
    if not stage.endswith('controls'):
        arguments.append(str(ledger_path))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-word-' + stage + '-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=1200', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           pin['sdk'] + '/bin/bl', '--cold', 'run', str(script), '--', *arguments]
write(stage + '-command.json', command)
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / (stage + '-exit.json')).unlink(missing_ok=True)
output.unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
exit_data = {'exit_code': code, 'elapsed_seconds': time.monotonic() - started, 'postconditions_passed': False,
      'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists(),
      'output_sha256': sha(output) if output.exists() else None, 'ledger_retained_for_readers': ledger_path.is_dir()}
write(stage + '-exit.json', exit_data)
assert all(sha(R / name) == digest for name, digest in digests.items())
assert code == 0 and output.exists(), stage
result = read(output)
if stage == 'capture':
    assert result['producer-sdk'] == pin['sdk'] and result['producer-descriptor-sha256'] == pin['descriptor_sha256']
    assert len(result['rows']) == 12 and len({row['id'] for row in result['rows']}) == 12
    assert [row['expected'] for row in result['rows']].count('sat') == 8
    assert [row['expected'] for row in result['rows']].count('invalid-point') == 2
    assert [row['expected'] for row in result['rows']].count('solver-claim') == 2
    assert [row['answer-version'] for row in result['rows']].count(3) == 8
    assert result['compiler-proof-authority'] is False and result['checked-native-execution'] is False
else:
    assert result['sdk'] == result['recorded-producer-sdk'] == pin['sdk']
    assert result['sdk-only'] and result['research-import-path'] is False and result['source-payload-execution'] is False
    assert result['solver-exchanges'] == result['oracle-calls'] == 0
    assert result['checked-native-execution'] is False and result['compiler-proof-authority'] is False
    if stage.endswith('controls'):
        assert len(result['controls']) == 15 and all(row['status'] == 'refused' for row in result['controls'])
        assert result['rehashed-invalid-coordinate'] == 'independently-invalid' and result['edited-history'] == 'recorded-only'
    else:
        assert len(result['rows']) == len(result['ledger']) == 12
        assert result['application-atoms-before'] == result['application-atoms-after']
        assert result['ledger-before-packets'] is True
        assert all(row['ledger-envelope'] == 'payload-checked' and row['reopen-normalizer-calls'] == row['lookup-normalizer-calls'] == 1 for row in result['ledger'])
exit_data['postconditions_passed'] = True
write(stage + '-exit.json', exit_data)
print(json.dumps({'stage': stage, 'status': 'passed', 'sdk_pin_selected': False}), flush=True)
