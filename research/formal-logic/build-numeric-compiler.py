"""Use the existing Nix P/B/C compiler producer before preparing one new SDK.

`produce` only builds/verifies a compiler product, never an SDK. `install`
copies its complete verified floor atomically, with the manifest last. Review
and commit that real floor before the separate SDK preparation.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'
stage, = sys.argv[1:]
assert stage in ('produce', 'install')

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

def inventory(path):
    return {p.name: sha(p) for p in sorted(path.iterdir()) if p.is_file()}

baseline = read(E / 'baseline/sdk-pin.json')
assert read(P / 'sdk-pin.json') == baseline
assert read(E / 'baseline/state.json')['status'] == 'completed'
assert all(read(E / 'baseline/retirement.json').values())
assert sha(Path(baseline['sdk']) / 'artifact.json') == baseline['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
names = [str(Path(__file__).relative_to(R)), 'scripts/check-produced-compiler.py',
         'priv/boot/rt.bl', 'priv/host/decimal.bl', 'priv/host/num.bl', 'priv/lib/decimal.bl',
         'priv/lib/js/rt.mjs', 'priv/lib/system/smt.bl', 'nix/sdk-artifact.nix', 'nix/compiler-product.nix']
sources = {}
for name in names:
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    sources[name] = sha(R / name)
snapshot = {'code_commit': commit, 'source_sha256': sources, 'baseline_sdk_pin': baseline}
write(E / ('compiler-' + stage + '-source-pin.json'), snapshot)
proof_tool = runpy.run_path(str(R / 'scripts/check-produced-compiler.py'))

def verify(compiler):
    subprocess.run(['nix-store', '--check-validity', str(compiler)], check=True, timeout=120)
    subprocess.run(['nix-store', '--verify-path', str(compiler)], check=True, timeout=120)
    return proof_tool['verify_proof'](compiler, compiler / 'seed')

def bounded(name, argv, ceiling):
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
               '--unit=work-formal-numeric-' + name + '-' + commit[:12],
               '--working-directory=' + str(R), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group']
    # Use the same operator-owned Nix transport settings as SDK preparation.
    import os
    for variable in ('NIX_CONFIG', 'NIX_SSHOPTS', 'NIX_USER_CONF_FILES', 'NIX_CONF_DIR', 'SSH_AUTH_SOCK', 'XDG_CONFIG_HOME'):
        if variable in os.environ:
            command.append('--setenv=' + variable)
    command += argv
    write(E / (name + '-command.json'), command)
    write(E / (name + '-source-pin.json'), snapshot)
    (E / (name + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    (E / (name + '-exit.json')).unlink(missing_ok=True)
    started = time.monotonic()
    with (E / (name + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(E / (name + '-exit.json'), {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
    if code:
        raise SystemExit(code)

if stage == 'produce':
    directory = R / '.bl/numeric-compiler' / commit[:12]
    directory.mkdir(parents=True, exist_ok=True)
    fingerprint = subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
    bounded('compiler-source', ['nix-build', str(R / 'nix/sdk-source.nix'), '--argstr', 'source', str(R),
            '--out-link', str(directory / 'source'), '--option', 'timeout', '3300',
            '--option', 'experimental-features', 'nix-command flakes'], 3700)
    engine = (directory / 'source').resolve(strict=True)
    captured = subprocess.check_output([R / 'scripts/sdk-inputs', '--root', str(engine),
                                       '--policy', str(R / 'nix/engine-inputs.json')], text=True).strip()
    assert captured == fingerprint
    for name in names:
        if name.startswith(('priv/', 'nix/')):
            assert sha(engine / name) == sources[name]
    bounded('compiler-product', ['nix-build', str(engine / 'nix/sdk-artifact.nix'), '--argstr', 'source', str(engine),
            '--argstr', 'product', 'compiler', '--argstr', 'previous', baseline['sdk'],
            '--out-link', str(directory / 'compiler'), '--option', 'timeout', '3300',
            '--option', 'experimental-features', 'nix-command flakes'], 7200)
    compiler = (directory / 'compiler').resolve(strict=True)
    assert str(compiler).startswith('/nix/store/')
    proof = verify(compiler)
    inputs = read(compiler / 'qualification/inputs.json')
    assert all(sha(R / name) == digest for name, digest in inputs.items())
    assert all(sha(R / name) == digest for name, digest in sources.items())
    result = {'status': 'passed', 'recorded_utc': datetime.now(timezone.utc).isoformat(),
              'compiler': str(compiler), 'engine': str(engine), 'engine_fingerprint': fingerprint,
              'retention_directory': str(directory), 'producer': read(compiler / 'producer.json'),
              'proof': proof, 'compiler_input_sha256': inputs, 'source_pin': snapshot,
              'floor_sha256': inventory(compiler / 'seed'), 'sdk_produced': False,
              'scope': 'Actual existing compiler-only Nix producer; complete P/B/C byte reproduction and fresh boots. No SDK or language theorem.'}
    write(E / 'compiler-qualification.json', result)
    print(json.dumps({'status': 'passed', 'compiler': str(compiler), 'sdk_produced': False}), flush=True)
else:
    result = read(E / 'compiler-qualification.json')
    assert result['status'] == 'passed' and result['sdk_produced'] is False
    compiler = Path(result['compiler'])
    assert verify(compiler) == result['proof']
    assert inventory(compiler / 'seed') == result['floor_sha256']
    assert all(sha(R / name) == digest for name, digest in result['compiler_input_sha256'].items())
    floor = R / 'priv/bootstrap/seed'
    before = inventory(floor)
    assert set(before) == set(result['floor_sha256']), 'Review an inventory change before installation.'
    for name in before:
        assert subprocess.check_output(['git', 'show', commit + ':priv/bootstrap/seed/' + name], cwd=R) == (floor / name).read_bytes()
    write(E / 'compiler-floor-install.json', {'status': 'installing', 'compiler': str(compiler), 'before': before})
    for name in [*sorted(set(before) - {'manifest.term'}), 'manifest.term']:
        temporary = floor / ('.numeric-install-' + name)
        assert not temporary.exists()
        temporary.write_bytes((compiler / 'seed' / name).read_bytes())
        temporary.replace(floor / name)
    assert inventory(floor) == result['floor_sha256']
    write(E / 'compiler-floor-install.json', {'status': 'passed', 'compiler': str(compiler),
          'qualification_sha256': sha(E / 'compiler-qualification.json'), 'before': before,
          'after': inventory(floor), 'manifest_last': True, 'sdk_produced': False,
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'source_pin': snapshot})
    print(json.dumps({'status': 'installed', 'files': len(before), 'sdk_produced': False}), flush=True)
