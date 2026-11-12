"""Retain preparation compatibility and actual raw-native project-prototype evidence."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/term-forest'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def committed(commit, name):
    return subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R)


pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
core = 'research/formal-logic/src/formal/term-forest.bl'
test = 'research/formal-logic/test/term_forest_test.bl'
# These first two checks predate launch-time source snapshots. The exact
# before-check commits are retained from the task's committed check batches.
# Compare their actual source bytes, and archive their original runner recipes.
anchors = {'focused': 'd291d5cff5a1650396bbb413f47bbfcf9e3bb306',
           'corpus': '554a7cd2494588ebbf8214f7013af75697dc7f7f'}
stages = {}
for stage in ('focused', 'corpus', 'native', 'sharing'):
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'], stage
    command = read(E / (stage + '-command.json'))
    assert pin['sdk'] + '/bin/bl' in command and '--cold' in command
    assert '--property=MemoryMax=4G' in command and '--property=MemorySwapMax=0' in command
    assert '--property=RuntimeMaxSec=900' in command
    if stage in anchors:
        commit = anchors[stage]
        names = [core, test, 'research/formal-logic/sdk-pin.json',
                 'research/formal-logic/src/formal/native-cases.bl']
        if stage == 'corpus':
            names += ['research/formal-logic/term-forest-check.bl',
                      'research/formal-logic/src/formal/advanced-cases.bl',
                      'research/formal-logic/src/formal/feature-cases.bl']
        sources = {}
        for name in names:
            body = committed(commit, name)
            assert body == (R / name).read_bytes(), (stage, name)
            sources[name] = hashlib.sha256(body).hexdigest()
        recipe = committed(commit, 'research/formal-logic/run-term-forest.py')
        (E / (stage + '-original-recipe.py')).write_bytes(recipe)
        source = {'code_commit': commit, 'source_sha256': sources,
                  'original_recipe_sha256': hashlib.sha256(recipe).hexdigest(),
                  'provenance': 'Exact before-check committed batch; launch-time source snapshots were not yet emitted for this stage.'}
    else:
        source = read(E / (stage + '-source-pin.json'))
        assert source['sdk_pin'] == pin
        for name, digest in source['source_sha256'].items():
            assert hashlib.sha256(committed(source['code_commit'], name)).hexdigest() == digest
        assert source['source_sha256'][core] == sha(R / core)
    stages[stage] = {'exit': result, 'source': source,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
assert '521 passed' in (E / 'focused-checks.txt').read_text()
corpus = read(E / 'corpus.json')
assert len(corpus['rows']) == 187 and corpus['managed-query-calls'] == 0
assert all(row['exact-definitions'] and row['ordered-roots'] and not row['compiler-proof-authority'] for row in corpus['rows'])
native = read(E / 'native.json')
assert len(native['rows']) == len({row['family'] for row in native['rows']}) == 19
assert native['raw-native-scopes'] == 38 and native['managed-query-calls'] == 0
status_counts = Counter()


def check_identity(identity):
    assert identity['sdk'] == pin['sdk']
    artifacts = identity['artifacts']
    assert artifacts['sdk'] == pin['sdk'] and artifacts['worker']['origin'] == 'sdk'
    assert sha(Path(artifacts['worker']['path'])) == identity['worker-sha256'] == artifacts['worker']['sha256']
    if identity['backend'] == 'z3':
        assert artifacts['library']['origin'] == 'sdk'
        assert sha(Path(artifacts['library']['path'])) == identity['library-sha256'] == artifacts['library']['sha256']
    assert artifacts['packaged']['oxiz-version'] == '0.3.4'
    assert artifacts['packaged']['features'] == ['oxiz-core/std', 'oxiz-solver/std']


for row in native['rows']:
    assert row['exact-legacy-definitions'] and len(row['engines']) == 2
    assert {engine['engine'] for engine in row['engines']} == {'z3', 'oxiz'}
    for engine in row['engines']:
        check_identity(engine['identity'])
        assert engine['accepted'] and engine['transport'] == 'raw-compatibility'
        assert engine['independent-replay'] == 'not-run' and engine['certificate'] == 'not-checked'
        assert not engine['compiler-proof-authority']
        if engine['reply']['ok']:
            assert engine['managed-context-invalidated']
        status_counts[(engine['engine'], engine['native-status'])] += 1
sharing = read(E / 'sharing.json')
assert sharing['raw-native-scopes'] == 2 and sharing['managed-query-calls'] == 0
assert sharing['data-graph']['nodes'] == 45 and sharing['data-graph']['expanded-nodes'] == 1572852
assert sharing['canonical-graph-bytes'] == 1349 and sharing['expanded-term-occurrences'] == 131071
assert sharing['checking']['typed-nodes'] == sharing['checking']['scope-states'] == 17
assert sharing['checking']['materialized-components'] == 5
for row in sharing['results']:
    check_identity(row['identity'])
    assert row['status'] == 'sat' and row['root'] is True and row['native-packet-bytes'] == 772
    assert row['managed-context-invalidated'] and row['transport'] == 'raw-compatibility'
timing = {}
for key in ('initial-graph', 'graph-preparation', 'legacy-export'):
    values = [row['timing-ms'][key] for row in corpus['rows']]
    timing[key] = {'total_ms': sum(values), 'median_ms': statistics.median(values), 'maximum_ms': max(values)}
report = {'schema': 'enchant.formal.term-forest-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'availability': 'project-preview',
          'sdk_pin': pin, 'implementation_sha256': sha(R / core), 'stages': stages,
          'focused_assertions': 521, 'exact_preparation_questions': 187,
          'native_families': 19, 'raw_native_scopes': 40, 'managed_query_calls': 0,
          'native_family_status_counts': [{'backend': backend, 'status': status, 'count': count}
                                          for (backend, status), count in sorted(status_counts.items())],
          'sharing': sharing, 'corpus_sha256': sha(E / 'corpus.json'), 'native_sha256': sha(E / 'native.json'),
          'preparation_timings': timing,
          'timing_scope': 'One serial preparation run with initial graph conversion recorded separately. Small-case graph preparation is slower overall; these numbers are not a solver-speed or end-to-end query benchmark.',
          'scope': 'Graph-reference typed preparation, compatibility with existing definitions/root order, scope/provenance controls and actual raw native transport. Research module is not in this SDK, not managed graph-owner admission, and not a proof of typed-forest, BL or compiler preservation.',
          'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'focused': 521, 'questions': 187, 'raw_native_scopes': 40, 'managed_queries': 0}))
