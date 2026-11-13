"""Numeric admission/evaluation, actual SDK call controls and broad compatibility."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-point'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
qualified = read(P / 'evidence/observation-semantics/qualification.json')
assert qualified['status'] == 'passed' and qualified['sdk_pin'] == pin
sdk_sources = {}
for name in ('priv/lib/formal/term.bl', 'priv/lib/formal/evaluate.bl', 'priv/lib/formal/data-graph.bl'):
    assert sha(R / name) == sha(Path(pin['source']) / name)
    sdk_sources[name] = sha(R / name)
stages = {}
for stage in ('focused', 'trace', 'example', 'compatibility'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        # The stage dispatcher gained additional stages after the first run;
        # actual commands and committed launch versions remain bound below.
        if name != 'research/formal-logic/run-numeric-point.py' or stage == 'trace':
            assert sha(R / name) == digest, name
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired']
    command = read(E / (stage + '-command.json'))
    assert all(flag in command for flag in (pin['sdk'] + '/bin/bl', '--cold',
               '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group'))
    stages[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
counts = {'rational-preflight': 2783, 'numeric-point': 425, 'bounded-point': 345,
          'term-forest-evaluate': 107, 'term-forest': 521, 'graph-reader': 24,
          'graph-observations': 102, 'question-forest': 71}
log = (E / 'focused-checks.txt').read_text()
for name, count in counts.items():
    assert f'formal.{name}-test  {count} passed' in log
assert '8 file(s) passed, 0 failed, 0 incoherent' in log
trace_log = (E / 'trace-checks.txt').read_text()
assert 'formal.numeric-execution-trace-test  34 passed' in trace_log
assert '1 file(s) passed, 0 failed, 0 incoherent' in trace_log
trace = read(E / 'trace.json')
assert trace['compiler-proof-authority'] is False
expected = {'normalizer-direct': ('rational', 1), 'normalizer-admission-denied': ('rational', 0),
            'normalizer-admitted': ('rational', 2), 'addition-direct': ('radd', 1),
            'addition-denied': ('radd', 0), 'addition-admitted': ('radd', 1),
            'multiplication-direct': ('rmul', 1), 'multiplication-denied': ('rmul', 0),
            'multiplication-admitted': ('rmul', 1), 'whole-normalization-direct': ('rational', 3),
            'whole-normalization-admitted': ('rational', 7), 'inactive-branch-admission': ('rational', 2)}
assert len(trace['events']) == len(expected)
for event in trace['events']:
    assert (event['function'], event['calls']) == expected[event['label']] and event['arity'] == 2
    target = 'Term' if event['function'] == 'rational' else 'Evaluate'
    assert event['module'] == 'Elixir.BeamLisp.Ns.Body.Formal.' + target
example = read(E / 'example.json')
result = example['result']
assert result['evaluated']['profile'] == 'bl/bounded-numeric-point-preview-v1'
assert result['evaluated']['phase'] == 'evaluation' and result['evaluated']['status'] == 'incomplete'
assert result['evaluated']['resources']['rational-primitive-calls'] == 4
assert result['evaluated']['resources']['charged-work-units'] == 123377
assert result['evaluated']['admission']['charged-work-units'] == 108
assert result['evaluated']['resources']['refusals'][0]['reason'] == {
    'kind': 'resource-limit', 'metric': 'component-bits', 'required': 52, 'limit': 32}
assert result['admission-refused']['phase'] == 'admission'
assert result['admission-refused']['admission']['charged-work-units'] == 0
assert result['admission-refused']['admission']['constructor-execution'] == 'not-run'
assert result['admission-refused']['resources']['sdk-calls'] == 0
assert result['admission-refused']['data-reference'] == result['evaluated']['data-reference']
assert result['complete']['values'] == [{'formal/real': [1, 2]}]
assert result['decided']['values'] == [False] and result['decided']['status'] == 'complete'
for value in result.values():
    assert value['native-calls'] == 0 and value['compiler-proof-authority'] is False
    assert value['assertion-replay'] == 'not-run'
corpus = read(E / 'compatibility.json')
assert corpus['managed-query-calls'] == 0 and corpus['native-execution'] == 'not-invoked'
assert corpus['compiler-proof-authority'] is False and len(corpus['rows']) == 187
baseline_path = P / 'evidence/bounded-point/compatibility.json'
baseline = {row['id']: row for row in read(baseline_path)['rows']}
assert set(baseline) == {row['id'] for row in corpus['rows']}
root_values = 0
for row in corpus['rows']:
    assert row['compiler-proof-authority'] is False and row['data-reference'] == baseline[row['id']]['data-reference']
    assert [point['mode'] for point in row['points']] == ['absent', 'zero', 'alternate', 'ill-sorted']
    for i, point in enumerate(row['points']):
        assert point['exact-values'] and point['checking']['argument-traversal'] == 'graph-references'
        root_values += point['roots']
        for key in ('mode', 'roots', 'unavailable', 'value-reference', 'checking'):
            assert point[key] == baseline[row['id']]['points'][i][key], (row['id'], key)
assert root_values == 6300
report = {'schema': 'enchant.formal.numeric-point-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'sdk_source_sha256': sdk_sources,
          'profile': 'bl/bounded-numeric-point-preview-v1', 'availability': 'project-preview',
          'assertion_executions': sum(counts.values()) + 34, 'assertions_by_file': {**counts, 'numeric-execution-trace': 34},
          'stages': stages, 'trace_sha256': sha(E / 'trace.json'), 'trace_events': trace['events'],
          'example_sha256': sha(E / 'example.json'), 'general_profile': {'questions': 187, 'point_maps': 748,
          'exact_root_values': root_values, 'historical_exact_case_matches': 187,
          'historical_baseline_sha256': sha(baseline_path), 'corpus_sha256': sha(E / 'compatibility.json')},
          'compiler_proof_authority': False,
          'scope': 'Fresh Bool/Int/Real graph admission with separately reserved literal normalization, private concrete rational forecasts and request charges, phase-specific incompleteness, demanded-node sharing and SDK semantic agreement. Actual BEAM call-count controls observe skipped normalizers/arithmetic and current repeated input checks. General-profile value fingerprints/counters remain identical across the full saved corpus. Other value families, ordinary SDK/managed-owner policy and assertion replay, universal cost/totality and implementation/compiler preservation remain open.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'assertion_executions': report['assertion_executions'],
                  'trace_events': len(trace['events']), 'general_profile_questions': 187}))
