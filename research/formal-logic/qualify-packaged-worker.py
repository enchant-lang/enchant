"""Qualify SDK artifact discovery and observed portable execution, not activation."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tomllib

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/packaged-worker'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise AssertionError(why)


def counts(path, expected):
    text = path.read_text()
    result = {name: int(n) for name, n in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', text)}
    require(set(result) == expected and all(result.values()), 'all expected files: ' + str(path))
    require(f'{len(expected)} file(s) passed, 0 failed, 0 incoherent' in text, 'complete successful run')
    return result


candidate, pin = read(E / 'sdk-candidate.json'), read(P / 'sdk-pin.json')
require(all(candidate[k] == pin[k] for k in ('sdk', 'descriptor_sha256', 'source')), 'selected exact SDK')
sdk, engine = Path(pin['sdk']), Path(candidate['engine_source'])
require(sha(sdk / 'artifact.json') == pin['descriptor_sha256'], 'immutable descriptor')
metadata = read(sdk / 'artifact.json')
require(metadata['source'] == pin['source'], 'SDK source')
for name, digest in candidate['source_sha256'].items():
    require(sha(R / name) == digest, 'unchanged code: ' + name)
    require((R / name).read_bytes() == subprocess.check_output(['git', 'show', candidate['code_commit'] + ':' + name], cwd=R),
            'committed code: ' + name)
for name, digest in candidate['engine_source_sha256'].items():
    require(sha(engine / name) == digest, 'captured engine input: ' + name)
for name, digest in candidate['source_sha256'].items():
    if name.startswith(('priv/', 'native/')):
        require(sha(Path(pin['source']) / name) == digest, 'actual SDK source: ' + name)
require(len(candidate['engine_source_sha256']) == 39 and len(candidate['compatibility_source_sha256']) == 3,
        'runtime/build inputs separate from research compatibility')
build = read(E / 'managed-build-result.json')
require(build['id'] == candidate['managed_handle'] and build['status'] == 'succeeded'
        and build['exit_code'] == 0 and build['spawn_count'] == 1, 'single successful managed production')
compiler = read(E / 'produced-compiler.json')
previous = read(P / 'evidence/effects/produced-compiler.json')
require(compiler['status'] == 'passed' and compiler['sdk'] == pin['sdk'] and compiler['files'] == 141
        and compiler['manifest_sha256'] == previous['manifest_sha256'], 'same complete qualified compiler floor')
preflight = read(E / 'source-preflight.json')
require(preflight['beam-selection']['modality'] == 'proven' and not any(preflight[k] for k in
        ('source-errors', 'target-dependency-errors', 'require-cycles', 'sources_changed_during_analysis')), 'Source preflight')
require('0 passed, 6 failed' in (E / 'baseline-checks.txt').read_text(), 'original unconfigured failures retained')
focused = counts(E / 'focused-checks.txt', {'system.formal-artifact-test', 'source-formal-artifact-test',
    'system.effect-test', 'system.formal-effect-test', 'source-effect-test', 'system.formal-context-owner-test',
    'system.formal-answer-test', 'system.formal-oracle-test'})
require(sum(focused.values()) == 503 and focused['system.formal-artifact-test'] == 42
        and focused['source-formal-artifact-test'] == 11, 'focused SDK and Source boundaries')
regression = counts(E / 'regression-checks.txt', {'system.oracle-test', 'system.system-test'} |
    {'formal.' + name + '-test' for name in ('query', 'backend', 'kernel', 'certificate', 'core', 'record',
     'protocol', 'protocol-trace', 'contract', 'loop', 'translation', 'api', 'facade', 'witness',
     'core-counterexamples', 'advanced', 'features', 'native', 'context', 'selected-runtime')})
require(sum(regression.values()) == 7086, 'complete formal regression')
for name in ('focused-command.json', 'regression-command.json', 'examples-command.json', 'portable-examples-command.json'):
    command = read(E / name)
    for variable in ('ENCHANT_FORMAL_WORKER', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH'):
        require(any(command[i:i+2] == ['-u', variable] for i in range(len(command)-1)), 'unconfigured run: ' + name)
for name in ('examples-command.json', 'portable-examples-command.json'):
    require('-p' not in read(E / name), 'no research import path')
total = 0
for name in ('advanced', 'features', 'native'):
    current = read(E / 'regression' / (name + '.json'))
    old = {row['id']: row for row in read(P / 'evidence/effects/regression' / (name + '.json'))['cases']}
    require(not current['disagreements'] and not current['invalid-models'], 'healthy paired matrix')
    require(old.keys() == {row['id'] for row in current['cases']}, 'same paired questions')
    for row in current['cases']:
        require(row['question-sha256'] == old[row['id']]['question-sha256'], 'same complete question identity')
        for backend in ('z3', 'oxiz'):
            require(all(row[backend][k] == old[row['id']][backend][k] for k in ('solver-status', 'verdict')),
                    'unchanged native capability: ' + row['id'])
            require(row[backend]['identity']['sdk'] == pin['sdk'], 'exact matrix SDK')
    total += len(current['cases'])
require(total == 187, 'all previous paired questions')
artifact = read(sdk / 'image/priv/formal/artifact.json')
require(artifact == read(E / 'native-artifact.json') and artifact['packaging'] == 'nix', 'actual packaged descriptor')
for field, path in [('worker', sdk / 'image/priv/formal/bin/formal-worker'), ('z3', sdk / 'image/priv/z3/bin/libz3.so')]:
    require(sha(path) == artifact[field]['sha256'], 'actual packaged bytes: ' + field)
crate = R / 'native/ports/formal_worker'
require(sha(crate / 'Cargo.lock') == artifact['cargo_lock_sha256'], 'actual Cargo lock')
prior_lock = tomllib.loads(subprocess.check_output(['git', 'show', '9d1433f3a:research/oxiz-prototype/worker/Cargo.lock'], cwd=R, text=True))
registry = lambda document: {(p['name'], p['version']): p for p in document['package'] if 'source' in p}
require(registry(tomllib.loads((crate / 'Cargo.lock').read_text())) == registry(prior_lock), 'all registry pins unchanged')
require(read(E / 'notices-check.json')['registry_packages'] == 104
        and read(E / 'notices-check.json')['all_locked_registry_packages_covered'], 'registry notice metadata')
require(read(E / 'compatibility-result.json') == {'exit_code': 0, 'private_target_removed': True}
        and not (R / '.bl/qualify/packaged-worker-compat-check').exists(), 'compatibility compiles and private target retired')
require(sha(R / 'research/oxiz-prototype/worker/target/release/formal-worker')
        == read(P / 'evidence/effects/qualification.json')['worker_sha256'], 'preceding qualified research worker retained')
portable = read(E / 'portable-artifact.json')
require(portable['image'] == metadata['image'] and portable['sha256'] == sha(Path(portable['product']) / 'bl.drop'),
        'portable product packages this exact image')
relocated = read(E / 'portable-runtime-artifact.json')
require(relocated['packaging'] == 'portable-shell-v1', 'relocated descriptor')
for field in ('worker', 'z3'):
    require(relocated[field]['producer_sha256'] == artifact[field]['sha256']
            and relocated[field]['sha256'] != artifact[field]['sha256'], 'producer and runtime hashes distinct')
    text = (E / ('portable-' + field + '-dynamic.txt')).read_text()
    require('RPATH' not in text and 'RUNPATH' not in text, 'no ELF runtime search path')
observation = read(E / 'portable-observation-note.json')
require(observation['application_exit_code'] == 0 and observation['runtime_files_outside_nix_store']
        and observation['runtime_hashes_match'], 'actual portable observation, with corrected observer lookup')
for name, packaging in [('examples.json', 'nix'), ('portable-examples.json', 'portable-shell-v1')]:
    example = read(E / name)
    require(not Path(example['cwd']).is_relative_to(R) and example['research-import-path'] is False, 'unrelated working directory')
    require([row['backend'] for row in example['rows']] == ['z3', 'oxiz'], 'both ordinary SDK choices')
    for row in example['rows']:
        require(row['satisfiable'] == 'sat' and row['x'] == 7 and row['replay'] == 'valid'
                and row['increment'] == 'proved' and row['certificate'] == 'not-checked', 'actual term results')
        require(row['artifacts']['worker']['origin'] == 'sdk'
                and row['artifacts']['packaged']['packaging'] == packaging, 'actual selected package kind')
        if packaging == 'portable-shell-v1':
            require(row['artifacts']['worker']['sha256'] == relocated['worker']['sha256'], 'runtime reports relocated worker')
            require(row['artifacts']['library']['sha256'] == relocated['z3']['sha256'] if row['backend'] == 'z3'
                    else row['artifacts']['library'] is None, 'only Z3 selects the relocated library')
qualified = [R / name for name in candidate['source_sha256']]
qualified += [R / name for name in ('test/bl/system/formal_artifact_test.bl', 'test/bl/source_formal_artifact_test.bl')]
qualified += [P / name for name in ('PACKAGED-WORKER.md', 'packaged-worker-check.bl', 'run', 'review', 'qualify-packaged-worker.py')]
report = {'schema': 'enchant.formal.packaged-worker-qualification.v1', 'checkpoint': 32, 'sdk_pin': pin,
    'source': {'code_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip(),
               'sha256': {str(path.relative_to(R)): sha(path) for path in qualified}},
    'managed_build': build, 'compiler': compiler,
    'checks': {'focused': focused, 'regression': regression, 'total_assertions': 7589, 'failed': 0},
    'unchanged_paired_questions': 187, 'native_artifact': artifact, 'portable_artifact': portable,
    'relocated_runtime_artifact': relocated, 'portable_observation': observation,
    'scope': ['SDK-owned worker and library defaults', 'option/environment/image provenance',
              'ordinary SDK-only and selected Source calls', 'observed portable execution with relocated hashes',
              'canonical native port source separate from NIF products'],
    'remaining': ['clean-host activation and rolling-release qualification', 'remaining legacy/source Oracle migration',
                  'native pooling, broader effects and compiler/runtime preservation proofs'],
    'compiler_proof_authority': False}
(E / 'qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'checkpoint': 32, 'focused': 503, 'regression': 7086, 'paired_questions': 187,
                  'portable_scope': 'observed-host-execution', 'compiler_proof_authority': False}))
