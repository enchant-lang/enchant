"""Qualify managed original-graph execution; higher language/presentation remain separate."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-graph'
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
assert link['sdk_pin'] == pin and len(link['runtime_source_sha256']) == 700
metadata = read(Path(pin['sdk']) / 'artifact.json')
for name, digest in link['runtime_source_sha256'].items():
    assert sha(R / name) == sha(Path(pin['source']) / name) == sha(Path(metadata['source']) / name) == digest
    assert sha(Path(pin['sdk']) / 'lib/beam_lisp-0.1.0' / name) == digest
assert set(link['source_changes']) == {'priv/lib/formal/backend.bl', 'priv/lib/oracle.bl', 'priv/lib/formal/request-answer.bl', 'priv/lib/formal/request-point.bl', 'priv/lib/formal/graph-question.bl', 'priv/lib/formal/evaluate.bl', 'priv/lib/formal/graph-execution.bl', 'priv/lib/formal/graph-replay.bl', 'priv/lib/formal/coordinates.bl', 'priv/lib/formal/request.bl', 'priv/lib/veritas/ledger.bl', 'priv/lib/formal/logic.bl', 'priv/lib/formal/request-record.bl', 'priv/lib/formal/graph-terms.bl', 'priv/lib/formal/request-runtime.bl'}
baseline = read(E / 'baseline-sdk-pin.json')
parent = read(P / 'evidence/shared-primitives/qualification.json')
assert baseline == parent['sdk_pin'] and parent['status'] == 'passed'
oldmeta = read(Path(baseline['sdk']) / 'artifact.json')
for name in ('compiler', 'dependencies', 'platform', 'formalWorker'):
    assert metadata[name] == oldmeta[name] == link['unchanged_components'][name]
assert parent['compiler_floor']['files'] == 141
assert parent['compiler_floor']['compiler'] == metadata['compiler']
stages = {}
required = ('source-preflight', 'sdk-preflight', 'sdk-preflight-controls', 'sdk-focused', 'format-focused',
            'project-focused', 'sdk-regression', 'regression', 'facade', 'profile-sorts',
            'managed-reader-one', 'managed-reader-two', 'managed-reader-controls',
            'paired-native-corpus', 'managed-native-corpus', 'key-probe', 'request-ledger-write',
            'request-ledger-reader-one', 'request-ledger-reader-two', 'request-ledger-controls')
for stage in required:
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == (baseline if stage == 'source-preflight' else pin)
    for name, digest in source['source_sha256'].items():
        body = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)
        assert hashlib.sha256(body).hexdigest() == digest
        if name != 'research/formal-logic/run-managed-graph.py':
            assert sha(R / name) == digest, name
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired'], stage
    if result.get('exit_source') == 'retained-original-systemd-service':
        adoption = read(E / (stage + '-adoption-source-pin.json'))
        terminal = read(E / (stage + '-adoption-terminal.json'))
        assert stage == 'paired-native-corpus'
        assert sha(E / (stage + '-adoption-terminal.json')) == result['adoption_terminal_sha256']
        assert terminal['Id'] == adoption['unit'] and terminal['InvocationID'] == adoption['invocation']
        assert terminal['ActiveState'] == 'inactive' and terminal['MainPID'] == '0'
        assert terminal['Result'] == 'success' and terminal['ExecMainCode'] == '1' and terminal['ExecMainStatus'] == '0'
        assert adoption['initial_state']['ActiveState'] == 'active'
        assert adoption['original_source_pin_sha256'] == sha(E / (stage + '-source-pin.json'))
        assert adoption['outer_handle_exit_code'] == 143
        assert sha(R / adoption['recipe']) == adoption['recipe_sha256']
        recipe_body = subprocess.check_output(['git', 'show', adoption['code_commit'] + ':' + adoption['recipe']], cwd=R)
        assert hashlib.sha256(recipe_body).hexdigest() == adoption['recipe_sha256']
    command = read(E / (stage + '-command.json'))
    ceiling = 3600 if stage == 'paired-native-corpus' else (1800 if stage == 'managed-native-corpus' else (720 if stage == 'sdk-preflight-controls' else 900))
    assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group'))
    if stage not in ('source-preflight', 'sdk-preflight', 'sdk-preflight-controls'):
        assert pin['sdk'] + '/bin/bl' in command and '--cold' in command
    if stage in ('sdk-focused', 'format-focused', 'sdk-regression', 'profile-sorts', 'managed-reader-one', 'managed-reader-two', 'managed-reader-controls'):
        assert '-p' not in command, stage
    stages[stage] = {'source_pin': source, 'exit': result,
                     'command_sha256': sha(E / (stage + '-command.json')), 'log_sha256': sha(E / (stage + '-checks.txt'))}
runs = {}
for stage, files in (('sdk-focused', 5), ('format-focused', 1), ('project-focused', 9), ('sdk-regression', 7), ('regression', 31), ('facade', 7)):
    log = (E / (stage + '-checks.txt')).read_text()
    rows = {name: int(count) for name, count in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
    assert len(rows) == files and f'{files} file(s) passed, 0 failed, 0 incoherent' in log
    runs[stage] = rows
assert runs['sdk-focused']['formal.shared-evaluator-test'] == 130
assert runs['sdk-focused']['formal.graph-admission-test'] > 45
assert runs['sdk-focused']['formal.managed-graph-test'] >= 202
assert runs['sdk-focused']['formal.request-test'] >= 120
assert runs['sdk-focused']['formal.graph-keys-test'] >= 60
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
probe = read(E / 'profile-sorts.json')
assert probe['native-sessions'] == probe['managed-query-calls'] == 0
assert probe['compiler-proof-authority'] is False
expected = {'general-unused-real': ('admitted', 1), 'bool-int-unused-real': ('refused', 0),
            'numeric-unused-fp-s2': ('refused', 0), 'numeric-unused-rounding': ('refused', 0),
            'numeric-unused-int': ('admitted', 1)}
assert len(probe['rows']) == len(expected)
for row in probe['rows']:
    assert (row['status'], row['actual-app-constructor-calls']) == expected[row['case']]

keys = read(E / 'key-probe.json')
assert keys['keyword-names-still-absent'] is True
assert keys['native-exchanges'] == keys['managed-query-calls'] == keys['native-sessions'] == 0
assert len(keys['rows']) == 3 and all(row['status'] == 'admitted' and row['checking']['materialized-keys'] == 0 for row in keys['rows'])
assert keys['compiler-proof-authority'] is False

managed = read(E / 'managed-native-corpus.json')
assert managed['compiler-proof-authority'] is False
assert managed['native-deadlines'] == {'solver-ms': 500, 'hard-ms': 2000}
assert len(managed['rows']) == 187 and len({r['id'] for r in managed['rows']}) == 187
assert sum(r['numeric-sorts'] for r in managed['rows']) == 94
legacy = {r['id']: r for r in read(E / 'paired-native-corpus.json')['rows']}
managed_differences = []
points = 0
for row in managed['rows']:
    for engine in ('z3', 'oxiz'):
        answer = row[engine]
        assert answer['formal/managed-graph-reply'] == 2 and answer['reply-profile'] == 'bl/managed-numeric-graph-preview-v2'
        assert answer['compiler-proof-authority'] is False and answer['trusted'] is False
        assert answer['certificate']['status'] == 'not-checked'
        assert answer['request-reference'] == answer['question-reference'] == row['reference']
        assert answer['native-limits'] == managed['native-deadlines']
        if not row['numeric-sorts']:
            assert answer['solver-status'] == 'not-run' and answer['phase'] == 'admission'
            assert answer['native-scope-attempts'] == 0
        else:
            before = legacy[row['id']][engine]
            for name in ('solver-status', 'verdict', 'phase'):
                if answer.get(name) != before.get(name):
                    managed_differences.append({'id': row['id'], 'engine': engine, 'field': name,
                                               'before': before.get(name), 'after': answer.get(name)})
            if answer['validation']['status'] != before['validation']['status']:
                managed_differences.append({'id': row['id'], 'engine': engine, 'field': 'validation.status',
                                           'before': before['validation']['status'], 'after': answer['validation']['status']})
        if answer['solver-status'] == 'sat' and answer['assertion-replay'] == 'run':
            points += 1
(E / 'managed-vs-legacy.json').write_text(json.dumps(managed_differences, indent=2) + '\n')
assert not managed_differences, managed_differences
readers = [read(E / (stage + '.json')) for stage in ('managed-reader-one', 'managed-reader-two')]
assert readers[0]['process'] != readers[1]['process'] and readers[0]['cwd'] != readers[1]['cwd']
for reader in readers:
    assert reader['sdk-only'] and reader['research-import-path'] is False and reader['source-payload-execution'] is False
    assert reader['native-exchanges'] == reader['managed-query-calls'] == 0
    assert reader['checked-native-execution'] is False and reader['compiler-proof-authority'] is False
    assert len(reader['rows']) == 187 and reader['replayed-points'] == points
    assert reader['sdk'] == pin['sdk']
    for row in reader['rows']:
        for engine in ('z3', 'oxiz'):
            assert row[engine]['checked-native-execution'] is False
assert readers[0]['rows'] == readers[1]['rows']
controls = read(E / 'managed-reader-controls.json')
assert controls['positive']['status'] == 'accepted' and controls['positive']['point-replay'] == 'run'
assert len(controls['controls']) == 10 and all(r['status'] == 'refused' for r in controls['controls'])
assert controls['rehashed-invalid-coordinate'] == 'independently-invalid'
assert controls['native-exchanges'] == controls['managed-query-calls'] == 0
assert controls['checked-native-execution'] is False and controls['compiler-proof-authority'] is False

ledger_write = read(E / 'request-ledger-write.json')
assert ledger_write['mode'] == 'write' and len(ledger_write['rows']) == 2 and ledger_write['native-exchanges'] == 4
ledger_readers = [read(E / (stage + '.json')) for stage in ('request-ledger-reader-one', 'request-ledger-reader-two')]
assert ledger_readers[0]['process'] != ledger_readers[1]['process'] and ledger_readers[0]['cwd'] != ledger_readers[1]['cwd']
for reader in [ledger_write, *ledger_readers, read(E / 'request-ledger-controls.json')]:
    assert reader['sdk-only'] and reader['research-import-path'] is False and reader['source-payload-execution'] is False
    assert reader['key-names-still-absent'] and reader['sdk'] == pin['sdk']
    assert reader['managed-query-calls'] == 0 and reader['checked-native-execution'] is False and reader['compiler-proof-authority'] is False
    if reader['mode'] != 'write':
        assert reader['native-exchanges'] == 0
for reader in ledger_readers:
    assert len(reader['rows']) == 2
    assert all(row['validation'] == 'valid' and row['verdict'] == 'sat' and row['recorded-artifact-matches-this-sdk'] for row in reader['rows'])
assert ledger_readers[0]['rows'] == ledger_readers[1]['rows']
ledger_controls = read(E / 'request-ledger-controls.json')
assert ledger_controls['positive'] == 'sat' and ledger_controls['changed-point'] == 'independently-invalid'
assert len(ledger_controls['controls']) == 6 and all(row['status'] == 'refused' for row in ledger_controls['controls'])
assert ledger_controls['actual-index-tampering']['status'] == 'refused'
assert read(E / 'request-ledger-fixture-retired.json')['retired'] is True

native = read(E / 'paired-native-corpus.json')
oldnative = {row['id']: row for row in read(P / 'evidence/shared-primitives/paired-native-corpus.json')['rows']}
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
report = {'schema': 'enchant.formal.managed-graph-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'stages': stages, 'runs': runs,
          'recipe': {'code_commit': code_commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'artifact_sha256': {name: sha(E / name) for name in ('sdk-candidate.json', 'sdk-traces.json',
              'profile-sorts.json', 'key-probe.json', 'request-ledger-write.json', 'request-ledger-reader-one.json',
              'request-ledger-reader-two.json', 'request-ledger-controls.json', 'managed-native-corpus.json', 'managed-reader-one.json', 'managed-reader-two.json',
              'managed-reader-controls.json', 'managed-vs-legacy.json', 'paired-native-corpus.json', 'native-differences.json')},
          'assertion_executions': sum(sum(rows.values()) for rows in runs.values()),
          'runtime_sources': 700, 'build_linkage_sha256': sha(E / 'build-linkage.json'),
          'compiler_floor': parent['compiler_floor'], 'actual_sdk_traces': traces,
          'managed_questions': 187, 'numeric_questions': 94, 'saved_replayed_points': points,
          'sdk_only_readers': 4, 'assurance_refusal_controls': 16, 'persisted_request_records': 2,
          'paired_native_questions': 187, 'native_differences': native_differences,
          'managed_vs_legacy': managed_differences, 'project_pin_promoted': False, 'compiler_proof_authority': False,
          'scope': 'One immutable SDK: fresh original graph admission and private numeric replay inside the actual native owner, raw unused binder sort gates, graph-native application keys and coordinate/diagnostic data, oracle request scope and typed request ledger persistence, unchanged native deadlines and legacy outcomes, mixed import allocator/lifecycle checks, canonical-coordinate policy and fresh SDK-only model reopening with assurance/semantic tamper controls. Saved status/execution remain reported data. Retained-session language request integration, full observation materialization, wider derived-value policies and public API migration remain separate work. No universal cost, totality, implementation/compiler preservation or new backend theory support is established.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'assertion_executions': report['assertion_executions'],
                  'managed_questions': 187, 'saved_points': points, 'sdk_only_readers': 4}))
