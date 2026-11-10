"""Reconstruct checkpoint 19 from committed source and constructive SAT evidence."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/witnesses'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


snapshot = read(E / 'check-source-pin.json')
for name, digest in snapshot['sha256'].items():
    path = P / name
    require(sha(path) == digest, 'changed qualification source: ' + name)
    committed = subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + path.relative_to(R).as_posix()], cwd=R)
    require(committed == path.read_bytes(), 'source differs from recorded commit: ' + name)
log = (E / 'checks.txt').read_text()
counts = {name: int(count) for name, count in re.findall(r'✓\s+(formal\.[\w-]+)\s+(\d+) passed', log)}
require(len(counts) == 33 and '33 file(s) passed, 0 failed, 0 incoherent' in log, 'green thirty-three-file integration')
require(counts['formal.witness-test'] == 274 and counts['formal.query-test'] == 76, 'witness and shared-query regression coverage')
require('Ran 5 tests' in (E / 'bridge-check.txt').read_text() and '\nOK\n' in (E / 'bridge-check.txt').read_text(), 'independent constructive checker tests')
require('Ran 4 tests' in (E / 'prior-term-regression-check.txt').read_text() and '\nOK\n' in (E / 'prior-term-regression-check.txt').read_text(), 'original term-checker regressions after shared grammar extraction')
pins = {name: read(P / ('metatheory/' + name + '-pin.json')) for name in ['refutation', 'terms', 'witness']}
require(sha(P / 'metatheory/refutation-pin.json') == pins['terms']['normalized_kernel_pin_sha256'], 'normalized dependency pin')
require(sha(P / 'metatheory/terms-pin.json') == pins['witness']['typed_term_pin_sha256'], 'typed-term dependency pin')
for pin in pins.values():
    for key in ['source', 'compiled']:
        require(sha(P / pin[key]['path']) == pin[key]['sha256'], 'model artifact pin')
tool = read(P / 'metatheory/tool-pin.json')
require(sha(Path(tool['path']) / 'bin/lean') == tool['binary_sha256'], 'Lean tool pin')
audits = {}
for line in (E / 'model-check.txt').read_text().splitlines():
    match = re.fullmatch(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[(.*)\])", line)
    require(match is not None, 'unexpected witness model audit')
    audits[match[1]] = match[2].split(', ') if match[2] else []
require(set(audits) == {'FormalWitness.' + name for name in ['checked_context_holds', 'checked_witness_satisfiable', 'empty_context_satisfiable', 'false_context_unsatisfiable']}, 'four general constructive results')
require(Counter(tuple(v) for v in audits.values()) == Counter({('propext', 'Quot.sound'): 3, ('propext',): 1}), 'actual witness general dependencies')
accepted, rejected = read(E / 'execution/accepted.json'), read(E / 'execution/rejected.json')
originals = {row['id']: row for row in read(E / 'examples/summary.json')['rows']}
require(len(accepted) == len(originals) == 32 and len(rejected) == 6, 'accepted/rejected evidence counts')
origins = Counter(row['discovery'].get('backend', row['discovery']['kind']) for row in originals.values())
require(origins == Counter({'explicit-bindings': 22, 'z3': 5, 'oxiz': 5}), 'authored and dual native origins')
for row in accepted:
    target = E / 'execution' / row['id']
    packet = read(E / 'examples' / (row['id'] + '.json'))
    require(row['packet'] == packet['identity'] == originals[row['id']]['packet'] and row['question'] == packet['question'], 'original witness attribution')
    require(row['status'] == 'checked-term-satisfiability' and row['axioms'] == {'packetAccepted': ['propext'], 'originalContextHolds': ['propext', 'Quot.sound'], 'originalContextSatisfiable': ['propext', 'Quot.sound']}, 'actual applied constructive theorem audit')
    require(sha(target / 'Check.lean') == row['proof_source_sha256'] and sha(target / 'Check.olean') == row['proof_olean_sha256'], 'applied proof artifact custody')
    require(row['full_query_connection'] == 'requires-fresh-BL-question-reconstruction' and row['backend_attestation'] == 'not-established' and row['compiler_proof_authority'] is False, 'witness authority boundary')
for row in rejected:
    target = E / 'execution/rejected' / row['id']
    require(row['status'] == 'rejected-by-lean' and not (target / 'Check.olean').exists() and (target / 'lean.txt').exists(), 'semantic failure has no compiled success')
fresh = read(E / 'fresh/witnesses-fresh.json')
require(len(fresh['rows']) == 32 and all(v > 0 for v in fresh['calibration'].values()) and all(v == 0 for v in fresh['checking-window'].values()), 'fresh positively calibrated replay')
require(all(row['status'] == 'checked-data-connection' and row['changed-original'] == 'rejected' and row['kernel-execution'] == 'not-run' for row in fresh['rows']), 'fresh original-question connection')
prior_accepted = read(E / 'prior-term-regression/accepted.json')
prior_rejected = read(E / 'prior-term-regression/rejected.json')
require(len(prior_accepted) == 17 and len(prior_rejected) == 5, 'prior universal typed-term proof scope preserved')
corpora = []
for name in ['advanced', 'features', 'native']:
    current = read(E / 'corpora' / (name + '.json'))
    prior = read(P / 'evidence/obligations/corpora' / (name + '.json'))
    signature = lambda data: {row['id']: {engine: row[engine]['verdict'] for engine in ['z3', 'oxiz']} for row in data['cases']}
    require(signature(current) == signature(prior) and current['disagreements'] == [] and current['invalid-models'] == [], 'native drift: ' + name)
    corpora.append({'corpus': name, 'questions': len(current['cases']), 'per_case_verdicts_unchanged': True, 'summary': current['summary']})
require(sum(row['questions'] for row in corpora) == 187, 'complete existing native corpus')
archive_pin = read(E / 'examples/archive-pin.json')
require(sha(E / 'examples/witnesses.etf') == archive_pin['sha256'] and (E / 'examples/witnesses.etf').stat().st_size == archive_pin['bytes'], 'original archive custody')
artifacts = {f.relative_to(P).as_posix(): sha(f) for f in sorted(E.rglob('*')) if f.is_file() and f.name not in {'qualification.json', 'dossier-qualification.json'} and not any(part.startswith('browser') for part in f.parts)}
result = {'schema': 'enchant.formal.constructive-witness-qualification.v1', 'checkpoint': 19,
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': read(P / 'sdk-pin.json'),
          'worker_sha256': sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker'),
          'z3_library_sha256': sha(Path(read(P / 'sdk-pin.json')['sdk']) / 'image/priv/z3/bin/libz3.so'),
          'checks': {'source_snapshot': snapshot, 'files': counts, 'total_assertions': sum(counts.values()), 'failures': 0},
          'witness_model': {'pin': pins['witness'], 'tool': tool, 'general_audits': audits, 'semantics': pins['witness']['semantics']},
          'applied_witnesses': {'accepted_originals': 32, 'authored_assignments': 22, 'native_models': {'z3': 5, 'oxiz': 5}, 'rejected_false_or_undefined': 6,
                                'scope': 'explicit-existence-in-original-partial-typed-assertion-model', 'classical_choice': 'not-admitted',
                                'full_query_attribution': 'separate-fresh-BL-reconstruction', 'backend_attestation': 'not-established'},
          'fresh_reconstruction': fresh, 'native_comparison': {'questions': 187, 'corpora': corpora},
          'previous_universal_proofs': {'accepted': 17, 'rejected_altered_originals': 5, 'unchanged_semantics': True},
          'common_v1_bundle_witness_facet': 'still-pending-format-composition',
          'shared_query_boundary': 'native-certificate-obligation-and-witness-counterexample-consistency',
          'remaining_trust': ['term-data/typed-semantics correspondence and codec', 'model-to-question interpretation and composition',
                              'Source elaboration/specialization correspondence', 'BL compiler and BEAM runtime', 'local execution custody'],
          'retained_failed_attempts': 'Static assertion delimiters, xor constructor spelling, actual backend metadata adaptation, and a whole-query serialization limit reached by a previously accepted shared relation graph. The corrected shared validator preserves the DAG boundary; failed attempts are excluded from accepted evidence.',
          'production_default_changed': False, 'compiler_proof_authority': False, 'artifact_sha256': artifacts}
(E / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'assertions': sum(counts.values()), 'files': len(counts), 'existence_proofs': 32, 'semantic_rejections': 6, 'unchanged_native_questions': 187}))
