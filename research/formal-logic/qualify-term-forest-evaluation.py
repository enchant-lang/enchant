"""Qualify the project graph evaluator without granting replay/proof authority."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/term-forest-evaluation'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
stages = {}
for stage in ('focused', 'corpus', 'sharing'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        # Recipes can grow between stages; checked implementation/fixtures cannot.
        if name != 'research/formal-logic/run-term-forest-evaluation.py':
            assert sha(R / name) == digest, (stage, name)
    result = read(E / (stage + '-exit.json'))
    assert result == {'exit_code': 0, 'runtime_retired': True}
    command = read(E / (stage + '-command.json'))
    for required in (pin['sdk'] + '/bin/bl', '--cold', '--property=MemoryMax=4G',
                     '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=900',
                     '--property=KillMode=control-group'):
        assert required in command
    stages[stage] = {'source': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
assert '92 passed' in (E / 'focused-checks.txt').read_text()
corpus = read(E / 'corpus.json')
assert len(corpus['rows']) == 187
assert corpus['managed-query-calls'] == 0 and corpus['native-execution'] == 'not-invoked'
assert corpus['compiler-proof-authority'] is False
comparisons = 0
unavailable = 0
timing = {'graph-evaluation': 0, 'legacy-evaluation': 0}
for row in corpus['rows']:
    assert row['compiler-proof-authority'] is False
    assert [p['mode'] for p in row['points']] == ['absent', 'zero', 'alternate', 'ill-sorted']
    for point in row['points']:
        assert point['exact-values'] is True
        assert point['checking']['argument-traversal'] == 'graph-references'
        assert 0 <= point['checking']['evaluated-nodes'] <= point['checking']['typed-nodes']
        assert point['value-reference']['profile'] == 'bl/public-data-graph-v1'
        assert len(point['value-reference']['sha256']) == 64
        comparisons += point['roots']
        unavailable += point['unavailable']
        for key in timing:
            timing[key] += point['timing-ms'][key]
report = {'schema': 'enchant.formal.term-forest-evaluation-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'availability': 'project-preview',
          'sdk_pin': pin, 'stages': stages, 'focused_assertions': 92,
          'questions': 187, 'point_maps': 748, 'exact_root_comparisons': comparisons,
          'unavailable_root_values': unavailable, 'managed_query_calls': 0,
          'native_execution': 'not-invoked', 'timing_totals_ms': timing,
          'timing_scope': 'Serial observations include graph admission/preparation for every point, while legacy evaluation reads already materialized terms. These are not solver-speed or matched end-to-end benchmarks.',
          'sharing_fixture': {'term_occurrences': 131071, 'typed_nodes': 17,
                              'evaluated_nodes': 17, 'requested_roots': 2},
          'semantics': 'Selected SDK primitive evaluation, with identical ITE/AND/OR demand and eager implication. Unsupported or unassigned mathematics stays incomplete.',
          'scope': 'Checked compatibility fixtures, not exhaustive evaluator equivalence. Project module is outside the immutable SDK and managed question/reply/observation/ledger path. No quantifier interpretation, independently checked native model certificate, or compiler preservation proof is added.',
          'compiler_proof_authority': False, 'corpus_sha256': sha(E / 'corpus.json')}
sharing = read(E / 'sharing.json')
assert sharing['managed-query-calls'] == 0 and sharing['native-execution'] == 'not-invoked'
assert sharing['term-occurrences'] == 131071
assert sharing['data-graph']['nodes'] == 45 and sharing['data-graph']['expanded-nodes'] == 1572852
assert sharing['canonical-graph-bytes'] == 1349
assert sharing['result']['values'] == [True, True]
assert sharing['result']['checking']['typed-nodes'] == sharing['result']['checking']['evaluated-nodes'] == 17
assert sharing['compiler-proof-authority'] is False and sharing['result']['compiler-proof-authority'] is False
report['sharing'] = sharing
report['sharing_sha256'] = sha(E / 'sharing.json')
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'focused': 92, 'questions': 187,
                  'point_maps': 748, 'exact_root_comparisons': comparisons}))
