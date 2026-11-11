"""Qualify the term-native bridge from owned observation receipts to checked Core."""
import json
from pathlib import Path
import re
import subprocess

import core_observation_check as bridge
from witness_kernel import theorem_audits

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-observations'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


source = read(E / 'check-source-pin.json')
for name, digest in source['sha256'].items():
    file = P / name
    committed = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + file.relative_to(R).as_posix()], cwd=R)
    require(sha(file) == digest and file.read_bytes() == committed, 'qualified observation source snapshot: ' + name)

checks = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', checks)}
expected = {'core-observations', 'core-actors', 'runtime-protocol', 'source-protocol', 'source-trace', 'api',
            'advanced', 'features', 'native'}
require(counts.keys() == {'formal.' + name + '-test' for name in expected}
        and '9 file(s) passed, 0 failed, 0 incoherent' in checks, 'qualified BL coverage')
for log, tests in [('lean-checks.txt', 4), ('prior-actor-checks.txt', 3)]:
    transcript = (E / log).read_text()
    require(f'Ran {tests} tests' in transcript and '\nOK\n' in transcript, 'successful Lean suites: ' + log)
cli = read(E / 'cli-check.json')
require(cli['status'] == 'checked-recorded-core-trace' and cli['recorded_safety'] == 'safe'
        and cli['checked_prefixes'] == 5 and cli['all_traces_safety_packet'] is not None, 'documented CLI entry point')

index = read(E / 'examples/summary.json')
archive = E / 'examples/core-observations.etf'
require(sha(archive) == index['archive']['sha256'] and archive.stat().st_size == index['archive']['bytes'],
        'saved original receipt custody')
originals = {row['id']: row for row in index['rows']}
results = {row['id']: row for row in read(E / 'execution/accepted.json')}
require(len(originals) == 7 and results.keys() == originals.keys() | {'bank-linked'}, 'complete recording and applied proof corpus')
require(set(originals) == {'bank', 'context-counter', 'overlapping-message-names', 'full-idle', 'initial-only', 'failure', 'unsafe-return'},
        'coverage of owned sequential adapter examples')
for name, result in results.items():
    linked = name == 'bank-linked'
    original_name = 'bank' if linked else name
    original = originals[original_name]
    packet = read(E / 'examples' / (original_name + '.json'))
    layouts = bridge.validate(packet)
    folder = E / 'execution' / name
    generated = folder / 'CoreObservedTrace.lean'
    require(read(folder / 'result.json') == {key: value for key, value in result.items() if key != 'id'},
            'individual observation result identity')
    require(result['status'] == 'checked-recorded-core-trace' and result['subject'] == packet['model']['subject']
            and result['packet'] == packet['identity'] == original['packet']
            and result['observation'] == packet['observation'] and original['receipt'] == packet['observation']['receipt']
            and result['events'] == original['events'] == len(packet['frames']) - 1
            and result['checked_prefixes'] == len(packet['frames']) and result['compiler_proof_authority'] is False
            and result['execution_authenticity'] == 'observer-trusted'
            and result['receipt_connection'] == 'requires-fresh-BL-reconstruction'
            and result['universal_runtime_refinement'] == 'not-established', 'exact observation subject and checked extent')
    require(sha(generated) == result['source_sha256']
            and sha(folder / 'CoreObservedTrace.olean') == result['olean_sha256'], 'checked trace proof custody')
    audits, verdict, failure, violation = bridge.verify_source(generated.read_text(), packet, layouts, linked)
    require((verdict, failure, violation) == (result['recorded_safety'], result['first_failure_at'], result['first_invariant_violation_at'])
            and verdict == {'holds': 'safe', 'violated': 'unsafe'}[original['runtime-safety']],
            'Core check of recorded prefix safety')
    allowed = bridge.terms.AXIOM_POLICIES['lean-standard' if linked else 'choice-free']
    require(result['axiom_policy'] == ('lean-standard' if linked else 'choice-free')
            and theorem_audits((folder / 'lean.txt').read_text(), audits) == result['axioms']
            and all(set(axioms) <= allowed for axioms in result['axioms'].values()), 'actual checked axiom dependencies')
    if linked:
        checked = read(folder / 'safety/result.json')
        universal = read(E.parent / 'core-actors/examples/bank.json')
        require(result['all_traces_safety_packet'] == checked['packet'] == universal['identity']
                and packet['model'] == bridge.actor.model_data(universal)
                and result['all_traces_olean_sha256'] == checked['olean_sha256'] == sha(folder / 'safety/CoreActorCheck.olean')
                and all('Classical.choice' in result['axioms'][f'CoreObservedTrace.recordedSafe{n}']
                        for n in range(result['checked_prefixes'])), 'fresh exact bank theorem and its applications')
    else:
        require(result['all_traces_safety_packet'] is None and result['all_traces_olean_sha256'] is None,
                'standalone trace verification needs no safety theorem')

require(results['full-idle']['checked_prefixes'] == 65 and results['initial-only']['checked_prefixes'] == 1
        and results['failure']['first_failure_at'] == 2 and results['unsafe-return']['first_invariant_violation_at'] == 1,
        'check the full cap, initial-only, and both kinds of unsafe run')
rejected = read(E / 'execution/rejected.json')
require(len(rejected) == 7 and all(row['status'] == 'not-accepted-by-Lean' for row in rejected), 'seven resealed false claims')
for row in rejected:
    folder = E / 'execution/rejected' / row['id']
    require('error:' in (folder / 'lean.txt').read_text() and not (folder / 'CoreObservedTrace.olean').exists()
            and not (folder / 'result.json').exists(), 'Lean rejected changed data and retired stale success')
label_only = read(E / 'execution/changed-receipt-label/result.json')
require(label_only['observation']['receipt'] == '0' * 64 and label_only['recorded_safety'] == 'safe'
        and label_only['receipt_connection'] == 'requires-fresh-BL-reconstruction', 'independent checker claims no receipt custody')

fresh = read(E / 'fresh/core-observations-fresh.json')
require(fresh['archive-sha256'] == sha(archive) and {row['id'] for row in fresh['rows']} == originals.keys()
        and len(fresh['rows']) == len(originals), 'saved receipt recheck coverage')
for row in fresh['rows']:
    original = originals[row['id']]
    require(row['packet'] == original['packet'] and row['receipt'] == original['receipt']
            and row['status'] == 'checked-data-connection' and row['changed-receipt'] == 'rejected'
            and row['kernel-execution'] == 'not-run', 'fresh exact receipt reconstruction')

native = {}
for name in ('advanced', 'features', 'native'):
    new = read(E / 'corpora' / (name + '.json'))
    prior = read(E.parent / 'core-actors/corpora' / (name + '.json'))
    def signature(result):
        return {row['id']: tuple(row[engine]['verdict'] for engine in ('z3', 'oxiz')) for row in result['cases']}
    require(signature(new) == signature(prior) and new['disagreements'] == [] and new['invalid-models'] == [],
            'unchanged paired backend verdicts: ' + name)
    native[name] = len(new['cases'])
require(sum(native.values()) == 187, 'all prior paired native questions')

sdk = read(P / 'sdk-pin.json')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file()
             and not any(part.startswith(('browser', 'dossier')) for part in path.relative_to(E).parts)
             and path.name != 'qualification.json'}
report = {'schema': 'enchant.formal.core-observation-qualification.v1', 'checkpoint': 26, 'source': source, 'sdk_pin': sdk,
          'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
          'z3_library_sha256': sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so'),
          'checks': {'files': counts, 'assertions': sum(counts.values()), 'failed': 0},
          'recorded_traces': {'runs': len(originals), 'prefixes': sum(results[name]['checked_prefixes'] for name in originals),
                              'unsafe_runs': 2, 'rejected_substitutions': len(rejected),
                              'linked_bank_prefixes': results['bank-linked']['checked_prefixes']},
          'fresh_reconstruction': fresh, 'native_corpus_unchanged': native, 'artifacts': artifacts,
          'execution_authenticity': 'observer-trusted', 'universal_runtime_refinement': 'not-established',
          'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'recorded_traces': report['recorded_traces'], 'assertions': sum(counts.values()),
                  'files': len(counts), 'native_questions': sum(native.values())}))
