"""Qualify the exact translation theorems and their original BL subjects."""
import json
from pathlib import Path
import re
import subprocess

import core_translation_check as bridge

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-translations'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


source = read(E / 'check-source-pin.json')
for name, digest in source['sha256'].items():
    file = P / name
    committed = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + file.relative_to(R).as_posix()], cwd=R)
    require(sha(file) == digest and file.read_bytes() == committed, 'qualified translation source snapshot: ' + name)
checks = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', checks)}
expected = {'core-translations', 'translation', 'core-terms', 'core-contracts', 'connection',
            'obligation', 'api', 'advanced', 'features', 'native'}
require(counts.keys() == {'formal.' + name + '-test' for name in expected}
        and '10 file(s) passed, 0 failed, 0 incoherent' in checks
        and counts['formal.core-translations-test'] == 96, 'qualified BL coverage')
require('Ran 3 tests' in (E / 'lean-checks.txt').read_text() and '\nOK\n' in (E / 'lean-checks.txt').read_text(),
        'exact translation check suite')
regression = (E / 'prior-proof-checks.txt').read_text()
require('Ran 5 tests' in regression and 'Ran 3 tests' in regression and regression.count('\nOK\n') == 2,
        'earlier Core correspondence and contract check suites')

_, libraries = bridge.checked_kernel()
model_audits = bridge.theorem_audits((E / 'model-check.txt').read_text(), {
    'CoreTranslation.' + theorem for theorem in ['eval_covered', 'decode_covered', 'payload_equal_eval',
                                                'checked_comparison_equal', 'composed_translation']})
choice_free = bridge.terms.AXIOM_POLICIES['choice-free']
require(all(set(deps) <= choice_free for deps in model_audits.values()), 'general composition proof axioms')
index = read(E / 'examples/summary.json')
archive = E / 'examples/core-translations.etf'
require(sha(archive) == index['archive']['sha256'] and archive.stat().st_size == index['archive']['bytes'], 'saved subject custody')
originals = {row['id']: row for row in index['rows']}
accepted = {row['id']: row for row in read(E / 'execution/accepted.json')}
rejected = read(E / 'execution/rejected.json')
require(len(originals) == len(accepted) == 9 and originals.keys() == accepted.keys() and len(rejected) == 2,
        'complete original and adversarial translation corpus')
for name, row in accepted.items():
    output = E / 'execution' / name
    packet = read(E / 'examples' / (name + '.json'))
    require(row['packet'] == packet['identity'] == originals[name]['packet'] and
            row['subject'] == packet['subject'] == originals[name]['subject'] and
            row['status'] == 'checked-core-translation' and row['compiler_proof_authority'] is False,
            'applied theorem binds the original pair and question')
    require(read(output / 'result.json') == {key: value for key, value in row.items() if key != 'id'}, 'individual result identity')
    generated = output / 'CoreTranslationCheck.lean'
    require(sha(generated) == row['source_sha256'] and sha(output / 'CoreTranslationCheck.olean') == row['olean_sha256'],
            'applied theorem source and object custody')
    layouts = bridge.validate(packet)
    bridge.verify_source(generated.read_text(), packet, *layouts)
    for side, scope in [('before', 'BeforeCore'), ('after', 'AfterCore')]:
        bridge.core.verify_source((output / side / 'Check.lean').read_text(), packet[side], *layouts[0], namespace=scope)
    bridge.terms.verify_source((output / 'entailment/Check.lean').read_text(), packet['entailment'], *layouts[1])
    require(set(row['imported_olean_sha256']) == {'before', 'after', 'entailment'} and
            all(sha(output / side / 'Check.olean') == value for side, value in row['imported_olean_sha256'].items()),
            'fresh Core and entailment premise custody')
    require(bridge.theorem_audits((output / 'lean.txt').read_text(), bridge.AUDITS) == row['axioms'], 'composed theorem audit')
require(sum(row['axiom_policy'] == 'choice-free' for row in accepted.values()) == 8 and
        'Classical.choice' in accepted['signed-quotient']['axioms']['originalCoreOutcomesEqual'], 'choice-free and signed quotient proofs')
for row in rejected:
    output = E / 'execution/rejected' / row['id']
    require(row['status'] == 'not-accepted-by-Lean' and 'exactTranslationQuestion' in (output / 'lean.txt').read_text()
            and not (output / 'CoreTranslationCheck.olean').exists() and not (output / 'result.json').exists(),
            'failed equality keeps no composed success object')

fresh = read(E / 'fresh/core-translations-fresh.json')
require(fresh['archive-sha256'] == sha(archive) and {row['id'] for row in fresh['rows']} == originals.keys(),
        'all original saved subjects were reconstructed')
require(all(row['packet'] == originals[row['id']]['packet'] and row['subject'] == originals[row['id']]['subject']
            and row['status'] == 'checked-data-connection' and row['changed-precondition'] == 'rejected'
            and row['kernel-execution'] == 'not-run' for row in fresh['rows']), 'fresh replay of exact translation data')

native = {}
for name in ('advanced', 'features', 'native'):
    new = read(E / 'corpora' / (name + '.json'))
    prior = read(P / 'evidence/core-contracts/corpora' / (name + '.json'))
    signature = lambda result: {row['id']: tuple(row[engine]['verdict'] for engine in ('z3', 'oxiz')) for row in result['cases']}
    require(signature(new) == signature(prior) and new['disagreements'] == [] and new['invalid-models'] == [],
            'unchanged backend verdicts: ' + name)
    native[name] = len(new['cases'])
require(sum(native.values()) == 187, 'all prior paired backend questions')
sdk = read(P / 'sdk-pin.json')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file()
             and not any(part.startswith(('browser', 'dossier')) for part in path.relative_to(E).parts)
             and path.name != 'qualification.json'}
report = {'schema': 'enchant.formal.core-translation-qualification.v1', 'checkpoint': 23,
          'source': source, 'sdk_pin': sdk,
          'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
          'z3_library_sha256': sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so'),
          'checks': {'files': counts, 'assertions': sum(counts.values()), 'failed': 0},
          'model': {'pin': libraries['CoreTranslation'], 'audited_laws': model_audits},
          'translations': {'checked': len(accepted), 'choice_free': 8, 'rejected_substitutions': len(rejected)},
          'fresh_reconstruction': fresh, 'native_corpus_unchanged': native, 'artifacts': artifacts,
          'source_compiler_preservation': 'not-established', 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'translations': report['translations'], 'assertions': sum(counts.values()),
                  'files': len(counts), 'native_questions': sum(native.values())}))
