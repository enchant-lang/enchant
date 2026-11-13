"""Regenerate one compiler floor, then prepare one immutable semantic SDK.

Run `seed` first; review and commit its actual floor before `prepare`. Neither
stage changes the selected project pin or the live dossier host.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'
E.mkdir(exist_ok=True)
stage, = sys.argv[1:]
assert stage in ('seed', 'prepare')

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

baseline = read(E / 'baseline/sdk-pin.json')
assert read(E / 'baseline/state.json')['status'] == 'completed'
assert all(read(E / 'baseline/retirement.json').values())
assert read(P / 'sdk-pin.json') == baseline
assert sha(Path(baseline['sdk']) / 'artifact.json') == baseline['descriptor_sha256']
metadata = read(Path(baseline['sdk']) / 'artifact.json')
platform = Path(metadata['platform']) / 'bin'
assert (platform / 'elixir').is_file()
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
runtime_names = ['priv/boot/rt.bl', 'priv/host/decimal.bl', 'priv/host/num.bl',
                 'priv/lib/decimal.bl', 'priv/lib/js/rt.mjs', 'priv/lib/system/smt.bl']
names = runtime_names + ['test/bl/numeric_equality_test.bl', 'test/js/numeric-equality.test.mjs',
        'test/bl/system/smt_mod_test.bl', 'test/bl/datom/sequential_key_test.bl',
        'test/bl/datom/query_composite_join_test.bl', 'test/bl/host_num_test.bl',
        'test/bl/decimal_oracle_port_test.bl', 'scripts/regenerate-seed',
        'scripts/regenerate-seed.bl', str(Path(__file__).relative_to(R))]
if stage == 'prepare':
    assert read(E / 'seed-exit.json')['exit_code'] == 0
    names += [str(path.relative_to(R)) for path in sorted((R / 'priv/bootstrap/seed').iterdir()) if path.is_file()]
sources = {}
for name in names:
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    sources[name] = sha(R / name)
write(E / (stage + '-source-pin.json'), {'code_commit': commit, 'source_sha256': sources,
                                      'baseline_sdk_pin': baseline})
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
environment = os.environ.copy()
environment['PATH'] = str(platform) + ':' + environment['PATH']
recovery = None
if stage == 'seed':
    output = R / '.bl/regen' / ('formal-numeric-' + commit[:12])
    assert not output.exists(), 'Retain and inspect an earlier generation before restarting.'
    # The checkout's historical build/ can be older than its current compiler
    # sources. Recover through the qualified image, without a second checkout,
    # recompiling dependencies, or modifying any SDK bytes.
    recovery = Path(tempfile.mkdtemp(prefix='formal-numeric-recovery-'))
    (recovery / 'scripts').mkdir()
    wrapper = recovery / 'scripts/regenerate-seed'
    shutil.copy2(R / 'scripts/regenerate-seed', wrapper)
    # A full SDK carries immutable library forwarder routes. Loading those and
    # then recompiling a driver under the next compiler correctly refuses its
    # publication. Build a development image from only the qualified compiler
    # floor and source; no SDK library receipt enters this recovery VM.
    recovered_priv = recovery / 'priv'
    recovered_priv.mkdir()
    for entry in (Path(baseline['sdk']) / 'lib/beam_lisp-0.1.0/priv').iterdir():
        if entry.name not in ('precompiled.term', 'sdk-code.term'):
            (recovered_priv / entry.name).symlink_to(entry)
    recovered_ebin = recovery / 'build'
    recovered_ebin.mkdir()
    compiler_seed = Path(metadata['compiler']) / 'seed'
    floor_members = {}
    for entry in compiler_seed.iterdir():
        if entry.is_file():
            shutil.copy2(entry, recovered_ebin / entry.name)
            floor_members[entry.name] = sha(entry)
    assert len(floor_members) == 141 and 'Elixir.BeamLisp.beam' in floor_members
    shutil.copy2(Path(baseline['sdk']) / 'image/ebin/beam_lisp.app', recovered_ebin / 'beam_lisp.app')
    libraries = recovery / '.bl/lib'
    libraries.mkdir(parents=True)
    for library in sorted((Path(baseline['sdk']) / 'lib').iterdir()):
        if library.name == 'beam_lisp-0.1.0':
            app = libraries / library.name
            app.mkdir()
            (app / 'ebin').symlink_to(recovered_ebin)
            (app / 'priv').symlink_to(recovered_priv)
        else:
            (libraries / library.name).symlink_to(library)
    environment.update(BL_BOOTSTRAP_INSTALL='1', BL_REGEN_MEMORY_MAX='4G', BL_REGEN_ROOT=str(R))
    command = [str(wrapper), str(output)]
    policy = {'memory_max': '4G', 'memory_swap_max': '1G', 'install_after_fresh_source_floor_check': True,
              'toolchain_platform': metadata['platform'], 'output': str(output),
              'recovery_image': str(recovery), 'recovery_sdk': baseline['sdk'],
              'recovery_wrapper_sha256': sha(wrapper), 'target': str(R),
              'recovery_compiler': metadata['compiler'], 'compiler_floor_sha256': floor_members,
              'precompiled_sdk_library_index': False,
              'recovery_links': {str(path.relative_to(recovery)): str(path.resolve(strict=True))
                                 for path in recovery.rglob('*') if path.is_symlink()}}
else:
    fingerprint = subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
    command = [str(R / 'scripts/prepare-checkout-sdk')]
    policy = {'managed_preparation': True, 'engine_fingerprint': fingerprint,
              'toolchain_platform': metadata['platform']}
write(E / (stage + '-command.json'), {'argv': command, 'policy': policy})
(E / (stage + '-exit.json')).unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, env=environment, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    if recovery:
        shutil.rmtree(recovery)
        write(E / 'seed-recovery-retirement.json', {'path': str(recovery), 'retired': not recovery.exists()})
write(E / (stage + '-exit.json'), {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
if code:
    raise SystemExit(code)
assert all(sha(R / name) == digest for name, digest in sources.items())
if stage == 'prepare':
    assert fingerprint == subprocess.check_output([R / 'scripts/prepare-checkout-sdk', '--fingerprint'], text=True).strip()
    directory = R / '.bl/sdks' / fingerprint
    sdk = (directory / 'result-sdk').resolve(strict=True)
    engine = (directory / 'source-engine').resolve(strict=True)
    assert str(sdk).startswith('/nix/store/') and str(engine).startswith('/nix/store/')
    for name in runtime_names:
        assert sha(engine / name) == sources[name]
        assert sha(sdk / 'lib/beam_lisp-0.1.0' / name) == sources[name]
    candidate = {'sdk': str(sdk), 'descriptor_sha256': sha(sdk / 'artifact.json'), 'source': str(engine),
                 'base_commit': commit, 'engine_fingerprint': fingerprint}
    write(E / 'sdk-candidate.json', candidate)
print(json.dumps({'stage': stage, 'exit_code': code, 'project_pin_changed': False}), flush=True)
