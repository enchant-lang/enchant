"""Reopen the exact earlier managed records with the new SDK and explicit producer identity."""
from datetime import datetime, timezone
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
D = E / 'previous-readers'
D.mkdir(exist_ok=True)
BASE = P / 'evidence/managed-graph'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

pin = read(E / 'sdk-candidate.json')
parent = read(BASE / 'qualification.json')
producer = parent['sdk_pin']
assert parent['status'] == 'passed'
assert read(E / 'build-linkage.json')['sdk_pin'] == pin
assert read(E / 'focused-exit.json')['exit_code'] == 0
assert read(P / 'sdk-pin.json') == read(E / 'baseline-sdk-pin.json')
for selected in (pin, producer):
    assert sha(Path(selected['sdk']) / 'artifact.json') == selected['descriptor_sha256']
assert read(Path(producer['sdk']) / 'artifact.json')['formalWorker'] == read(Path(pin['sdk']) / 'artifact.json')['formalWorker']
fixture = BASE / 'managed-native-corpus.json'
assert sha(fixture) == parent['artifact_sha256']['managed-native-corpus.json']
producer_path = E / 'previous-producer-sdk-pin.json'
assert read(producer_path) == producer
sources = [Path(__file__), P / 'numeric-previous-reader.bl', fixture, BASE / 'qualification.json',
           E / 'sdk-candidate.json', producer_path]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for source in sources:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = sha(source)
snapshot = {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin, 'recorded_producer_sdk_pin': producer}
results = []
for stage, mode in [('one', 'read'), ('two', 'read'), ('controls', 'controls')]:
    runtime = Path(tempfile.mkdtemp(prefix='formal-word-previous-runtime-'))
    cwd = Path(tempfile.mkdtemp(prefix='formal-word-previous-consumer-'))
    output = D / (stage + '.json')
    output.unlink(missing_ok=True)
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
               '--unit=work-formal-word-previous-' + stage + '-' + pin['engine_fingerprint'][:12],
               '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
               '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
               pin['sdk'] + '/bin/bl', '--cold', 'run', str(P / 'numeric-previous-reader.bl'), '--',
               str(fixture), str(output), mode, str(producer_path)]
    write(D / (stage + '-source-pin.json'), snapshot)
    write(D / (stage + '-command.json'), command)
    (D / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    started = time.monotonic()
    try:
        with (D / (stage + '-checks.txt')).open('w') as stream:
            code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    finally:
        shutil.rmtree(runtime)
        shutil.rmtree(cwd)
    write(D / (stage + '-exit.json'), {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
          'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists()})
    assert code == 0 and output.exists(), stage
    result = read(output)
    assert result['sdk'] == result['checker-sdk'] == pin['sdk']
    assert result['recorded-producer-sdk'] == producer['sdk'] != result['checker-sdk']
    assert result['sdk-only'] and result['research-import-path'] is False and result['source-payload-execution'] is False
    assert result['native-exchanges'] == result['managed-query-calls'] == 0
    assert result['checked-native-execution'] is False and result['compiler-proof-authority'] is False
    assert all(sha(R / name) == digest for name, digest in digests.items())
    results.append(result)
    print(json.dumps({'stage': stage, 'status': 'passed', 'solver_exchanges': 0}), flush=True)
assert results[0]['process'] != results[1]['process'] and results[0]['cwd'] != results[1]['cwd']
assert results[0]['rows'] == results[1]['rows'] == read(BASE / 'managed-reader-one.json')['rows']
assert len(results[0]['rows']) == 187
assert results[0]['replayed-points'] == results[1]['replayed-points'] == parent['saved_replayed_points'] == 52
assert len(results[2]['controls']) == 11 and all(row['status'] == 'refused' for row in results[2]['controls'])
assert results[2]['rehashed-invalid-coordinate'] == 'independently-invalid'
write(E / 'previous-readers-qualification.json', {
    'schema': 'bl.word-sdk-previous-records-qualification.v1', 'status': 'passed',
    'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'source_pin': snapshot,
    'recorded_producer_sdk_pin': producer, 'questions': 187, 'fresh_sdk_only_readers': 2,
    'replayed_points_per_reader': 52, 'refusal_controls': 11, 'solver_exchanges': 0,
    'artifact_sha256': {str(path.relative_to(D)): sha(path) for path in sorted(D.glob('*')) if path.is_file()},
    'checked_native_execution': False, 'compiler_proof_authority': False,
    'scope': 'The exact earlier managed graph records and saved points remain readable with explicit producer/checker identities. Recorded native status/history is not authenticated; no universal compatibility or implementation theorem is claimed.'})
print(json.dumps({'status': 'passed', 'questions': 187, 'fresh_readers': 2, 'points_per_reader': 52}))
