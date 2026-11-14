"""Audit the exact artifact and every required gate before a separate selection step."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/scalar-integration'
C = P / 'evidence/numeric-semantics'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin, baseline = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
parent = read(P / 'evidence/word-integration/qualification.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == baseline
retained = read(P / 'evidence/retained-request/qualification.json')
assert retained['sdk_pin'] == parent['baseline_sdk_pin']
assert read(C / 'qualification.json')['sdk_pin'] == retained['baseline_sdk_pin']
sdk = Path(pin['sdk'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
metadata = read(sdk / 'artifact.json')
linkage = read(E / 'build-linkage.json')
assert linkage['status'] == 'bound' and linkage['sdk_pin'] == pin and linkage['qualified_baseline'] == baseline
assert len(linkage['source_sha256']) == 723 and len(linkage['source_changes']) == 13
for name, digest in linkage['source_sha256'].items():
    assert sha(R / name) == sha(Path(pin['source']) / name) == sha(Path(metadata['source']) / name) == sha(sdk / 'lib/beam_lisp-0.1.0' / name) == digest
assert linkage['unchanged_components'] == {name: metadata[name] for name in ('platform', 'formalWorker')}
old_metadata = read(Path(baseline['sdk']) / 'artifact.json')
assert all(old_metadata[name] == metadata[name] for name in ('platform', 'formalWorker'))
floor_path = C / 'compiler-floor-install.json'
floor = read(floor_path)
assert floor['status'] == 'passed' and len(floor['after']) == linkage['compiler_floor_files'] == 141
assert sha(floor_path) == linkage['compiler_floor_install_sha256']
for name, digest in floor['after'].items():
    assert sha(R / 'priv/bootstrap/seed' / name) == sha(Path(metadata['compiler']) / 'seed' / name) == sha(sdk / 'image/priv/bootstrap/seed' / name) == digest
# Numeric and JS behavior is inherited by exact unchanged implementation
# bytes, with the predecessor qualification retained explicitly as evidence.
numeric_names = ['priv/boot/rt.bl', 'priv/host/num.bl', 'priv/host/decimal.bl', 'priv/lib/decimal.bl',
                 'priv/lib/system/smt.bl', 'priv/lib/js/rt.mjs', 'priv/lib/js/leaves.mjs', 'priv/lib/js/host-leaves.mjs']
for name in numeric_names:
    assert sha(Path(baseline['source']) / name) == linkage['source_sha256'][name]
stages = {}
runs = {}
for stage in ('preflight', 'preflight-controls', 'focused', 'word-focused', 'legacy', 'regression', 'native', 'packets', 'text-packets', 'evidence-packets'):
    source = read(E / (stage + '-source-pin.json'))
    assert source['sdk_pin'] == pin
    for name, digest in source['source_sha256'].items():
        assert sha(R / name) == digest, name
        assert hashlib.sha256(subprocess.check_output(['git', 'show', source['code_commit'] + ':' + name], cwd=R)).hexdigest() == digest
    result = read(E / (stage + '-exit.json'))
    assert result['exit_code'] == 0 and result['runtime_retired'] and result['consumer_cwd_retired'], stage
    command = read(E / (stage + '-command.json'))
    assert all(flag in command for flag in ('--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + ('3600' if stage == 'native' else '1200'), '--property=KillMode=control-group'))
    log = (E / (stage + '-checks.txt')).read_text()
    if stage in ('focused', 'word-focused', 'legacy', 'regression', 'native', 'packets', 'text-packets', 'evidence-packets'):
        assert pin['sdk'] + '/bin/bl' in command and '--cold' in command
        assert ('-p' in command) == (stage in ('regression', 'native'))
    if stage in ('focused', 'word-focused', 'legacy', 'regression'):
        count = {'focused': 8, 'word-focused': 12, 'legacy': 5, 'regression': 31}[stage]
        rows = {name: int(total) for name, total in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
        assert len(rows) == count and f'{count} file(s) passed, 0 failed, 0 incoherent' in log
        assert result['complete_green_test_summary'] is True
        runs[stage] = rows
    stages[stage] = {'source_pin': source, 'exit': result, 'command_sha256': sha(E / (stage + '-command.json')),
                     'log_sha256': sha(E / (stage + '-checks.txt'))}
assert runs['word-focused']['formal.retained-request-check'] == 90
assert {key: runs['word-focused'][key] for key in parent['assertion_runs']['focused']} == parent['assertion_runs']['focused']
assert runs['word-focused']['formal.word-graph-test'] == 1139
assert runs['word-focused']['formal.word-request-test'] == 40 and runs['word-focused']['formal.word-owner-test'] == 36
assert runs['word-focused']['formal.request-lookup-test'] == 129
assert runs['word-focused']['formal.word-owner-admission-test'] >= 30
assert sum(runs['legacy'].values()) == 818
assert sum(runs['regression'].values()) == 8141
preflight = read(E / 'source-preflight.json')
assert preflight['root'] == pin['source'] and preflight['runtime'] == pin['sdk'] and preflight['selected-count'] == 604
for name in ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis'):
    assert preflight[name] == []
assert preflight['selector_changed_during_analysis'] is False and preflight['driver_changed_during_analysis'] is False
assert 'SDK-PREFLIGHT-CONTROL passed: parse, target edge and cycle refusals' in (E / 'preflight-controls-checks.txt').read_text()
records = read(E / 'records-qualification.json')
assert records['status'] == 'passed' and records['sdk_pin'] == pin
assert records['records'] == records['ledger_rows_per_reader'] == 20
assert records['refusal_controls'] == 16
assert records['independently_invalid_text_controls'] == 3
assert records['normalizer_calls_per_selected_lookup'] == 1 and records['ledger_before_packets'] is True
assert records['fresh_sdk_only_readers'] == 2 and records['solver_exchanges'] == records['oracle_calls'] == 0
assert read(E / 'corpus-ledger-retirement.json')['retired'] is True
text_packets = read(E / 'text-packets.json')
assert text_packets['status'] == 'passed' and text_packets['records'] == 4 and text_packets['negative-controls'] == 4
assert text_packets['native-exchanges'] == text_packets['oracle-calls'] == 0 and text_packets['manual-schema-preload'] is False
assert text_packets['sdk'] == pin['sdk'] and text_packets['warmed-atoms-stable'] is True
assert len(text_packets['domain-observations']) == 5
evidence_packets = read(E / 'evidence-packets.json')
assert evidence_packets['status'] == 'passed' and evidence_packets['packets'] == 2 and evidence_packets['fresh-checks'] == 6
assert evidence_packets['negative-controls'] == 6 and evidence_packets['native-exchanges'] == evidence_packets['oracle-calls'] == 0
assert evidence_packets['sdk'] == pin['sdk'] and evidence_packets['warmed-atoms-stable'] is True
assert runs['focused'] == {'formal.scalar-text-graph-test':72, 'formal.scalar-text-resource-test':474,
 'formal.scalar-text-interface-test':38, 'formal.scalar-text-owner-test':21, 'formal.finite-word-certificate-test':82,
 'formal.request-evidence-test':47, 'formal.evidence-effect-test':32, 'formal.evidence-oracle-test':17}
focused_artifacts = {}
for name in ('text-native.json', 'term-native.json', 'word-native.json', 'bundle-corpus.json', 'bundle-corpus.json.coverage.json'):
    path = E / name
    assert (E / 'focused-command.json').stat().st_mtime_ns <= path.stat().st_mtime_ns <= (E / 'focused-exit.json').stat().st_mtime_ns
    focused_artifacts[name] = sha(path)
text_rows = read(E / 'text-native.json')['observations']
assert len(text_rows) == 4
assert {(row['case'], row['backend']) for row in text_rows} == {
    ('coordinate','z3'), ('coordinate','oxiz'), ('codepoint-contract','z3'), ('codepoint-contract','oxiz')}
for row in text_rows:
    assert row['source']['identity']['sdk'] == pin['sdk'] and row['compiler-proof-authority'] is False
    if row['case'] == 'coordinate':
        assert row['source']['status'] == row['verdict'] == 'sat'
    else:
        assert row['source']['status'] == ('unsat' if row['backend'] == 'z3' else 'unknown')
word_rows = read(E / 'word-native.json')['rows']
assert len(word_rows) == 2 and {row['backend'] for row in word_rows} == {'z3','oxiz'}
for row in word_rows:
    assert row['identity']['sdk'] == pin['sdk'] and row['native-status'] == 'unsat'
    assert row['native-verdict'] == 'solver-claim' and row['native-certificate']['status'] == 'not-checked'
    independent = row['independent-check']
    assert independent['status'] == 'checked' and independent['points-checked'] == 8
    assert independent['feasibility'] == 'not-established' and independent['compiler-proof-authority'] is False
assert word_rows[0]['independent-check']['statement'] == word_rows[1]['independent-check']['statement']
bundle_rows = read(E / 'bundle-corpus.json')['rows']
assert len(bundle_rows) == 2 and {row['backend'] for row in bundle_rows} == {'z3','oxiz'}
assert len(read(E / 'bundle-corpus.json.coverage.json')) == 5
assert all(row['identity']['sdk'] == pin['sdk'] and row['result']['proof-check']['points-checked'] == 8 for row in bundle_rows)
term_rows = read(E / 'term-native.json')['rows']
assert len(term_rows) == 2 and all(row['identity']['sdk'] == pin['sdk'] for row in term_rows)
previous_word = read(E / 'previous-word-readers-qualification.json')
assert previous_word['status'] == 'passed' and previous_word['sdk_pin'] == pin
assert previous_word['recorded_producer_sdk_pin'] == baseline and previous_word['records'] == 12
assert previous_word['fresh_sdk_only_readers'] == 2 and previous_word['refusal_controls'] == 15
assert previous_word['solver_exchanges'] == previous_word['oracle_calls'] == 0
previous = read(E / 'previous-readers-qualification.json')
assert previous['status'] == 'passed' and previous['sdk_pin'] == pin
assert previous['questions'] == 187 and previous['replayed_points_per_reader'] == 52
assert previous['fresh_sdk_only_readers'] == 2 and previous['refusal_controls'] == 11 and previous['solver_exchanges'] == 0
prior_retained = read(E / 'prior-retained-readers-qualification.json')
assert prior_retained['status'] == 'passed' and prior_retained['sdk_pin'] == pin
assert prior_retained['recorded_producer_sdk_pin'] == parent['baseline_sdk_pin']
assert prior_retained['records'] == 12 and prior_retained['fresh_sdk_only_readers'] == 2
assert prior_retained['refusal_controls'] == 12 and prior_retained['solver_exchanges'] == prior_retained['oracle_calls'] == 0
native = read(E / 'native.json')
before = {row['id']: row for row in read(P / 'evidence/word-integration/native.json')['rows']}
assert native['compiler-proof-authority'] is False and len(native['rows']) == 187
assert set(before) == {row['id'] for row in native['rows']}
differences = []
for row in native['rows']:
    old = before[row['id']]
    assert row['roots'] == old['roots'] and row['standard-identity'] == old['standard-identity']
    for engine in ('z3', 'oxiz'):
        current, prior = row[engine], old[engine]
        assert current['identity']['sdk'] == pin['sdk'] and current['identity']['backend'] == engine
        for key in ('worker-sha256', 'library-sha256'):
            assert current['identity'][key] == prior['identity'][key]
        for key in ('solver-status', 'verdict', 'phase', 'observation-basis'):
            if current.get(key) != prior.get(key):
                differences.append({'id': row['id'], 'backend': engine, 'field': key, 'before': prior.get(key), 'after': current.get(key)})
        if current['validation'].get('status') != prior['validation'].get('status'):
            differences.append({'id': row['id'], 'backend': engine, 'field': 'validation.status',
                                'before': prior['validation'].get('status'), 'after': current['validation'].get('status')})
(E / 'native-differences.json').write_text(json.dumps(differences, indent=2) + '\n')
assert not differences, differences
packets = read(E / 'packets.json')
assert packets['records'] == 12 and len(packets['rows']) == 12
assert packets['manual-schema-preload'] is False and packets['source-payload-execution'] is False
assert packets['checked-native-execution'] is False and packets['compiler-proof-authority'] is False
assert (E / 'packets-command.json').stat().st_mtime_ns <= (E / 'packets.json').stat().st_mtime_ns <= (E / 'packets-exit.json').stat().st_mtime_ns
comparison = read(E / 'native-comparison.json')
assert comparison['status'] == 'passed' and comparison['sdk_pin'] == pin and comparison['questions'] == 187
assert comparison['differences'] == [] and comparison['native_sha256'] == sha(E / 'native.json')
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
recipe = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + recipe], cwd=R) == Path(__file__).read_bytes()
report = {'schema': 'bl.scalar-integration-sdk-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin, 'baseline_sdk_pin': baseline,
          'build_linkage_sha256': sha(E / 'build-linkage.json'), 'source_changes': linkage['source_changes'],
          'parent_word_qualification_sha256': sha(P / 'evidence/word-integration/qualification.json'),
          'inherited_numeric_qualification_sha256': sha(C / 'qualification.json'), 'unchanged_numeric_source_sha256': {name: linkage['source_sha256'][name] for name in numeric_names},
          'inherited_compiler_floor_install_sha256': sha(floor_path), 'compiler_floor_files': 141,
          'stages': stages, 'assertion_runs': runs, 'beam_assertions': sum(sum(rows.values()) for rows in runs.values()),
          'preflight_namespaces': 604, 'records_qualification_sha256': sha(E / 'records-qualification.json'),
          'previous_records_qualification_sha256': sha(E / 'previous-readers-qualification.json'),
          'previous_word_records_qualification_sha256': sha(E / 'previous-word-readers-qualification.json'),
          'text_packets_sha256': sha(E / 'text-packets.json'), 'evidence_packets_sha256': sha(E / 'evidence-packets.json'),
          'focused_artifact_sha256': focused_artifacts,
          'prior_retained_qualification_sha256': sha(E / 'prior-retained-readers-qualification.json'),
          'native_questions': 187, 'native_outcome_differences': differences, 'native_comparison_sha256': sha(E / 'native-comparison.json'), 'native_sha256': sha(E / 'native.json'),
          'recipe': {'code_commit': commit, 'path': recipe, 'sha256': sha(Path(__file__))},
          'project_pin_selected': False, 'compiler_proof_authority': False,
          'scope': 'One immutable numeric-word-scalar-text SDK with a separate finite word certificate checker, conservative evidence proof allowance and explicit evidence effects: graph-native composition, resource-accounted word admission/replay, atomic owner settings, indexed selected-row lookup, versioned portable answers, nested leases, canonical/legacy/project regressions, actual durable records and fresh solver-denied readers, previous record compatibility and unchanged paired native outcomes. Numeric implementation bytes and the compiler floor inherit explicit preceding qualifications. No general native-history authentication, complete theory coverage, compiler preservation or language totality theorem is established.'}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'beam_assertions': report['beam_assertions'], 'native_questions': 187, 'project_pin_selected': False}))
