"""Qualify original native counterexamples, exact projections and recorded Core traces."""
import json
from pathlib import Path
import re
import subprocess

import core_counterexample_check as bridge
from witness_kernel import theorem_audits

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-counterexamples'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


source = read(E / 'check-source-pin.json')
for name, digest in source['sha256'].items():
    file = P / name
    committed = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + file.relative_to(R).as_posix()], cwd=R)
    require(sha(file) == digest and file.read_bytes() == committed, 'qualified counterexample source snapshot: ' + name)
checks = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', checks)}
expected = {'core-counterexamples', 'core-observations', 'witness', 'protocol-trace', 'source-trace', 'api',
            'advanced', 'features', 'native'}
require(counts.keys() == {'formal.' + name + '-test' for name in expected}
        and '9 file(s) passed, 0 failed, 0 incoherent' in checks, 'qualified BL coverage')
for filename, tests in [('lean-checks.txt', 3), ('prior-observation-checks.txt', 4)]:
    transcript = (E / filename).read_text()
    require(f'Ran {tests} tests' in transcript and '\nOK\n' in transcript, 'successful proof regressions: ' + filename)
index = read(E / 'examples/summary.json')
archive = E / 'examples/core-counterexamples.etf'
require(sha(archive) == index['archive']['sha256'] and archive.stat().st_size == index['archive']['bytes'],
        'saved original native observations and receipts')
originals = {row['id']: row for row in index['rows']}
results = {row['id']: row for row in read(E / 'execution/accepted.json')}
require(len(originals) == len(results) == 12 and originals.keys() == results.keys(), 'all six paired counterexamples')
allowed = bridge.terms.AXIOM_POLICIES['choice-free']
for name, row in results.items():
    original = originals[name]
    packet = read(E / 'examples' / (name + '.json'))
    layout = bridge.validate(packet)
    folder = E / 'execution' / name
    generated = folder / 'CoreCounterexampleCheck.lean'
    require(read(folder / 'result.json') == {key: value for key, value in row.items() if key != 'id'}, 'individual theorem result')
    require(row['status'] == 'checked-original-query-and-unsafe-core-run'
            and row['packet'] == packet['identity'] == original['packet'] and row['subject'] == packet['subject']
            and row['subject']['identity'] == original['subject'] and row['subject']['query'] == original['query']
            and row['discovery'] == packet['discovery'] and row['discovery']['engine'] == original['engine']
            and row['query_witness'] == packet['witness']['identity'] and row['recorded_trace'] == packet['execution']['identity']
            and row['receipt'] == original['receipt'] == packet['execution']['observation']['receipt']
            and row['events'] == original['events'] and row['checked_prefixes'] == row['events'] + 1,
            'exact original question, witness and recorded execution')
    require(sha(generated) == row['source_sha256'] and sha(folder / 'CoreCounterexampleCheck.olean') == row['olean_sha256'],
            'composed proof source and object custody')
    audits = bridge.verify_source(generated.read_text(), packet, layout)
    require(theorem_audits((folder / 'lean.txt').read_text(), audits) == row['axioms']
            and row['axiom_policy'] == 'choice-free' and all(set(deps) <= allowed for deps in row['axioms'].values()),
            'actual composed theorem audit')
    query = read(folder / 'witness/result.json')
    trace = read(folder / 'trace/result.json')
    require(query['status'] == 'checked-term-satisfiability' and query['packet'] == packet['witness']['identity']
            and query['proof_olean_sha256'] == row['imported_query_olean_sha256'] == sha(folder / 'witness/Check.olean')
            and trace['status'] == 'checked-recorded-core-trace' and trace['recorded_safety'] == 'unsafe'
            and trace['packet'] == packet['execution']['identity'] and trace['checked_prefixes'] == row['checked_prefixes']
            and trace['olean_sha256'] == row['imported_trace_olean_sha256'] == sha(folder / 'trace/CoreObservedTrace.olean'),
            'freshly checked imported premise objects')
    witness_layout = bridge.witnesses.validate(packet['witness'])
    bridge.witnesses.verify_source((folder / 'witness/Check.lean').read_text(), packet['witness'], *witness_layout)
    require(theorem_audits((folder / 'witness/lean.txt').read_text(),
                          {'packetAccepted', 'originalContextHolds', 'originalContextSatisfiable'}) == query['axioms']
            and all(set(deps) <= allowed for deps in query['axioms'].values()), 'fresh witness theorem audit')
    trace_layout = bridge.observed.validate(packet['execution'])
    trace_audits, verdict, failed, violated = bridge.observed.verify_source((folder / 'trace/CoreObservedTrace.lean').read_text(),
                                                                        packet['execution'], trace_layout, False)
    require(theorem_audits((folder / 'trace/lean.txt').read_text(), trace_audits) == trace['axioms']
            and (verdict, failed, violated) == ('unsafe', row['first_failure_at'], row['first_invariant_violation_at']),
            'exact recorded Core trace and its unsafe prefix')
    for prefix in range(row['checked_prefixes']):
        require(f'CoreCounterexampleCheck.projectedState{prefix}Matches' in row['axioms'], 'every recorded state is connected')
    require(row['completed_bindings'] == len(packet['bindings'])
            and row['extra_observation_bindings'] == len(packet['bindings']) - len(packet['witness']['bindings'])
            and {key: count for key, count in row['completion_origins'].items() if count} == original['completion'],
            'all completion origins survive export')
    require(row['query_and_receipt_connection'] == 'requires-fresh-BL-reconstruction'
            and row['backend_provenance'] == 'claimed-engine-response' and row['execution_authenticity'] == 'observer-trusted'
            and row['general_unrolling_correspondence'] == row['universal_runtime_refinement'] == 'not-established'
            and row['compiler_proof_authority'] is False, 'explicit scope and remaining connections')
cases = {row['case'] for row in originals.values()}
require(len(cases) == 6 and sum(row['checked_prefixes'] for row in results.values()) == 26, 'six cases and 26 checked prefixes')
for case in cases:
    pair = [row for row in originals.values() if row['case'] == case]
    require(len(pair) == 2 and {row['engine'] for row in pair} == {'z3', 'oxiz'}
            and pair[0]['query'] == pair[1]['query'] and pair[0]['subject'] == pair[1]['subject'],
            'both engines received the same exact original source query')
require(results['overdraft-oxiz']['completion_origins']['explicit-replay-completion'] > 0
        and results['overdraft-oxiz']['extra_observation_bindings'] > 0, 'watch-only opaque inputs retain explicit completion')

rejected = read(E / 'execution/rejected.json')
require(len(rejected) == 3, 'all mismatched premise challenges')
for row in rejected:
    folder = E / 'execution/rejected' / row['id']
    require(row['status'] == 'not-accepted-by-Lean' and row['query_witness'] == row['unsafe_trace'] == 'checked'
            and read(folder / 'witness/result.json')['status'] == 'checked-term-satisfiability'
            and read(folder / 'trace/result.json')['recorded_safety'] == 'unsafe'
            and 'error:' in (folder / 'lean.txt').read_text()
            and not (folder / 'CoreCounterexampleCheck.olean').exists() and not (folder / 'result.json').exists(),
            'valid premises cannot authorize a false value connection')
fresh = read(E / 'fresh/core-counterexamples-fresh.json')
require(fresh['archive-sha256'] == sha(archive) and len(fresh['rows']) == len(originals)
        and {row['id'] for row in fresh['rows']} == originals.keys(), 'all original native responses and receipts reconnect')
sdk = read(P / 'sdk-pin.json')
worker = sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker')
z3_library = sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so')
for row in fresh['rows']:
    original = originals[row['id']]
    packet = read(E / 'examples' / (row['id'] + '.json'))
    backend = row['backend-identity']
    require(row['packet'] == original['packet'] and row['receipt'] == original['receipt']
            and row['subject'] == original['subject'] and row['native-result'] == packet['discovery']['result']
            and row['status'] == 'checked-data-connection' and row['changed-query'] == 'rejected'
            and row['kernel-execution'] == 'not-run', 'fresh original subject/native/receipt reconstruction')
    require(backend['backend'] == original['engine'] and backend['worker-sha256'] == worker and backend['sdk'] == sdk['sdk']
            and backend['library-sha256'] == (z3_library if original['engine'] == 'z3' else None),
            'recorded native response artifact identity')
cli = read(E / 'cli-check.json')
require(cli['status'] == 'checked-original-query-and-unsafe-core-run'
        and cli['packet'] == originals['initial-violation-oxiz']['packet'] and cli['checked_prefixes'] == 1, 'public capped entry point')
native = {}
for name in ('advanced', 'features', 'native'):
    new = read(E / 'corpora' / (name + '.json'))
    prior = read(E.parent / 'core-observations/corpora' / (name + '.json'))
    def signature(result):
        return {row['id']: tuple(row[engine]['verdict'] for engine in ('z3', 'oxiz')) for row in result['cases']}
    require(signature(new) == signature(prior) and new['disagreements'] == [] and new['invalid-models'] == [],
            'unchanged paired native verdicts: ' + name)
    native[name] = len(new['cases'])
require(sum(native.values()) == 187, 'all shared native questions')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file()
             and not any(part.startswith(('browser', 'dossier')) for part in path.relative_to(E).parts)
             and path.name != 'qualification.json'}
report = {'schema': 'enchant.formal.core-counterexample-qualification.v1', 'checkpoint': 27, 'source': source,
          'sdk_pin': sdk, 'worker_sha256': worker, 'z3_library_sha256': z3_library,
          'checks': {'files': counts, 'assertions': sum(counts.values()), 'failed': 0},
          'counterexamples': {'original_queries': len(cases), 'engines': ['z3', 'oxiz'], 'composed_runs': len(results),
                              'checked_prefixes': 26, 'choice_free': len(results), 'rejected_pairings': len(rejected)},
          'fresh_reconstruction': fresh, 'native_corpus_unchanged': native, 'artifacts': artifacts,
          'execution_authenticity': 'observer-trusted', 'general_unrolling_correspondence': 'not-established',
          'universal_runtime_refinement': 'not-established', 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'counterexamples': report['counterexamples'], 'assertions': sum(counts.values()),
                  'files': len(counts), 'native_questions': sum(native.values())}))
