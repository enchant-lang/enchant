"""Recheck preceding SDK graph records in fresh numeric-SDK-only consumers."""
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
E = P / 'evidence/numeric-semantics'
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
producer = read(E / 'baseline/sdk-pin.json')
qualification = read(E / 'qualification.json')
parent = read(BASE / 'qualification.json')
assert qualification['status'] == parent['status'] == 'passed'
assert qualification['sdk_pin'] == pin and qualification['baseline_sdk_pin'] == parent['sdk_pin'] == producer
for selected in (pin, producer):
    assert sha(Path(selected['sdk']) / 'artifact.json') == selected['descriptor_sha256']
old_metadata, new_metadata = [read(Path(selected['sdk']) / 'artifact.json') for selected in (producer, pin)]
assert old_metadata['formalWorker'] == new_metadata['formalWorker']
fixture = BASE / 'managed-native-corpus.json'
assert sha(fixture) == parent['artifact_sha256']['managed-native-corpus.json']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [Path(__file__), P / 'numeric-previous-reader.bl', fixture, BASE / 'qualification.json',
           E / 'qualification.json', E / 'baseline/sdk-pin.json', E / 'sdk-candidate.json']
digests = {}
for source in sources:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = sha(source)
snapshot = {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin, 'recorded_producer_sdk_pin': producer}
reports = []
for stage, mode in [('one', 'read'), ('two', 'read'), ('controls', 'controls')]:
    runtime = Path(tempfile.mkdtemp(prefix='formal-numeric-previous-runtime-'))
    cwd = Path(tempfile.mkdtemp(prefix='formal-numeric-previous-consumer-'))
    output = D / (stage + '.json')
    output.unlink(missing_ok=True)
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
               '--unit=work-formal-numeric-previous-' + stage + '-' + pin['engine_fingerprint'][:12],
               '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
               '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
               pin['sdk'] + '/bin/bl', '--cold', 'run', str(P / 'numeric-previous-reader.bl'), '--',
               str(fixture), str(output), mode, str(E / 'baseline/sdk-pin.json')]
    write(D / (stage + '-source-pin.json'), snapshot)
    write(D / (stage + '-command.json'), command)
    (D / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    started = time.monotonic()
    try:
        with (D / (stage + '-checks.txt')).open('w') as stream:
            code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
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
    reports.append(result)
    assert all(sha(R / name) == digest for name, digest in digests.items())
    print(json.dumps({'stage': stage, 'exit_code': code, 'native_exchanges': 0}), flush=True)
assert reports[0]['process'] != reports[1]['process'] and reports[0]['cwd'] != reports[1]['cwd']
assert reports[0]['rows'] == reports[1]['rows'] == read(BASE / 'managed-reader-one.json')['rows']
assert len(reports[0]['rows']) == 187 and reports[0]['replayed-points'] == reports[1]['replayed-points'] == parent['saved_replayed_points']
controls = reports[2]
assert controls['positive']['status'] == 'accepted' and controls['rehashed-invalid-coordinate'] == 'independently-invalid'
assert len(controls['controls']) == 11 and all(row['status'] == 'refused' for row in controls['controls'])
report = {'schema': 'bl.numeric-previous-records-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
          'recorded_producer_sdk_pin': producer, 'source_pin': snapshot,
          'questions': 187, 'fresh_sdk_only_readers': 2, 'replayed_points_per_reader': reports[0]['replayed-points'],
          'refusal_controls': 11, 'native_exchanges': 0, 'managed_query_calls': 0,
          'artifact_sha256': {str(path.relative_to(D)): sha(path) for path in sorted(D.glob('*')) if path.is_file()},
          'checked_native_execution': False, 'compiler_proof_authority': False,
          'scope': 'Exact preceding managed graph records, mathematical value references and saved point results remain readable in fresh SDK-only consumers of the numeric SDK. Recorded producer identity is pinned separately from the checker; neither authenticates historical native execution. This is not a universal format or implementation correspondence theorem.'}
write(E / 'previous-readers-qualification.json', report)
print(json.dumps({'status': 'passed', 'questions': 187, 'fresh_readers': 2,
                  'replayed_points_per_reader': reports[0]['replayed-points'], 'refusal_controls': 11, 'native_exchanges': 0}))
