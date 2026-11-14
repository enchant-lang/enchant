"""Build one wide SDK candidate after exact-result and narrow source gates."""
from pathlib import Path
import hashlib, json, subprocess, time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/wide-integration'
E.mkdir(exist_ok=True)
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
baseline = read(P / 'sdk-pin.json')
parent = read(P / 'evidence/obligation-integration/qualification.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == baseline
assert sha(Path(baseline['sdk']) / 'artifact.json') == baseline['descriptor_sha256']
native_path = P / 'evidence/wide-owner-prototype/native-smoke/qualification.json'
native = read(native_path)
assert native['status'] == 'passed' and native['questions'] == 9 and native['raw_status_differences'] == 0
assert native['qualified_runtime_sdk'] == baseline
gates = {}
renderer_differences = []
for phase in ('identities', 'narrow'):
    directory = P / 'evidence/wide-reference-reuse' / phase
    q = read(directory / 'qualification.json')
    assert q['status'] == 'passed' and q['phase'] == phase and q['sdk_pin'] == baseline
    assert q['source_pin']['base_native_qualification_sha256'] == sha(native_path)
    assert q['reference_format_changed'] is False
    for name, digest in q['source_pin']['source_sha256'].items():
        current = sha(R / name)
        if current != digest and name == 'research/formal-logic/src/formal/review-host.bl':
            # This file was conservatively recorded with the whole project
            # directory. It is not imported by term factories or the runtime.
            # Its later SVG-only repair has independent presentation evidence.
            presentation = read(P / 'evidence/wide-owner-presentation/dossier-qualification.json')
            assert presentation['status'] == 'passed' and presentation['sdk_pin'] == baseline
            browser_pin = read(P / 'evidence/wide-owner-presentation/browser-source-pin.json')
            assert browser_pin['source_sha256'][name] == current
            renderer_differences.append({'path': name, 'recorded': digest, 'current': current,
                                         'reason': 'Separately qualified review renderer; no runtime/factory/checker code change.'})
        else: assert current == digest, name
    for row in q['source_pin']['base_projected_modules']:
        assert sha(Path(row['source'])) == row['source_sha256']
    terminal = read(directory / 'owner-terminal.json')['state']
    assert terminal['SubState'] == 'exited' and terminal['MainPID'] == '0'
    assert terminal['Result'] == 'success' and terminal['ExecMainStatus'] == '0'
    gates[phase] = {'sha256': sha(directory / 'qualification.json'), 'assertions': q['assertions']}
assert read(P / 'evidence/wide-reference-reuse/identities/pure-observations.json')['native-exchanges'] == 0
for suffix in ('reader-one', 'reader-two'):
    path = native_path.parent / suffix / 'qualification.json'
    reader = read(path)
    assert reader['status'] == 'passed' and reader['packets'] == 20 and reader['native_exchanges'] == reader['oracle_calls'] == 0
    assert reader['sdk_pin'] == baseline
    gates[suffix] = {'sha256': sha(path), 'checks': reader['checks']}
names = ['resources/typed', 'graph-question', 'point-profile', 'graph-execution',
         'request-answer', 'request-point', 'logic', 'request-evidence']
runtime = ['priv/lib/formal/' + name + '.bl' for name in names]
for name, target in zip(names, runtime):
    source = P / 'prototypes/wide-owner/formal' / (name + '.bl')
    expected = (read(P / 'evidence/wide-reference-reuse/identities/source-pin.json')['source_sha256'][str(source.relative_to(R))]
                if name == 'request-evidence' else native['source_pin']['module_inputs']['formal.' + name.replace('/', '.')]['sha256'])
    assert sha(source) == expected == sha(R / target), target
placement_path = E / 'kvm-sandbox.json'
placement = read(placement_path)
assert placement['status'] == 'passed' and placement['api_version'] == 12
assert placement['device_opened_read_write'] is True and placement['empty_vm_created_and_closed'] is True
placement_provenance = read(E / 'kvm-sandbox-provenance.json')
assert placement_provenance['status'] == 'passed' and placement_provenance['product_sha256'] == sha(placement_path)
placement_terminal = read(E / 'kvm-owner-terminal.json')['state']
assert placement_terminal['SubState'] == 'exited' and placement_terminal['MainPID'] == '0'
assert placement_terminal['Result'] == 'success' and placement_terminal['ExecMainStatus'] == '0'
floor_path = P / 'evidence/numeric-semantics/compiler-floor-install.json'
floor = read(floor_path)
assert floor['status'] == 'passed' and floor['manifest_last'] is True
for name, digest in floor['after'].items(): assert sha(R / 'priv/bootstrap/seed' / name) == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for name in [*runtime, str(Path(__file__).relative_to(R)), 'research/formal-logic/sdk-pin.json']:
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    digests[name] = sha(R / name)
fingerprint = subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
assert fingerprint != baseline['engine_fingerprint']
assert not (E / 'sdk-candidate.json').exists(), 'Reuse the exact candidate; do not produce another SDK for routine checks.'
write('prepare-source-pin.json', {'code_commit': commit, 'source_sha256': digests,
      'baseline_sdk_pin': baseline, 'engine_fingerprint': fingerprint, 'projection_gates': gates,
      'renderer_only_source_differences': renderer_differences,
      'fresh_sandbox_placement_receipt_sha256': sha(placement_path),
      'sandbox_placement_provenance_sha256': sha(E / 'kvm-sandbox-provenance.json'),
      'compiler_floor_install_sha256': sha(floor_path)})
write('baseline-sdk-pin.json', baseline)
command = [str(R / 'scripts/prepare-checkout-sdk')]
write('prepare-command.json', command)
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
started = time.monotonic()
with (E / 'prepare-checks.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
write('prepare-exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
assert code == 0, (E / 'prepare-checks.txt').read_text()[-5000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
assert fingerprint == subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
directory = R / '.bl/sdks' / fingerprint
sdk, engine = [(directory / name).resolve(strict=True) for name in ('result-sdk', 'source-engine')]
assert str(sdk).startswith('/nix/store/') and str(engine).startswith('/nix/store/')
for name in runtime: assert sha(engine / name) == digests[name] == sha(sdk / 'lib/beam_lisp-0.1.0' / name)
write('sdk-candidate.json', {'sdk': str(sdk), 'descriptor_sha256': sha(sdk / 'artifact.json'),
      'source': str(engine), 'base_commit': commit, 'engine_fingerprint': fingerprint})
print(json.dumps({'status': 'candidate-built', 'sdk': str(sdk), 'project_pin_changed': False,
                  'qualification': 'pending full native matrix, canonical regressions and cold/historical readers'}))
