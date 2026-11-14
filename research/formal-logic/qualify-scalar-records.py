"""Audit actual fresh packet/ledger readers and retire only their generated store."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/scalar-integration'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(E / 'sdk-candidate.json')
assert read(P / 'sdk-pin.json') == read(E / 'baseline-sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
checks = {}
for stage in ('capture', 'reader-one', 'reader-two', 'reader-controls'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        assert sha(R / name) == digest
        assert hashlib.sha256(subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['postconditions_passed']
    assert result['runtime_retired'] and result['consumer_cwd_retired'] and result['ledger_retained_for_readers']
    output = E / ('corpus.json' if stage == 'capture' else stage + '.json')
    assert sha(output) == result['output_sha256']
    command = read(E / (stage + '-command.json'))
    assert pin['sdk'] + '/bin/bl' in command and '--cold' in command and '-p' not in command
    assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=1200', '--property=KillMode=control-group', '--expand-environment=no'))
    checks[stage] = {'source_pin': source, 'exit': result, 'output_sha256': sha(output),
                     'command_sha256': sha(E / (stage + '-command.json')), 'log_sha256': sha(E / (stage + '-checks.txt'))}
corpus = read(E / 'corpus.json')
assert corpus['producer-sdk'] == pin['sdk'] and corpus['producer-descriptor-sha256'] == pin['descriptor_sha256']
assert len(corpus['rows']) == 20 and len({row['id'] for row in corpus['rows']}) == 20
one, two, controls = [read(E / (stage + '.json')) for stage in ('reader-one', 'reader-two', 'reader-controls')]
assert one['process'] != two['process'] and one['cwd'] != two['cwd']
assert one['rows'] == two['rows'] and one['ledger'] == two['ledger']
assert len(one['rows']) == len(one['ledger']) == 20
assert sum(row['answer-version'] == 3 for row in one['rows']) == 12
assert sum(row['verdict'] == 'sat' for row in one['rows']) == 14
assert sum(row['verdict'] == 'invalid-point' for row in one['rows']) == 4
assert sum(row['verdict'] == 'solver-claim' for row in one['rows']) == 2
assert len(controls['controls']) == 15 and all(row['status'] == 'refused' for row in controls['controls'])
assert controls['rehashed-invalid-coordinate'] == 'independently-invalid' and controls['edited-history'] == 'recorded-only'
extra=controls['scalar-controls']
assert extra['word-only-downgrade']=='refused' and len(extra['invalid-text-points'])==3
assert all(r['verdict']=='invalid-point' for r in extra['invalid-text-points'])
for result in (one, two, controls):
    assert result['sdk'] == result['recorded-producer-sdk'] == pin['sdk']
    assert result['sdk-only'] and result['research-import-path'] is False and result['source-payload-execution'] is False
    assert result['solver-exchanges'] == result['oracle-calls'] == 0
    assert result['checked-native-execution'] is False and result['compiler-proof-authority'] is False
for result in (one, two):
    assert result['application-atoms-before'] == result['application-atoms-after']
    assert result['ledger-before-packets'] is True
    assert all(row['reopen-normalizer-calls'] == row['lookup-normalizer-calls'] == 1 for row in result['ledger'])
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
owned = read(E / 'corpus-ledger.json')
root, ledger = Path(owned['root']), Path(owned['path'])
assert owned['sdk_pin'] == pin and root.parent == R / '.bl' and root.name.startswith('formal-scalar-corpus-')
assert not root.is_symlink() and ledger == root / 'ledger' and ledger.is_dir() and not ledger.is_symlink()
files = {str(path.relative_to(root)): sha(path) for path in root.rglob('*') if path.is_file()}
assert files
retirement_path = E / 'corpus-ledger-retirement.json'
retirement = {'root': str(root), 'ledger': str(ledger), 'files_sha256_before_retirement': files,
              'condition_satisfied': 'two actual fresh SDK-only packet and durable-ledger readers plus fifteen common refusals and four text controls passed',
              'retired': False, 'recorded_utc': datetime.now(timezone.utc).isoformat()}
retirement_path.write_text(json.dumps(retirement, indent=2) + '\n')
shutil.rmtree(root)
retirement['retired'] = not root.exists()
assert retirement['retired']
retirement_path.write_text(json.dumps(retirement, indent=2) + '\n')
report = {'schema': 'bl.scalar-request-records-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'records': 20,
          'retained_v3_records': 12, 'fresh_or_supplied_v2_records': 8, 'fresh_sdk_only_readers': 2,
          'ledger_rows_per_reader': 20, 'normalizer_calls_per_selected_lookup': 1, 'ledger_before_packets': True, 'refusal_controls': 16, 'independently_invalid_text_controls': 3, 'solver_exchanges': 0, 'oracle_calls': 0,
          'checks': checks, 'reader_rows': one['rows'], 'ledger_retirement_sha256': sha(retirement_path),
          'compiler_proof_authority': False, 'checked_native_execution': False,
          'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'scope': 'Actual retained/fresh/supplied portable answers and durable ledger rows reopened in two fresh SDK-only processes with solver calls denied. Full subject and point replay, unfamiliar shared metadata, exact version distinctions and independent tamper controls are checked. History, artifact labels, storage authenticity and native execution remain recorded rather than authenticated.'}
(E / 'records-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'records': 20, 'fresh_readers': 2, 'ledger_rows_per_reader': 20, 'normalizer_calls_per_selected_lookup': 1, 'ledger_before_packets': True, 'controls': 15, 'ledger_retired': True}))
