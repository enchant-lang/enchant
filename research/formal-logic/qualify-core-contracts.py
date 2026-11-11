"""Check the integration receipts for exact Core contract composition."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

import core_contract_check as bridge

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-contracts'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


def commits_match(pin):
    for name, digest in pin['sha256'].items():
        path = P / name
        committed = subprocess.check_output(['git', 'show', pin['code_commit'] + ':' + path.relative_to(R).as_posix()], cwd=R)
        require(sha(path) == digest and path.read_bytes() == committed, 'qualified source snapshot: ' + name)


source = read(E / 'check-source-pin.json')
commits_match(source)
checks = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', checks)}
require(len(counts) == 36 and '36 file(s) passed, 0 failed, 0 incoherent' in checks
        and counts['formal.core-contracts-test'] == 96, 'complete BL integration suite')
for name, tests in [('lean-checks.txt', 3), ('prior-core-checks.txt', 5)]:
    log = (E / name).read_text()
    require(f'Ran {tests} tests' in log and '\nOK\n' in log, name + ' passed')

_, libraries = bridge.checked_kernel(True)
model = bridge.witnesses.theorem_audits((E / 'model-check.txt').read_text(), {
    'CoreContract.' + name for name in ['rename_eval', 'rename_entails', 'allowed_eval', 'named_allowed',
                                      'checked_claim_holds', 'composed_contract']})
require(all(set(deps) <= bridge.terms.AXIOM_POLICIES['choice-free'] for deps in model.values()), 'generic contract model axiom policy')

index = read(E / 'examples/summary.json')
archive = E / 'examples/core-contracts.etf'
require(sha(archive) == index['archive']['sha256'] and archive.stat().st_size == index['archive']['bytes'], 'saved BL subject custody')
originals = {row['id']: row for row in index['rows']}
accepted = {row['id']: row for row in read(E / 'execution/accepted.json')}
rejected = read(E / 'execution/rejected.json')
require(len(originals) == len(accepted) == 8 and originals.keys() == accepted.keys() and len(rejected) == 5, 'complete contract corpus')
for name, row in accepted.items():
    output = E / 'execution' / name
    packet = read(E / 'examples' / (name + '.json'))
    require(row['packet'] == packet['identity'] == originals[name]['packet'] and row['subject'] == packet['core']['subject']
            and row['status'] == 'checked-core-contract' and row['compiler_proof_authority'] is False, 'applied theorem binds its original subject')
    require(row['witness'] == originals[name]['witness'] and
            ('originalCoreHasAdmittedOutcome' in row['axioms']) == (row['witness'] is not None), 'checked admission scope')
    require(read(output / 'result.json') == {key: value for key, value in row.items() if key != 'id'}, 'individual result identity')
    require(sha(output / 'CoreContractCheck.lean') == row['source_sha256'] and sha(output / 'CoreContractCheck.olean') == row['olean_sha256']
            and sha(output / 'core/Check.olean') == row['imported_core_sha256']
            and sha(output / 'entailment/Check.olean') == row['imported_entailment_sha256'], 'applied theorem and premises custody')
    bridge.verify_source((output / 'CoreContractCheck.lean').read_text(), packet, *bridge.validate(packet))
    require(bridge.witnesses.theorem_audits((output / 'lean.txt').read_text(), set(row['axioms'])) == row['axioms'], 'composed theorem audit')
require(sum(row['witness'] is not None for row in accepted.values()) == 6
        and sum(row['axiom_policy'] == 'choice-free' for row in accepted.values()) == 7, 'admission and axiom coverage')
require('Classical.choice' in accepted['allowed-division']['axioms']['originalCoreSatisfiesContract']
        and accepted['vacuous']['witness'] is None, 'signed quotient and vacuity boundaries')
for row in rejected:
    root = E / 'execution/rejected' / row['id']
    require(row['status'] == 'not-accepted-by-Lean' and row['theorem'] in (root / 'lean.txt').read_text()
            and not (root / 'CoreContractCheck.olean').exists() and not (root / 'result.json').exists(), 'failed composition evidence')

fresh = read(E / 'fresh/core-contracts-fresh.json')
require(len(fresh['rows']) == 8 and set(fresh['calibration']) == set(fresh['checking-window']) == {'proof-search', 'formal-native-session'}
        and all(value > 0 for value in fresh['calibration'].values()) and all(value == 0 for value in fresh['checking-window'].values()), 'calibrated fresh replay')
require(all(row['packet'] == originals[row['id']]['packet'] and row['status'] == 'checked-data-connection'
            and row['rehashed-policy'] == 'rejected' and row['kernel-execution'] == 'not-run' for row in fresh['rows']), 'original packet and changed policy replay')

native = {}
for name in ['advanced', 'features', 'native']:
    new = read(E / 'corpora' / (name + '.json'))
    prior = read(P / 'evidence/core-terms/corpora' / (name + '.json'))
    signature = lambda result: {row['id']: tuple(row[engine]['verdict'] for engine in ['z3', 'oxiz']) for row in result['cases']}
    require(signature(new) == signature(prior) and new['disagreements'] == [] and new['invalid-models'] == [], 'native regression: ' + name)
    native[name] = len(new['cases'])
require(sum(native.values()) == 187, 'full native theory corpus')

sdk = read(P / 'sdk-pin.json')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file()
             and not any(part.startswith(('browser', 'dossier')) for part in path.relative_to(E).parts)
             and path.name != 'qualification.json'}
report = {'schema': 'enchant.formal.core-contract-qualification.v1', 'checkpoint': 22,
          'source': source, 'sdk_pin': sdk,
          'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
          'z3_library_sha256': sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so'),
          'checks': {'files': counts, 'assertions': sum(counts.values()), 'failed': 0},
          'model': {'pin': libraries['CoreContract'], 'audited_laws': model},
          'contracts': {'checked': len(accepted), 'with_admitted_outcome': 6, 'choice_free': 7, 'rejected_substitutions': len(rejected)},
          'fresh_reconstruction': fresh, 'native_corpus_unchanged': native, 'artifacts': artifacts,
          'source_compiler_preservation': 'not-established', 'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'contracts': report['contracts'], 'assertions': sum(counts.values()), 'files': len(counts), 'native_questions': sum(native.values())}))
