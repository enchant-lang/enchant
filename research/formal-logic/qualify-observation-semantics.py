"""Qualify common observation repairs and graph display reconstruction separately."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/observation-semantics'
OLD = P / 'evidence/graph-consumers'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def committed(snapshot, current=True):
    for name, digest in snapshot['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest, ('committed source', name)
        # Each launch pins its recipe. Later stages may add runner stages, but
        # may not silently change any subject implementation or test fixture.
        recipe = name in ('research/formal-logic/run-observation-semantics.py',
                          'research/formal-logic/run-observation-admission.py')
        if current and not recipe:
            assert sha(R / name) == digest, ('current checked subject', name)

pin = read(E / 'sdk-candidate.json')
sdk, source = Path(pin['sdk']), Path(pin['source'])
meta = read(sdk / 'artifact.json')
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
build = read(E / 'sdk-source-pin.json')
committed(build, current=False)
assert read(E / 'sdk-build-exit.json')['exit_code'] == 0
assert build['code_commit'] == pin['base_commit'] and build['engine_fingerprint'] == pin['engine_fingerprint']
link = read(E / 'build-linkage.json')
assert link['sdk_pin'] == pin and link['engine_fingerprint'] == pin['engine_fingerprint']
assert len(link['runtime_source_sha256']) == 688
for name, digest in link['runtime_source_sha256'].items():
    assert sha(source / name) == sha(Path(meta['source']) / name) == sha(sdk / 'lib/beam_lisp-0.1.0' / name) == digest
    assert sha(R / name) == digest, ('current runtime', name)
for name in ('priv/lib/formal/query.bl', 'priv/lib/formal/value.bl'):
    assert build['source_sha256'][name] == link['runtime_source_sha256'][name]
assert set(link['source_changes']) == {'priv/lib/formal/query.bl', 'priv/lib/formal/value.bl', 'priv/lib/live/app.bl'}
receipt = read(E / 'managed-preparation-result.json')
operation = read(E / 'managed-operation.json')
assert sha(E / 'managed-operation.json') == link['operation_sha256'] == receipt['operation-sha256']
assert sha(E / 'managed-preparation-result.json') == link['receipt_sha256']
assert receipt['source'] == operation['source'] == str(source) and receipt['output'] == str(sdk)
assert operation['previous'] == read(E / 'baseline-sdk-pin.json')['sdk']

stages = {}
for stage in ('sdk-focused', 'graph-focused', 'native', 'observation-corpus', 'sdk-regression',
              'regression', 'paired-native-corpus', 'facade', 'live-regression',
              'preflight', 'preflight-controls', 'writer', 'consumer-one', 'consumer-two', 'example'):
    snapshot = read(E / (stage + '-source-pin.json'))
    assert snapshot['sdk_pin'] == pin
    committed(snapshot)
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired'], stage
    command = read(E / (stage + '-command.json'))
    for item in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0', '--property=KillMode=control-group'):
        assert item in command, (stage, item)
    if stage not in ('preflight', 'preflight-controls'):
        assert str(sdk / 'bin/bl') in command and '--cold' in command
        for variable in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH'):
            assert any(command[i:i + 2] == ['-u', variable] for i in range(len(command) - 1))
    work = next(x.split('=', 1)[1] for x in command if x.startswith('--working-directory='))
    runtime = next(x.split('=', 2)[2] for x in command if x.startswith('--setenv=XDG_RUNTIME_DIR='))
    assert not Path(work).exists() and not Path(runtime).exists()
    assert not Path(work).is_relative_to(R)
    stages[stage] = {'source': snapshot, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}

runs = {}
for stage, files in (('sdk-focused', 1), ('graph-focused', 4), ('native', 1), ('sdk-regression', 6),
                     ('regression', 31), ('facade', 7), ('live-regression', 1)):
    text = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    assert len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in text, stage
    runs[stage] = rows
assert runs['sdk-focused'] == {'formal.observation-test': 62}
assert runs['native'] == {'formal.observation-native-test': 16}
assert runs['graph-focused'] == {'formal.term-forest-evaluate-test': 104, 'formal.graph-observations-test': 102,
                                  'formal.question-forest-test': 71, 'formal.graph-reader-test': 21}
previous = read(OLD / 'qualification.json')
assert runs['sdk-regression'] == previous['runs']['focused']
assert runs['regression'] == previous['runs']['regression'] and runs['facade'] == previous['runs']['facade']

worker_sha = '595c0dc4a1cdababd4ee241eddba00bd7430de9292d48de7299dd4b41edd7006'
library_sha = '2c4c61e03b3fc1f5ccd0c388f5fcc89d00ccc058a2f9c2176b55a360ac606129'
def identity(row, engine):
    assert row['sdk'] == str(sdk) and row['backend'] == engine and row['worker-sha256'] == worker_sha
    artifacts = row['artifacts']
    assert artifacts['sdk'] == str(sdk) and artifacts['worker']['origin'] == 'sdk'
    assert artifacts['worker']['path'].startswith(meta['image'] + '/')
    assert artifacts['worker']['sha256'] == sha(Path(artifacts['worker']['path'])) == worker_sha
    assert artifacts['packaged']['oxiz-version'] == '0.3.4'
    assert artifacts['packaged']['features'] == ['oxiz-core/std', 'oxiz-solver/std']
    if engine == 'z3':
        assert row['library-sha256'] == artifacts['library']['sha256'] == library_sha
        assert artifacts['library']['origin'] == 'sdk' and sha(Path(artifacts['library']['path'])) == library_sha
    else:
        assert artifacts['library'] is None and row['library-sha256'] is None

native = read(E / 'native.json')
assert native['native-scopes'] == 4 and native['compiler-proof-authority'] is False
assert {row['engine'] for row in native['rows']} == {'z3', 'oxiz'}
for row in native['rows']:
    for mode in ('ordinary', 'graph'):
        reply = row[mode]
        identity(reply['identity'], row['engine'])
        assert reply['trusted'] is False and reply['verdict'] == 'sat'
        assert reply['validation']['status'] == 'valid' and reply['certificate']['status'] == 'not-checked'
    assert row['graph']['compiler-proof-authority'] is False and row['graph']['delegation'] == 'matched'

oldrows = {r['id']: r for r in read(OLD / 'corpus.json')['rows']}
paired = read(E / 'paired-native-corpus.json')['rows']
assert len(paired) == len(oldrows) == 187 and len({r['id'] for r in paired}) == 187
for row in paired:
    before = oldrows[row['id']]
    for field in ('graph', 'roots', 'standard-identity'):
        assert row[field] == before[field], (row['id'], field)
    for engine in ('z3', 'oxiz'):
        identity(row[engine]['identity'], engine)
        for field in ('solver-status', 'verdict', 'phase'):
            assert row[engine][field] == before[engine][field], (row['id'], engine, field)
for family in ('advanced', 'features', 'native'):
    data = read(E / 'regression' / (family + '.json'))
    assert not data['disagreements'] and not data['invalid-models']
    for row in data['cases']:
        before = oldrows[row['id']]
        assert row['question-sha256'] == before['roots']
        for engine in ('z3', 'oxiz'):
            identity(row[engine]['identity'], engine)
            for field in ('solver-status', 'verdict', 'phase'):
                assert row[engine][field] == before[engine][field]

corpus = read(E / 'observation-corpus.json')
assert corpus['managed-query-calls'] == 0 and corpus['native-execution'] == 'not-invoked'
assert corpus['compiler-proof-authority'] is False and len(corpus['rows']) == 187
assert {r['id'] for r in corpus['rows']} == set(oldrows)
observations = roots = 0
for row in corpus['rows']:
    assert row['question-reference'] == oldrows[row['id']]['graph']['reference']
    assert row['compiler-proof-authority'] is False
    assert [p['mode'] for p in row['points']] == ['absent', 'zero', 'alternate', 'ill-sorted']
    for point in row['points']:
        assert point['exact-observations'] and point['exact-root-values']
        assert point['checking']['argument-traversal'] == 'graph-references'
        assert point['checking']['evaluated-nodes'] <= point['checking']['typed-nodes']
        observations += point['observations']
        roots += point['roots']
assert (observations, roots) == (1176, 6300)
example = read(E / 'example.json')
assert example['managed-query-calls'] == 0 and example['compiler-proof-authority'] is False
assert example['inactive']['question-reference'] == example['active']['question-reference'] == example['question-reference']
assert example['inactive']['refused-observations'] == [] and example['active']['refused-observations'] == ['optional']
assert example['inactive']['observations']['optional']['value'] == {'present': False}
assert example['active']['observations']['optional']['reason'] == 'observation-materialization-refused'

floor = read(OLD / 'produced-compiler.json')
assert floor['status'] == 'passed' and floor['files'] == 141
assert floor['compiler'] == meta['compiler'] == link['unchanged_components']['compiler']
flight = read(E / 'source-preflight.json')
assert flight['root'] == str(source) and flight['runtime'] == str(sdk)
assert all(flight[k]['modality'] == 'exhausted' and flight[k]['complete'] for k in ('beam-selection', 'declaration-cases'))
assert not any(flight[k] for k in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis'))
assert not flight['selector_changed_during_analysis'] and not flight['driver_changed_during_analysis']
assert 'SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text()

writer = read(E / 'writer.json')
a, b = read(E / 'consumer-one.json'), read(E / 'consumer-two.json')
assert writer['sdk-only'] and writer['rows'] == 3 and len({writer['process'], a['process'], b['process']}) == 3
for data, stage in ((writer, 'writer'), (a, 'consumer-one'), (b, 'consumer-two')):
    assert data['sdk-only'] and not Path(data['cwd']).is_relative_to(R)
    assert '-p' not in read(E / (stage + '-command.json'))
for data in (a, b):
    assert data['managed-query-calls'] == 0 and data['source-compilation'] is False and data['compiler-proof-authority'] is False
    assert {r['engine'] for r in data['rows']} == {'z3', 'oxiz'}
    for row in data['rows']:
        for field in ('reference', 'graph', 'point'):
            assert row[field] == writer[field]
        assert row['materialization'] == 'refused'
        assert row['answer'] == {'verdict': 'sat', 'solver-status': 'sat', 'delegation': 'not-matched', 'observation-basis': 'independent-replay'}
        assert row['checking']['status'] == 'checked-data-connection' and row['checking']['kernel-execution'] == 'not-run'
fixture = read(E / 'owned-ledger.json')
assert fixture['active_db_retired'] and sha(E / fixture['archive']) == fixture['archive_sha256']
with tarfile.open(E / fixture['archive'], 'r:gz') as saved:
    for name, digest in fixture['files'].items():
        assert hashlib.sha256(saved.extractfile(name).read()).hexdigest() == digest
assert not (E / 'durable-ledger').exists() and not (E / 'durable-ledger.blobs').exists()

report = {'schema': 'enchant.formal.observation-semantics-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'runs': runs,
          'assertion_executions': sum(sum(rows.values()) for rows in runs.values()), 'stages': stages,
          'observation_questions': 187, 'point_maps': 748, 'exact_observation_values': observations,
          'exact_root_values': roots, 'pure_observation_query_calls': 0, 'paired_native_result_records': 374,
          'focused_list_native_scopes': 4, 'fresh_sdk_only_writer': 1, 'fresh_sdk_only_readers': 2,
          'build_linkage_sha256': sha(E / 'build-linkage.json'), 'owned_fixture': fixture,
          'retained_compiler_floor': {'receipt_sha256': sha(OLD / 'produced-compiler.json'),
                                      'compiler': meta['compiler'], 'files': 141,
                                      'basis': 'Identical immutable compiler, dependency and platform artifacts; fresh runtime/source and affected consumer checks.'},
          'scope': 'Common query counterexample admission and explicit list-valued observations in the SDK; graph-reader, graph-point and structured graph-observation interpreter remain project previews. Reconstruction does not replay assertions. Resource preflight and actual managed-owner integration remain required before promotion. No decoder/evaluator/BL implementation soundness, native certificate or compiler preservation theorem.',
          'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'assertions': report['assertion_executions'],
                  'questions': 187, 'point_maps': 748, 'observations': observations, 'root_values': roots}))
