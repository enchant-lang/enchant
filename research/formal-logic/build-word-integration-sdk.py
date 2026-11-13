"""Prepare one word/ledger SDK only after all coherent projection gates pass."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration'
E.mkdir(exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

baseline = read(P / 'sdk-pin.json')
parent = read(P / 'evidence/retained-request/qualification.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == baseline
assert sha(Path(baseline['sdk']) / 'artifact.json') == baseline['descriptor_sha256']
prototype = {}
for stage in ('pure', 'owners', 'legacy', 'ledger'):
    path = P / 'evidence/word-integration-prototype' / stage / 'qualification.json'
    result = read(path)
    assert result['status'] == 'passed' and result['base_sdk_pin'] == baseline
    for name, digest in result['source_pin']['source_sha256'].items():
        assert sha(R / name) == digest, name
    prototype[stage] = {'sha256': sha(path), 'assertions': result['assertions']}
cold_path = P / 'evidence/word-integration-prototype/packets/qualification.json'
cold = read(cold_path)
assert cold['status'] == 'passed' and cold['base_sdk_pin'] == baseline and cold['records'] == 12
assert cold['manual_schema_preload'] is False
prototype['packets'] = {'sha256': sha(cold_path), 'records': 12}
runtime_names = ['priv/lib/formal/' + name + '.bl' for name in
                 ['backend', 'coordinates', 'evaluate', 'graph-execution', 'graph-question', 'graph-terms',
                  'logic', 'point-profile', 'request-answer', 'request-point', 'request-record', 'resources/word']]
runtime_names += ['priv/lib/veritas/ledger.bl']
floor_path = P / 'evidence/numeric-semantics/compiler-floor-install.json'
floor = read(floor_path)
assert floor['status'] == 'passed' and floor['manifest_last'] and floor['sdk_produced'] is False
assert all(sha(R / 'priv/bootstrap/seed' / name) == digest for name, digest in floor['after'].items())
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
names = runtime_names + [str(Path(__file__).relative_to(R)), 'research/formal-logic/sdk-pin.json']
digests = {}
for name in names:
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    digests[name] = sha(R / name)
fingerprint = subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
write('prepare-source-pin.json', {'code_commit': commit, 'source_sha256': digests,
      'baseline_sdk_pin': baseline, 'engine_fingerprint': fingerprint,
      'prototype_qualifications': prototype,
      'compiler_floor_install_sha256': sha(floor_path)})
write('baseline-sdk-pin.json', baseline)
command = [str(R / 'scripts/prepare-checkout-sdk')]
write('prepare-command.json', command)
(E / 'prepare-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / 'prepare-exit.json').unlink(missing_ok=True)
started = time.monotonic()
with (E / 'prepare-checks.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
write('prepare-exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
if code:
    raise SystemExit(code)
assert all(sha(R / name) == digest for name, digest in digests.items())
assert fingerprint == subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
directory = R / '.bl/sdks' / fingerprint
sdk, engine = [(directory / name).resolve(strict=True) for name in ('result-sdk', 'source-engine')]
assert str(sdk).startswith('/nix/store/') and str(engine).startswith('/nix/store/')
for name in runtime_names:
    assert sha(engine / name) == digests[name] == sha(sdk / 'lib/beam_lisp-0.1.0' / name)
write('sdk-candidate.json', {'sdk': str(sdk), 'descriptor_sha256': sha(sdk / 'artifact.json'),
      'source': str(engine), 'base_commit': commit, 'engine_fingerprint': fingerprint})
print(json.dumps({'status': 'candidate-built', 'sdk': str(sdk), 'project_pin_changed': False}), flush=True)
