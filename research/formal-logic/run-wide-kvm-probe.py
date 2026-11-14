"""Observe actual KVM access in a fresh Nix sandbox without operator changes."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, re, secrets, subprocess, time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/wide-integration'
E.mkdir(exist_ok=True)
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
assert not (E / 'kvm-exit.json').exists() and not (E / 'kvm-sandbox.json').exists(), 'Retain earlier probe evidence before a retry.'
files = [Path(__file__), P / 'proposals/wide-kvm-builder-probe.nix',
         P / 'proposals/scalar-kvm-builder-probe.nix', R / 'flake.lock']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in files:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
nonce = secrets.token_hex(12)
write('kvm-source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'nonce': nonce,
                             'scope': 'Fresh sandbox observation; no Source, Nix projection or builder transport edits.'})
command = ['nix-build', str(P / 'proposals/wide-kvm-builder-probe.nix'), '--argstr', 'nonce', nonce, '--no-out-link']
write('kvm-command.json', command)
(E / 'kvm-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
started_wall = datetime.now(timezone.utc)
started = time.monotonic()
with (E / 'kvm-checks.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
write('kvm-exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
assert code == 0, (E / 'kvm-checks.txt').read_text()[-4000:]
paths = re.findall(r'^(/nix/store/[^\s]+formal-wide-kvm-sandbox-probe-' + nonce + r')$', (E / 'kvm-checks.txt').read_text(), re.M)
assert len(paths) == 1
product = Path(paths[0]); observed = read(product)
assert observed['status'] == 'passed' and observed['api_version'] == 12
assert observed['device_opened_read_write'] is True and observed['empty_vm_created_and_closed'] is True
assert datetime.fromisoformat(observed['recorded_utc']) >= started_wall - timedelta(seconds=2)
assert all(sha(R / name) == digest for name, digest in digests.items())
(E / 'kvm-sandbox.json').write_bytes(product.read_bytes())
write('kvm-sandbox-provenance.json', {'status': 'passed', 'source_pin': read(E / 'kvm-source-pin.json'),
       'product': str(product), 'product_sha256': sha(product),
       'product_nar_hash': subprocess.check_output(['nix-store', '--query', '--hash', product], text=True).strip(),
       'scope': 'The nonce changes the derivation; the returned timestamp follows this invocation. '
                'An actual Nix sandbox opens /dev/kvm read/write, queries API 12 and creates/closes an empty VM. '
                'No guest/compiler is run and no feature advertisement or operator configuration is changed.'})
print(json.dumps({'status': 'passed', 'stage': 'fresh-kvm-sandbox', 'product': str(product)}))
