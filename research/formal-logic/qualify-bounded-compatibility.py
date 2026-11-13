"""Fresh general-profile agreement; budget-profile correctness is separate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/bounded-point'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
source = read(E / 'compatibility-source-pin.json')
assert source['sdk_pin'] == pin
for name, digest in source['source_sha256'].items():
    body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
    assert hashlib.sha256(body).hexdigest() == digest == sha(R / name)
result = read(E / 'compatibility-exit.json')
assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired']
command = read(E / 'compatibility-command.json')
assert all(flag in command for flag in (pin['sdk'] + '/bin/bl', '--cold', '--property=MemoryMax=4G',
           '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=900', '--property=KillMode=control-group'))
corpus = read(E / 'compatibility.json')
assert corpus['managed-query-calls'] == 0 and corpus['native-execution'] == 'not-invoked'
assert corpus['compiler-proof-authority'] is False and len(corpus['rows']) == 187
baseline_path = P / 'evidence/term-forest-evaluation/corpus.json'
baseline = {row['id']: row for row in read(baseline_path)['rows']}
assert set(baseline) == {row['id'] for row in corpus['rows']}
matches = 0
differences = []
root_values = 0
for row in corpus['rows']:
    assert row['compiler-proof-authority'] is False
    assert [point['mode'] for point in row['points']] == ['absent', 'zero', 'alternate', 'ill-sorted']
    for point in row['points']:
        assert point['exact-values'] is True and point['checking']['argument-traversal'] == 'graph-references'
        root_values += point['roots']
    old = baseline[row['id']]
    def semantics(item):
        return {'data-reference': item['data-reference'], 'variables': item['variables'],
                'points': [{key: point[key] for key in ('mode', 'roots', 'unavailable', 'value-reference', 'checking')}
                           for point in item['points']]}
    if semantics(row) == semantics(old):
        matches += 1
    else:
        differences.append(row['id'])
assert matches == 187, differences
report = {'schema': 'enchant.formal.bounded-point-general-compatibility.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'source_pin': source,
          'exit': result, 'command_sha256': sha(E / 'compatibility-command.json'),
          'log_sha256': sha(E / 'compatibility-checks.txt'), 'corpus_sha256': sha(E / 'compatibility.json'),
          'questions': 187, 'point_maps': 748, 'exact_root_values': root_values,
          'historical_baseline_sha256': sha(baseline_path), 'historical_exact_case_matches': matches,
          'managed_query_calls': 0, 'compiler_proof_authority': False,
          'scope': 'The general graph point profile still agrees exactly with the qualified SDK on all requested roots at four deterministic assignments for each saved question, and retains the previous general-profile value fingerprints and counters. This checks the shared traversal across existing theories; it does not add budget policies for those theories or prove universal evaluator/implementation/ compiler preservation.'}
(E / 'compatibility-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'questions': 187, 'point_maps': 748,
                  'exact_root_values': root_values, 'historical_exact_case_matches': matches}))
