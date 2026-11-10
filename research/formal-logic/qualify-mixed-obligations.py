"""Qualify mixed obligation leaves, witnessed claim instances and transport."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

import obligation_proof as proof

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/mixed-obligations'
require = proof.require


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def test_log(name, count):
    log = (E / name).read_text()
    require(f'Ran {count} tests' in log and '\nOK\n' in log, name + ' successful tests')


snapshot = read(E / 'check-source-pin.json')
for name, digest in snapshot['sha256'].items():
    source = P / name
    committed = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + source.relative_to(R).as_posix()], cwd=R)
    require(sha(source) == digest and source.read_bytes() == committed, 'qualification source changed: ' + name)
log = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', log)}
require(len(counts) == 34 and '34 file(s) passed, 0 failed, 0 incoherent' in log and counts['formal.mixed-obligation-test'] == 54, 'full mixed BL integration')
test_log('bridge-check.txt', 5)
test_log('v1-check.txt', 6)
test_log('standalone-witness-check.txt', 5)
old_results = read(E / 'v1/results.json')
require(len(old_results) == 13 and sum(len(r['checked']) for r in old_results) == 23, 'archived v1 leaf coverage')
require(len(read(E / 'standalone-witness/accepted.json')) == 32 and len(read(E / 'standalone-witness/rejected.json')) == 6, 'standalone witness regression counts')
examples = {row['id']: row for row in read(E / 'examples/summary.json')['rows']}
old_examples = {row['id']: row for row in read(P / 'evidence/obligations/examples/summary.json')['rows']}
require(all(examples[name]['plan'] == row['plan'] for name, row in old_examples.items()), 'mixed evidence preserves all existing subject plans')
results = {row['id']: row for row in read(E / 'execution/results.json')}
require(len(examples) == len(results) == 17 and set(examples) == set(results), 'seventeen subject exports and reports')
require({row['subject_kind'] for row in results.values()} == {'query', 'contract', 'translation', 'loop', 'protocol', 'source-protocol', 'protocol-trace'}, 'all seven subject kinds')
sdk = read(P / 'sdk-pin.json')
worker = sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker')
z3 = sha(Path(sdk['sdk']) / 'image/priv/z3/bin/libz3.so')
kinds, origins, instance_count = Counter(), Counter(), 0
for name, record in examples.items():
    manifest = read(E / 'examples' / record['manifest-file'])
    require(proof.validate(manifest) == 2 and manifest['identity'] == record['manifest'], 'mixed manifest identity')
    archive = E / 'examples' / record['archive']['file']
    require(sha(archive) == record['archive']['sha256'] and archive.stat().st_size == record['archive']['bytes'], 'archived subject and bundle custody')
    discovery = record['discovery']
    if discovery:
        origins[discovery.get('backend', discovery['kind'])] += 1
        if discovery['kind'] == 'native-model':
            identity = discovery['identity']
            require(discovery['origin'] == 'claimed-not-cryptographically-attested' and identity['sdk'] == sdk['sdk'] and identity['worker-sha256'] == worker, 'native witness origin labels')
            require(identity['library-sha256'] == (z3 if discovery['backend'] == 'z3' else None), 'native witness library label')
    result = results[name]
    require(result['plan'] == record['plan'] and result['manifest'] == record['manifest'] and
            result['coverage'] == {key: value for key, value in record['coverage'].items() if key != 'pending'}, 'exact declared report coverage')
    require(result['model_theorem'] == 'not-established-by-this-runner' and result['compiler_proof_authority'] is False, 'term scope and authority')
    require(result['entailments_with_witnessed_context'] == record['entailments-with-witnessed-context'], 'fresh and external context matches')
    leaves = {row['index']: row for row in result['checked']}
    for index, row in leaves.items():
        target = E / 'execution' / name / 'rows' / f'{index:04d}'
        require(sha(target / 'Check.lean') == row['proof_source_sha256'] and sha(target / 'Check.olean') == row['proof_olean_sha256'], 'leaf proof artifact custody')
        require(row['packet'] == manifest['rows'][index]['packet']['identity'] and row['context'] == manifest['rows'][index]['context'], 'leaf context and packet binding')
        kinds[row['via']] += 1
    for instance in result['checked_instances']:
        index = instance['index']
        target = E / 'execution' / name / 'instances' / f'{index:04d}'
        require(sha(target / 'Instance.lean') == instance['source_sha256'] and sha(target / 'Instance.olean') == instance['olean_sha256'], 'applied proof artifact custody')
        leaf = leaves[index]
        initial = next(row for row in leaves.values() if row['role'] == 'feasibility')
        require(leaf['via'] == 'entailment' and leaf['context'] == initial['context'] and
                instance['status'] == 'checked-original-question-satisfying-claim' and instance['proof_packet'] == leaf['packet'] and
                instance['witness_packet'] == initial['packet'] and instance['imported_entailment_sha256'] == leaf['proof_olean_sha256'], 'exact instance dependencies')
        require(set(instance['axioms']) == {'chosenWitnessAccepted', 'chosenClaim', 'originalQuestionHasSatisfyingClaim'} and
                all(set(deps) <= proof.terms.AXIOM_POLICIES[instance['axiom_policy']] for deps in instance['axioms'].values()), 'actual applied theorem axioms')
        instance_count += 1
require(kinds == Counter({'entailment': 23, 'unreachable': 1, 'witness': 15}) and instance_count == 11, 'checked proof/witness/instance counts')
require(origins == Counter({'explicit-bindings': 10, 'z3': 4, 'oxiz': 1}), 'explicit and native witness origins')
require(results['sat']['checked'][0]['packet'] == results['sat-z3']['checked'][0]['packet'], 'same direct question and same assignments from both engines')
require(results['loop']['entailments_with_witnessed_context'] == ['obligation/initial/normal'], 'initial context applies only to matching loop premise')
require(not results['unknown']['coverage']['complete'] and results['unknown']['positive_feasibility'] == 'satisfiable-in-contained-typed-term-model', 'feasible model with incomplete proof')
require(results['vacuous']['coverage']['complete'] and results['vacuous']['initial_assumption_consistency'] == 'inconsistent-in-contained-typed-term-model', 'inconsistent model with complete conditional proof')
require(sum(r['coverage']['complete'] for r in results.values()) == 15 and sum(r['coverage']['ready'] for r in results.values()) == 26, 'required coverage totals')
fresh = read(E / 'fresh/obligations-fresh.json')
legacy_fresh = read(E / 'v1/fresh/obligations-fresh.json')
for value, expected in [(fresh, 17), (legacy_fresh, 13)]:
    require(len(value['rows']) == expected and set(value['calibration']) == set(value['checking-window']) == {'proof-search', 'formal-native-session'} and
            all(count > 0 for count in value['calibration'].values()) and all(count == 0 for count in value['checking-window'].values()), 'calibrated fresh reconstruction')
    require(all(row['status'] == 'checked-data-connection' and row['missing-row'] == 'rejected' and row['kernel-execution'] == 'not-run' for row in value['rows']), 'fresh full-subject replay scope')
corpora = []
for name in ['advanced', 'features', 'native']:
    new = read(E / 'corpora' / (name + '.json'))
    old = read(P / 'evidence/witnesses/corpora' / (name + '.json'))
    signature = lambda rows: {row['id']: {engine: row[engine]['verdict'] for engine in ['z3', 'oxiz']} for row in rows['cases']}
    require(signature(new) == signature(old) and new['disagreements'] == [] and new['invalid-models'] == [], 'native verdict drift: ' + name)
    corpora.append({'corpus': name, 'questions': len(new['cases']), 'per_case_verdicts_unchanged': True})
require(sum(corpus['questions'] for corpus in corpora) == 187, 'complete native corpus')
artifacts = {path.relative_to(P).as_posix(): sha(path) for path in sorted(E.rglob('*')) if path.is_file() and path.name not in {'qualification.json', 'dossier-qualification.json'} and not any(part.startswith('browser') for part in path.parts)}
qualification = {'schema': 'enchant.formal.mixed-obligation-qualification.v1', 'checkpoint': 20,
                 'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': sdk, 'worker_sha256': worker, 'z3_library_sha256': z3,
                 'checks': {'source_snapshot': snapshot, 'files': counts, 'total_assertions': sum(counts.values()), 'failures': 0},
                 'mixed_bundles': {'subjects': 17, 'complete_required': 15, 'incomplete_required': 2, 'required_rows': 28, 'ready_required': 26,
                                   'checked_leaves': dict(kinds), 'checked_satisfying_claim_instances': instance_count, 'witness_origins': dict(origins),
                                   'scope': 'typed-term-leaves-and-checked-instances', 'model_composition': 'reviewed-not-mechanically-proved'},
                 'fresh_reconstruction': fresh, 'prior_v1_fresh_reconstruction': legacy_fresh,
                 'native_comparison': {'questions': 187, 'corpora': corpora},
                 'prior_standalone_witnesses': {'accepted': 32, 'rejected': 6},
                 'prior_common_v1': {'manifests': 13, 'checked_leaves': 23, 'version_two_opt_in': True},
                 'remaining_trust': ['term data and typed semantics bridge', 'model interpretation and rule composition', 'Source/compiler/runtime correspondence', 'local execution custody'],
                 'production_default_changed': False, 'compiler_proof_authority': False, 'artifact_sha256': artifacts}
(E / 'qualification.json').write_text(json.dumps(qualification, indent=2) + '\n')
print(json.dumps({'assertions': sum(counts.values()), 'subjects': 17, 'checked_leaves': sum(kinds.values()), 'applied_instances': instance_count, 'unchanged_native_questions': 187}))
