"""Qualify exact controller return theorems and fresh Beam Lisp replay."""
import json
from pathlib import Path
import re
import subprocess

import core_loop_check as bridge
from witness_kernel import theorem_audits

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-loops'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


source = read(E / 'check-source-pin.json')
for name, digest in source['sha256'].items():
    file = P / name
    committed = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + file.relative_to(R).as_posix()], cwd=R)
    require(sha(file) == digest and file.read_bytes() == committed, 'qualified Core loop source snapshot: ' + name)
checks = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', checks)}
expected = {'core-loops', 'loop', 'core-translations', 'core-terms', 'obligation', 'api', 'advanced', 'features', 'native'}
require(counts.keys() == {'formal.' + name + '-test' for name in expected}
        and '9 file(s) passed, 0 failed, 0 incoherent' in checks
        and counts['formal.core-loops-test'] == 70, 'qualified BL coverage')
for name in ('lean-checks.txt', 'prior-translation-checks.txt'):
    log = (E / name).read_text()
    require('Ran 3 tests' in log and '\nOK\n' in log, name + ' passed')
_, libraries = bridge.checked_kernel()
total = theorem_audits((E / 'total-model.txt').read_text(), {
    'LoopTotal.restricted_wellFounded', 'LoopTotal.run_restricted', 'LoopTotal.terminates'})
model = theorem_audits((E / 'core-model.txt').read_text(), {
    'CoreLoop.' + name for name in ('replacement_eval', 'Layout.plug_reads', 'put_eval',
                                    'checked_initial', 'checked_step', 'composed_loop')})
standard = bridge.terms.AXIOM_POLICIES['lean-standard']
require(all(set(deps) <= standard for deps in [*total.values(), *model.values()]) and
        'Classical.choice' in total['LoopTotal.terminates'] and 'Classical.choice' in model['CoreLoop.composed_loop'],
        'audited ranking foundation')
index = read(E / 'examples/summary.json')
archive = E / 'examples/core-loops.etf'
require(sha(archive) == index['archive']['sha256'] and archive.stat().st_size == index['archive']['bytes'], 'saved subject custody')
originals = {row['id']: row for row in index['rows']}
accepted = {row['id']: row for row in read(E / 'execution/accepted.json')}
rejected = read(E / 'execution/rejected.json')
require(len(originals) == len(accepted) == 7 and originals.keys() == accepted.keys() and len(rejected) == 2,
        'complete original and adversarial Core loop corpus')
for name, row in accepted.items():
    output = E / 'execution' / name
    packet = read(E / 'examples' / (name + '.json'))
    require(row['packet'] == packet['identity'] == originals[name]['packet'] and
            row['subject'] == packet['subject'] == originals[name]['subject'] and
            row['status'] == 'checked-core-loop-return' and row['compiler_proof_authority'] is False
            and row['iteration_bound'] is None, 'applied theorem binds exact original subject with no bound')
    require(read(output / 'result.json') == {key: value for key, value in row.items() if key != 'id'}, 'individual result identity')
    generated = output / 'CoreLoopCheck.lean'
    require(sha(generated) == row['source_sha256'] and sha(output / 'CoreLoopCheck.olean') == row['olean_sha256'],
            'applied theorem source and object custody')
    layout, original, proof_layout = bridge.validate(packet)
    bridge.verify_source(generated.read_text(), packet, (layout, original, proof_layout))
    for side, scope in [('initializer', 'InitializerCore'), ('controller', 'ControllerCore')]:
        bridge.core.verify_source((output / side / 'Check.lean').read_text(), packet[side], *layout, namespace=scope)
    bridge.terms.verify_source((output / 'entailment/Check.lean').read_text(), packet['entailment'], *proof_layout)
    require(set(row['imported_olean_sha256']) == {'initializer', 'controller', 'entailment'} and
            all(sha(output / side / 'Check.olean') == value for side, value in row['imported_olean_sha256'].items()),
            'freshly checked Core and term premises')
    require(theorem_audits((output / 'lean.txt').read_text(), bridge.AUDITS) == row['axioms'] and
            all(set(deps) <= standard for deps in row['axioms'].values()), 'composed theorem audit')
for row in rejected:
    output = E / 'execution/rejected' / row['id']
    require(row['status'] == 'not-accepted-by-Lean' and 'exactLoopQuestion' in (output / 'lean.txt').read_text()
            and not (output / 'CoreLoopCheck.olean').exists() and not (output / 'result.json').exists(),
            'failed composition keeps no success object')
fresh = read(E / 'fresh/core-loops-fresh.json')
require(fresh['archive-sha256'] == sha(archive) and {row['id'] for row in fresh['rows']} == originals.keys(),
        'all original saved subjects were reconstructed')
require(all(row['packet'] == originals[row['id']]['packet'] and row['subject'] == originals[row['id']]['subject']
            and row['status'] == 'checked-data-connection' and row['changed-precondition'] == 'rejected'
            and row['kernel-execution'] == 'not-run' for row in fresh['rows']), 'fresh replay of exact Core loop data')
native = {}
for name in ('advanced', 'features', 'native'):
    new = read(E / 'corpora' / (name + '.json'))
    prior = read(P / 'evidence/core-translations/corpora' / (name + '.json'))
    signature = lambda result: {row['id']: tuple(row[engine]['verdict'] for engine in ('z3', 'oxiz')) for row in result['cases']}
    require(signature(new) == signature(prior) and new['disagreements'] == [] and new['invalid-models'] == [],
            'unchanged backend verdicts: ' + name)
    native[name] = len(new['cases'])
require(sum(native.values()) == 187, 'all prior paired native questions')
sdk = read(P / 'sdk-pin.json')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file()
             and not any(part.startswith(('browser', 'dossier')) for part in path.relative_to(E).parts)
             and path.name != 'qualification.json'}
report = {'schema': 'enchant.formal.core-loop-qualification.v1', 'checkpoint': 24,
          'source': source, 'sdk_pin': sdk,
          'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
          'z3_library_sha256': sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so'),
          'checks': {'files': counts, 'assertions': sum(counts.values()), 'failed': 0},
          'models': {'core_loop_pin': libraries['CoreLoop'], 'loop_total_pin': libraries['LoopTotal'],
                     'audited_laws': {**total, **model}},
          'loops': {'checked': len(accepted), 'iteration_bound': None, 'rejected_substitutions': len(rejected)},
          'fresh_reconstruction': fresh, 'native_corpus_unchanged': native, 'artifacts': artifacts,
          'source_compiler_preservation': 'not-established', 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'loops': report['loops'], 'assertions': sum(counts.values()),
                  'files': len(counts), 'native_questions': sum(native.values())}))
