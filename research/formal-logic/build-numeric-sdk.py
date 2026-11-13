"""Prepare one immutable SDK after the actual qualified floor is committed."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

baseline = read(E / 'baseline/sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
assert sha(Path(baseline['sdk']) / 'artifact.json') == baseline['descriptor_sha256']
floor = read(E / 'compiler-floor-install.json')
assert floor['status'] == 'passed' and floor['manifest_last'] and floor['sdk_produced'] is False
assert sha(E / 'compiler-qualification.json') == floor['qualification_sha256']
assert all(sha(R / 'priv/bootstrap/seed' / name) == digest for name, digest in floor['after'].items())
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
runtime_names = ['priv/boot/rt.bl', 'priv/host/decimal.bl', 'priv/host/num.bl',
                 'priv/lib/decimal.bl', 'priv/lib/js/rt.mjs', 'priv/lib/js/host-leaves.mjs',
                 'priv/lib/js/leaves.mjs', 'priv/lib/system/smt.bl']
names = runtime_names + [str(Path(__file__).relative_to(R))] + ['priv/bootstrap/seed/' + name for name in floor['after']]
sources = {}
for name in names:
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    sources[name] = sha(R / name)
fingerprint = subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
write(E / 'prepare-source-pin.json', {'code_commit': commit, 'source_sha256': sources,
      'engine_fingerprint': fingerprint, 'baseline_sdk_pin': baseline,
      'compiler_floor_install_sha256': sha(E / 'compiler-floor-install.json')})
command = [str(R / 'scripts/prepare-checkout-sdk')]
write(E / 'prepare-command.json', command)
(E / 'prepare-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / 'prepare-exit.json').unlink(missing_ok=True)
started = time.monotonic()
with (E / 'prepare-checks.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
write(E / 'prepare-exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
if code:
    raise SystemExit(code)
assert all(sha(R / name) == digest for name, digest in sources.items())
assert fingerprint == subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
directory = R / '.bl/sdks' / fingerprint
sdk, engine = [(directory / name).resolve(strict=True) for name in ('result-sdk', 'source-engine')]
assert str(sdk).startswith('/nix/store/') and str(engine).startswith('/nix/store/')
for name in runtime_names:
    assert sha(engine / name) == sources[name] == sha(sdk / 'lib/beam_lisp-0.1.0' / name)
write(E / 'sdk-candidate.json', {'sdk': str(sdk), 'descriptor_sha256': sha(sdk / 'artifact.json'),
      'source': str(engine), 'base_commit': commit, 'engine_fingerprint': fingerprint})
print(json.dumps({'status': 'candidate-built', 'sdk': str(sdk), 'project_pin_changed': False}), flush=True)
