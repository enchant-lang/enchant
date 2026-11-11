"""Qualify the exact source handler trace proofs and their Beam Lisp replay."""
import json
from pathlib import Path
import re
import subprocess

import core_actor_check as bridge
from witness_kernel import theorem_audits

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-actors'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


source = read(E / 'check-source-pin.json')
for name, digest in source['sha256'].items():
    file = P / name
    committed = subprocess.check_output(['git', 'show', source['code_commit'] + ':' + file.relative_to(R).as_posix()], cwd=R)
    require(sha(file) == digest and file.read_bytes() == committed, 'qualified actor source snapshot: ' + name)
checks = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', checks)}
expected = {'core-actors', 'source-protocol', 'protocol', 'protocol-trace', 'source-trace',
            'obligation', 'api', 'advanced', 'features', 'native'}
require(counts.keys() == {'formal.' + name + '-test' for name in expected}
        and '10 file(s) passed, 0 failed, 0 incoherent' in checks
        and counts['formal.core-actors-test'] == 69, 'qualified BL coverage')
log = (E / 'lean-checks.txt').read_text()
require('Ran 3 tests' in log and '\nOK\n' in log, 'exact trace proof check suite')
regressions = (E / 'prior-proof-checks.txt').read_text()
require(regressions.count('Ran 3 tests') == 2 and 'Ran 4 tests' in regressions
        and regressions.count('\nOK\n') == 3, 'term, translation and loop proof regressions')
_, libraries = bridge.checked_kernel()
model = theorem_audits((E / 'model-check.txt').read_text(), {
    'ActorTrace.' + name for name in ('after_failure', 'trace_safe', 'invariant_rebase', 'checked_init', 'checked_handler')})
require(all(set(deps) <= bridge.terms.AXIOM_POLICIES['choice-free'] for deps in model.values()), 'generic trace proof axioms')
index = read(E / 'examples/summary.json')
archive = E / 'examples/core-actors.etf'
require(sha(archive) == index['archive']['sha256'] and archive.stat().st_size == index['archive']['bytes'], 'saved subject custody')
originals = {row['id']: row for row in index['rows']}
accepted = {row['id']: row for row in read(E / 'execution/accepted.json')}
rejected = read(E / 'execution/rejected.json')
require(len(originals) == len(accepted) == 6 and originals.keys() == accepted.keys() and len(rejected) == 2,
        'complete original and adversarial actor corpus')
for name, row in accepted.items():
    output = E / 'execution' / name
    packet = read(E / 'examples' / (name + '.json'))
    require(row['packet'] == packet['identity'] == originals[name]['packet'] and
            row['subject'] == packet['subject'] == originals[name]['subject'] and
            row['status'] == 'checked-core-actor-trace-safety' and row['compiler_proof_authority'] is False
            and row['trace_bound'] is None and row['initial_feasibility'] == 'not-checked', 'applied theorem scope and subject')
    require(read(output / 'result.json') == {key: value for key, value in row.items() if key != 'id'}, 'individual result identity')
    generated = output / 'CoreActorCheck.lean'
    require(sha(generated) == row['source_sha256'] and sha(output / 'CoreActorCheck.olean') == row['olean_sha256'],
            'applied theorem source and object custody')
    audits = bridge.verify_source(generated.read_text(), packet, bridge.validate(packet))
    premises, premise_audits, leaves = bridge.premises_source(packet)
    require(row['handler_count'] == len(packet['handlers']) and len(leaves) == 1 + 2 * row['handler_count']
            and row['premise_packets'] == leaves, 'all checked handler premises and the initiation proof')
    require(premises == (output / 'premises/ActorPremises.lean').read_text() and
            sha(output / 'premises/ActorPremises.lean') == row['premise_source_sha256'] and
            sha(output / 'premises/ActorPremises.olean') == row['imported_olean_sha256'], 'grouped checked premise custody')
    require(theorem_audits((output / 'lean.txt').read_text(), audits) == row['axioms'] and
            theorem_audits((output / 'premises/lean.txt').read_text(), premise_audits) == row['premise_axioms'],
            'exact theorem and premise audits')
    allowed = bridge.terms.AXIOM_POLICIES[row['axiom_policy']]
    require(all(set(deps) <= allowed for deps in [*row['axioms'].values(), *row['premise_axioms'].values()]), 'actual axiom policy')
require(sum(row['handler_count'] for row in accepted.values()) == 7
        and sum(row['axiom_policy'] == 'choice-free' for row in accepted.values()) == 3
        and sum('Classical.choice' in row['axioms']['originalHandlerTracesSafe'] for row in accepted.values()) == 3,
        'seven checked handlers and both axiom policies')
for row in rejected:
    output = E / 'execution/rejected' / row['id']
    require(row['status'] == 'not-accepted-by-Lean' and 'definitional equality' in (output / 'lean.txt').read_text()
            and (output / 'premises/ActorPremises.olean').exists()
            and not (output / 'CoreActorCheck.olean').exists() and not (output / 'result.json').exists(),
            'failed composition keeps the checked premises only')
fresh = read(E / 'fresh/core-actors-fresh.json')
require(fresh['archive-sha256'] == sha(archive) and {row['id'] for row in fresh['rows']} == originals.keys(),
        'all original saved subjects were reconstructed')
require(all(row['packet'] == originals[row['id']]['packet'] and row['subject'] == originals[row['id']]['subject']
            and row['status'] == 'checked-data-connection' and row['changed-initial'] == 'rejected'
            and row['kernel-execution'] == 'not-run' for row in fresh['rows']), 'fresh replay of exact actor trace data')
native = {}
for name in ('advanced', 'features', 'native'):
    new = read(E / 'corpora' / (name + '.json'))
    prior = read(P / 'evidence/core-loops/corpora' / (name + '.json'))
    signature = lambda result: {row['id']: tuple(row[engine]['verdict'] for engine in ('z3', 'oxiz')) for row in result['cases']}
    require(signature(new) == signature(prior) and new['disagreements'] == [] and new['invalid-models'] == [],
            'unchanged backend verdicts: ' + name)
    native[name] = len(new['cases'])
require(sum(native.values()) == 187, 'all prior paired native questions')
sdk = read(P / 'sdk-pin.json')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file()
             and not any(part.startswith(('browser', 'dossier')) for part in path.relative_to(E).parts)
             and path.name != 'qualification.json'}
report = {'schema': 'enchant.formal.core-actor-trace-qualification.v1', 'checkpoint': 25,
          'source': source, 'sdk_pin': sdk,
          'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
          'z3_library_sha256': sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so'),
          'checks': {'files': counts, 'assertions': sum(counts.values()), 'failed': 0},
          'model': {'pin': libraries['ActorTrace'], 'audited_laws': model},
          'trace_proofs': {'protocols': len(accepted), 'handlers': 7, 'trace_bound': None,
                           'choice_free': 3, 'rejected_substitutions': len(rejected)},
          'fresh_reconstruction': fresh, 'native_corpus_unchanged': native, 'artifacts': artifacts,
          'live_actor_preservation': 'not-established', 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'trace_proofs': report['trace_proofs'], 'assertions': sum(counts.values()),
                  'files': len(counts), 'native_questions': sum(native.values())}))
