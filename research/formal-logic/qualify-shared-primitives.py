"""Qualify the SDK candidate; integration adapters/presentation are later gates."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/shared-primitives'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(E / 'sdk-candidate.json')
recipe = str(Path(__file__).relative_to(R))
code_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
assert subprocess.check_output(['git', 'show', code_commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
link = read(E / 'build-linkage.json')
assert link['sdk_pin'] == pin and len(link['runtime_source_sha256']) == 691
metadata = read(Path(pin['sdk']) / 'artifact.json')
for name, digest in link['runtime_source_sha256'].items():
    assert sha(R / name) == sha(Path(pin['source']) / name) == sha(Path(metadata['source']) / name) == digest
    assert sha(Path(pin['sdk']) / 'lib/beam_lisp-0.1.0' / name) == digest
assert set(link['source_changes']) == {'priv/lib/formal/evaluate.bl', 'priv/lib/formal/graph-terms.bl',
                                      'priv/lib/formal/resources/integer.bl', 'priv/lib/formal/resources/rational.bl'}
baseline = read(E / 'baseline-sdk-pin.json')
parent = read(P / 'evidence/observation-semantics/qualification.json')
assert baseline == parent['sdk_pin'] and parent['status'] == 'passed'
oldmeta = read(Path(baseline['sdk']) / 'artifact.json')
for name in ('compiler', 'dependencies', 'platform', 'formalWorker'):
    assert metadata[name] == oldmeta[name] == link['unchanged_components'][name]
assert parent['retained_compiler_floor']['files'] == 141
assert parent['retained_compiler_floor']['compiler'] == metadata['compiler']
stages = {}
required = ('source-preflight', 'sdk-preflight', 'sdk-preflight-controls', 'sdk-focused', 'project-focused',
            'sdk-regression', 'regression', 'facade', 'transport', 'direct-corpus',
            'reader-one', 'reader-two', 'paired-native-corpus')
for stage in required:
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == (baseline if stage == 'source-preflight' else pin)
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        if name != 'research/formal-logic/run-shared-primitives.py':
            assert sha(R / name) == digest, name
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired'], stage
    command = read(E / (stage + '-command.json'))
    ceiling = 3600 if stage == 'paired-native-corpus' else (720 if stage == 'sdk-preflight-controls' else 900)
    assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group'))
    if stage not in ('source-preflight', 'sdk-preflight', 'sdk-preflight-controls'):
        assert pin['sdk'] + '/bin/bl' in command and '--cold' in command
    if stage in ('sdk-focused', 'sdk-regression', 'transport', 'reader-one', 'reader-two'):
        assert '-p' not in command, stage
    stages[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')), 'log_sha256': sha(E / (stage + '-checks.txt'))}
runs = {}
for stage, files in (('sdk-focused', 1), ('project-focused', 9), ('sdk-regression', 7), ('regression', 31), ('facade', 7)):
    log = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
    assert len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in log
    runs[stage] = rows
assert runs['sdk-focused'] == {'formal.shared-evaluator-test': 130}
assert sum(runs['project-focused'].values()) == 4412
assert sum(runs['sdk-regression'].values()) == 899
assert sum(runs['regression'].values()) == 8141 and sum(runs['facade'].values()) == 585
traces = read(E / 'sdk-traces.json')
events = {event['label']: event for event in traces['events']}
assert len(events) == len(traces['events']) and traces['compiler-proof-authority'] is False
for name, calls in {'tree': 3, 'legacy-numeric': 7, 'direct-numeric': 3, 'direct-general': 3,
                    'shared-literal': 2, 'admission-denied': 0, 'primitive-denied': 2, 'variable': 1}.items():
    assert events[name]['normalizer-calls'] == calls
assert events['tree-dispatch']['private-dispatch-calls'] == events['graph-dispatch']['private-dispatch-calls'] == 1
assert events['language-privacy']['sdk-declaration'] == 'private'
assert events['language-privacy']['qualified-refusals'] == 2
assert events['language-privacy']['native-bridge-exported'] is True
transport = read(E / 'transport.json')
assert all(transport[name] is True for name in ('exact-graph-bytes', 'both-zero-signs', 'invalid-utf8-bytes'))
assert transport['compiler-proof-authority'] is False
corpus = read(E / 'direct-corpus.json')
assert corpus['schema'] == 'enchant.formal.shared-sdk-point-fixtures.v1' and corpus['managed-query-calls'] == 0
assert len(corpus['rows']) == 187 and corpus['compiler-proof-authority'] is False
previous = {row['id']: row for row in read(P / 'evidence/numeric-point/compatibility.json')['rows']}
assert set(previous) == {row['id'] for row in corpus['rows']}
roots = 0
for row in corpus['rows']:
    assert row['data-reference'] == previous[row['id']]['data-reference']
    for i, point in enumerate(row['points']):
        assert point['exact-values'] and point['concrete-values-sort-checked']
        for name in ('mode', 'roots', 'value-reference', 'checking'):
            assert point[name] == previous[row['id']]['points'][i][name], (row['id'], name)
        roots += point['roots']
assert roots == 6300
readers = [read(E / (stage + '.json')) for stage in ('reader-one', 'reader-two')]
assert readers[0]['process'] != readers[1]['process'] and readers[0]['cwd'] != readers[1]['cwd']
for reader in readers:
    assert reader['sdk-only'] and reader['research-import-path'] is False and reader['source-payload-execution'] is False
    assert reader['managed-query-calls'] == 0 and reader['compiler-proof-authority'] is False
    assert reader['transport-float-history'] == 'identity-kept' and len(reader['rows']) == 187
    expected_rows = {row['id']: row for row in corpus['rows']}
    assert set(expected_rows) == {row['id'] for row in reader['rows']}
    for row in reader['rows']:
        assert len(row['points']) == 4 and all(point['exact-values'] for point in row['points'])
        for actual, expected in zip(row['points'], expected_rows[row['id']]['points']):
            for name in ('mode', 'roots', 'checking'):
                assert actual[name] == expected[name], (row['id'], name)

native = read(E / 'paired-native-corpus.json')
oldnative = {row['id']: row for row in read(P / 'evidence/observation-semantics/paired-native-corpus.json')['rows']}
assert native['compiler-proof-authority'] is False and len(native['rows']) == 187
assert set(oldnative) == {row['id'] for row in native['rows']}
native_differences = []
worker_sha = '595c0dc4a1cdababd4ee241eddba00bd7430de9292d48de7299dd4b41edd7006'
library_sha = '2c4c61e03b3fc1f5ccd0c388f5fcc89d00ccc058a2f9c2176b55a360ac606129'
for row in native['rows']:
    old = oldnative[row['id']]
    assert row['roots'] == old['roots'] and row['standard-identity'] == old['standard-identity']
    for engine in ('z3', 'oxiz'):
        current, preceding = row[engine], old[engine]
        identity = current['identity']
        assert identity['sdk'] == pin['sdk'] and identity['backend'] == engine and identity['worker-sha256'] == worker_sha
        assert identity['library-sha256'] == (library_sha if engine == 'z3' else None)
        assert isinstance(current.get('validation'), dict) and isinstance(preceding.get('validation'), dict)
        for name in ('solver-status', 'verdict', 'phase', 'observation-basis'):
            if current.get(name) != preceding.get(name):
                native_differences.append({'id': row['id'], 'engine': engine, 'field': name,
                                           'before': preceding.get(name), 'after': current.get(name)})
        if current['validation'].get('status') != preceding['validation'].get('status'):
            native_differences.append({'id': row['id'], 'engine': engine, 'field': 'validation.status',
                                       'before': preceding['validation'].get('status'),
                                       'after': current['validation'].get('status')})
(E / 'native-differences.json').write_text(json.dumps(native_differences, indent=2) + '\n')
assert not native_differences, native_differences
report = {'schema': 'enchant.formal.shared-sdk-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'stages': stages, 'runs': runs,
          'recipe': {'code_commit': code_commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'artifact_sha256': {name: sha(E / name) for name in ('sdk-candidate.json', 'sdk-traces.json',
              'transport.json', 'direct-corpus.json', 'reader-one.json', 'reader-two.json',
              'paired-native-corpus.json', 'native-differences.json')},
          'assertion_executions': sum(sum(rows.values()) for rows in runs.values()),
          'runtime_sources': 691, 'build_linkage_sha256': sha(E / 'build-linkage.json'),
          'compiler_floor': parent['retained_compiler_floor'], 'actual_sdk_traces': traces,
          'pure_point_questions': 187, 'point_maps': 748, 'exact_root_values': roots, 'sdk_only_readers': 2,
          'paired_native_questions': 187, 'native_differences': native_differences,
          'project_pin_promoted': False, 'compiler_proof_authority': False,
          'scope': 'One immutable SDK, shared private mathematical dispatcher, fresh owned graph admission and resource profiles, actual Source privacy/native-bridge distinctions, complete point compatibility, fresh SDK-only readers and paired native regression at unchanged deadlines. Project adapter migration and live presentation are separate integration gates. No universal cost, totality, implementation/compiler preservation or new backend theory support is established.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'assertion_executions': report['assertion_executions'],
                  'pure_point_questions': 187, 'paired_native_questions': 187}))
