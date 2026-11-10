"""Qualify the exact Core term correspondence and its scoped artifacts."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

import core_term_check as bridge

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/core-terms'
sha, require = bridge.k.sha, bridge.require


def read(path):
    return json.loads(path.read_text())


snapshot = read(E / 'check-source-pin.json')
for name, digest in snapshot['sha256'].items():
    source = P / name
    committed = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + source.relative_to(R).as_posix()], cwd=R)
    require(sha(source) == digest and source.read_bytes() == committed, 'qualification source changed: ' + name)
log = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', log)}
require(len(counts) == 35 and '35 file(s) passed, 0 failed, 0 incoherent' in log and counts['formal.core-terms-test'] == 159, 'full Core term integration')
for name in ['bridge-check.txt', 'prior-mixed-check.txt']:
    transcript = (E / name).read_text()
    require('Ran 5 tests' in transcript and '\nOK\n' in transcript, name + ' successful tests')
prior = read(E / 'prior-mixed/results.json')
require(len(prior) == 17 and sum(len(row['checked']) for row in prior) == 39 and sum(len(row['checked_instances']) for row in prior) == 11, 'prior mixed obligation coverage')
pin = read(P / 'metatheory/core-terms-pin.json')
libraries = {'CoreTerms': pin}
for module, dependency in pin['libraries'].items():
    file = P / dependency['pin']
    require(sha(file) == dependency['sha256'], 'model dependency pin')
    libraries[module] = read(file)
require(set(libraries) == {'Core', 'CoreTerms', 'Terms', 'Refutation'}, 'complete model library set')
for library in libraries.values():
    for field in ['source', 'compiled']:
        require(sha(P / library[field]['path']) == library[field]['sha256'], 'model source and compiled object pin')
tool = read(P / 'metatheory/tool-pin.json')
require(sha(Path(tool['path']) / 'bin/lean') == tool['binary_sha256'], 'Lean binary pin')
expected_laws = {'CoreTerms.' + name for name in ['agrees_returned', 'agrees_raised', 'agrees_choice', 'proposition_choice', 'bind_choice',
                 'strict_values', 'strict_left_none', 'strict_right_none', 'partial_values', 'partial_left_none', 'partial_right_none',
                 'select_some', 'select_none', 'select_values', 'eval_choice', 'quotient_value', 'remainder_value', 'modulus_value',
                 'apply_quot', 'apply_rem', 'apply_mod']}
audit = bridge.proof_tools.theorem_audits((E / 'model-check.txt').read_text(), expected_laws)
require(all(set(deps) <= bridge.terms.AXIOM_POLICIES['lean-standard'] for deps in audit.values()), 'audited model axioms')
require(sum('Classical.choice' in deps for deps in audit.values()) == 6, 'signed arithmetic dependencies')
archive = read(E / 'examples/summary.json')
file = E / 'examples/core-terms.etf'
require(sha(file) == archive['archive']['sha256'] and file.stat().st_size == archive['archive']['bytes'], 'archived original subject custody')
examples = {row['id']: row for row in archive['rows']}
accepted = {row['id']: row for row in read(E / 'execution/accepted.json')}
rejected = read(E / 'execution/rejected.json')
require(len(examples) == len(accepted) == 34 and set(examples) == set(accepted) and len(rejected) == 6, 'complete applied proof corpus')
require(Counter(row['core-profile'] for row in examples.values()) == Counter({'bl/core-int-bool-outcomes-v1': 23, 'bl/core-record-outcomes-v2': 11}), 'scalar and record proof profiles')
for name, row in accepted.items():
    packet = read(E / 'examples' / (name + '.json'))
    integers, booleans = bridge.validate(packet)
    root = E / 'execution' / name
    bridge.verify_source((root / 'Check.lean').read_text(), packet, integers, booleans)
    require(sha(root / 'Check.lean') == row['source_sha256'] and sha(root / 'Check.olean') == row['olean_sha256'], 'applied theorem source and object custody')
    require(row['packet'] == packet['identity'] == examples[name]['packet'] and row['subject'] == packet['subject'] == examples[name]['subject'], 'proof binds exact packet and subject')
    require(row['status'] == 'checked-core-term-correspondence' and row['core_data_model_codec'] == 'reviewed' and row['compiler_proof_authority'] is False, 'checked Core model scope')
    require(set(row['axioms']) == {'coreTermCorrespondence', 'errorCatalogueRoundTrip'} and
            all(set(deps) <= bridge.terms.AXIOM_POLICIES[row['axiom_policy']] for deps in row['axioms'].values()), 'actual outcome and catalogue theorem audits')
for row in rejected:
    root = E / 'execution/rejected' / row['id']
    require(row['status'] == 'not-accepted-by-Lean' and (root / 'lean.txt').is_file() and
            not (root / 'Check.olean').exists() and not (root / 'result.json').exists(), 'failed semantic proof cannot retain an accepted receipt')
ignored = read(E / 'execution/ignored-failure-payload/result.json')
require(ignored['status'] == 'checked-core-term-correspondence' and ignored['packet'] != examples['named-first-error']['packet'], 'failure payload scope')
policy = E / 'execution/choice-free-quotient'
require('Classical.choice' in (policy / 'lean.txt').read_text() and not (policy / 'Check.olean').exists(), 'actual stricter axiom policy rejection')
fresh = read(E / 'fresh/core-terms-fresh.json')
require(len(fresh['rows']) == 34 and set(fresh['calibration']) == set(fresh['checking-window']) == {'proof-search', 'formal-native-session'} and
        all(value > 0 for value in fresh['calibration'].values()) and all(value == 0 for value in fresh['checking-window'].values()), 'calibrated fresh packet reconstruction')
require(all(row['packet'] == examples[row['id']]['packet'] and row['status'] == 'checked-data-connection' and
            row['rehashed-error'] == 'rejected' and row['kernel-execution'] == 'not-run' for row in fresh['rows']), 'exact saved data and changed-error rejection')
corpora = []
for name in ['advanced', 'features', 'native']:
    new = read(E / 'corpora' / (name + '.json'))
    old = read(P / 'evidence/mixed-obligations/corpora' / (name + '.json'))
    signature = lambda data: {row['id']: tuple(row[engine]['verdict'] for engine in ['z3', 'oxiz']) for row in data['cases']}
    require(signature(new) == signature(old) and new['disagreements'] == [] and new['invalid-models'] == [], 'native verdict drift: ' + name)
    corpora.append({'corpus': name, 'questions': len(new['cases']), 'per_case_verdicts_unchanged': True})
require(sum(row['questions'] for row in corpora) == 187, 'complete native corpus')
sdk = read(P / 'sdk-pin.json')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file() and path.name not in {'qualification.json', 'dossier-qualification.json'} and not any(part.startswith('browser') for part in path.parts)}
qualification = {'schema': 'enchant.formal.core-term-qualification.v1', 'checkpoint': 21,
                 'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': sdk,
                 'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
                 'z3_library_sha256': sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so'),
                 'checks': {'source_snapshot': snapshot, 'files': counts, 'total_assertions': sum(counts.values()), 'failures': 0},
                 'model': {'pin': pin, 'tool': tool, 'audits': audit},
                 'correspondence': {'checked_trees': 34, 'contract_subjects': 4, 'scalar_trees': 23, 'record_trees': 11,
                                    'rejected_semantic_substitutions': 6, 'ignored_failure_payload': 'accepted-mathematical-relation',
                                    'scope': 'all-typed-inputs-of-each-contained-core-and-exact-symbolic-outcome',
                                    'axiom_policy': 'lean-standard', 'choice_free_quotient': 'rejected-by-actual-dependencies'},
                 'fresh_reconstruction': fresh, 'native_comparison': {'questions': 187, 'corpora': corpora},
                 'prior_mixed_obligations': {'manifests': 17, 'checked_leaves': 39, 'applied_instances': 11},
                 'remaining_trust': ['named Core data to typed expression, record layout and error-name codec',
                                     'general lowerer soundness and contract-rule composition', 'Source/compiler/runtime correspondence', 'local execution custody'],
                 'production_default_changed': False, 'compiler_proof_authority': False, 'artifact_sha256': artifacts}
(E / 'qualification.json').write_text(json.dumps(qualification, indent=2) + '\n')
print(json.dumps({'assertions': sum(counts.values()), 'checked_core_trees': 34, 'rejected_substitutions': 6, 'unchanged_native_questions': 187}))
