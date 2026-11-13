"""Serial observations of identical finite values through three real targets.

The baseline deliberately records discrepancies. Candidate mode requires the
proposed exact-value relation; neither mode qualifies raw collection key laws.
An explicit immutable SDK is mandatory, and no project pin is changed here.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/numeric-semantics'
mode, pin_file = sys.argv[1:]
assert mode in ('baseline', 'candidate')
E = E / mode
E.mkdir(parents=True, exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

pin = read(Path(pin_file).resolve(strict=True))
sdk = Path(pin['sdk'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
runtime_js = sdk / 'lib/beam_lisp-0.1.0/priv/lib/js/rt.mjs'
assert runtime_js.is_file()
assert sha(runtime_js) == sha(Path(pin['source']) / 'priv/lib/js/rt.mjs')
tools = read(P / 'evidence/observation-semantics/browser-tools.json')
node = tools['node']['executable']
assert Path(node).is_file()
assert subprocess.check_output(['nix-store', '--query', '--hash', tools['node']['package']], text=True).strip() == tools['node']['nar_hash']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [Path(__file__), P / 'semantic-number-corpus.bl', P / 'semantic-number-corpus.mjs',
           P / 'semantics-src/semantics/numeric.bl', P / 'proposals/finite-number-cases.json',
           P / 'proposals/make-finite-number-cases.py']
if mode == 'candidate':
    sources += [P / 'semantics-src/semantics/decimal-oracle.bl', P / 'proposals/decimal-oracle-cases.json',
                P / 'proposals/make-decimal-oracle.py', R / 'test/bl/decimal_oracle_port_test.bl']
digests = {}
for source in sources:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = sha(source)
snapshot = {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
            'runtime_js_sha256': sha(runtime_js), 'node': tools['node'],
            'mode': mode, 'compiler_proof_authority': False}
write(E / 'sdk-pin.json', pin)
fixture = P / 'proposals/finite-number-cases.json'
assert read(fixture)['qualified_runtime'] is False
subprocess.run([sys.executable, str(P / 'proposals/make-finite-number-cases.py'), '--check'], check=True, cwd=R)
if mode == 'candidate':
    subprocess.run([sys.executable, str(P / 'proposals/make-decimal-oracle.py'), '--check'], check=True, cwd=R)
runtime = Path(tempfile.mkdtemp(prefix='formal-numeric-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-numeric-consumer-'))
build = E / 'compiled'
assert not build.exists(), 'Retain or explicitly archive an earlier build before another writer starts.'
completed = []

def run(stage, request, *, beam=False, ceiling=900):
    assert all(sha(R / name) == digest for name, digest in digests.items())
    cap = '4G' if beam else '2G'
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
               '--unit=work-formal-numeric-' + mode + '-' + stage + '-' + pin['engine_fingerprint'][:12],
               '--working-directory=' + str(cwd), '--property=MemoryMax=' + cap,
               '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=' + str(ceiling),
               '--property=KillMode=control-group', '--setenv=XDG_RUNTIME_DIR=' + str(runtime),
               'env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY']
    if beam:
        command += [str(sdk / 'bin/bl'), '--cold']
    else:
        command.append(node)
    command += request
    write(E / (stage + '-source-pin.json'), snapshot)
    write(E / (stage + '-command.json'), command)
    (E / (stage + '-exit.json')).unlink(missing_ok=True)
    (E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    write(E / 'state.json', {'status': 'running', 'stage': stage, 'completed': completed, **snapshot})
    started = time.monotonic()
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(E / (stage + '-exit.json'), {'exit_code': code, 'elapsed_seconds': time.monotonic() - started})
    if code:
        raise subprocess.CalledProcessError(code, command)
    completed.append(stage)
    print(json.dumps({'stage': stage, 'exit_code': code}), flush=True)

try:
    profile = 'require-profile' if mode == 'candidate' else 'observe'
    for name in ('beam.json', 'js-direct.json', 'js-compiled.json'):
        (E / name).unlink(missing_ok=True)
    run('beam', ['run', str(P / 'semantic-number-corpus.bl'), '--', str(fixture), str(E / 'beam.json'), profile], beam=True)
    run('js-direct', [str(P / 'semantic-number-corpus.mjs'), str(runtime_js), str(fixture), str(E / 'js-direct.json'), profile], ceiling=120)
    run('js-build', ['js', 'build', 'semantics.numeric', '-p', str(P / 'semantics-src'), '--out', str(build)], beam=True, ceiling=1200)
    assert sha(build / 'rt.mjs') == sha(runtime_js), 'The compiled observer must use the selected runtime bytes.'
    run('js-compiled', [str(P / 'semantic-number-corpus.mjs'), str(build / 'rt.mjs'), str(fixture),
                        str(E / 'js-compiled.json'), profile, str(build)], ceiling=120)
    manifest = {str(path.relative_to(build)): sha(path) for path in sorted(build.rglob('*')) if path.is_file()}
    assert 'ns/semantics.numeric.mjs' in manifest and 'rt.mjs' in manifest
    write(E / 'compiled-manifest.json', manifest)
    with tarfile.open(E / 'compiled.tar.gz', 'w:gz') as archive:
        archive.add(build, arcname='compiled')
    shutil.rmtree(build)
    reports = {name: read(E / (name + '.json')) for name in ('beam', 'js-direct', 'js-compiled')}
    assert all(report['values'] == 30 and report['pairs'] == 900 for report in reports.values())
    write(E / 'observation-summary.json', {'schema': 'bl.finite-number-three-target-observations.v1',
          'status': 'observed', 'mode': mode, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
          'sdk_pin': pin, 'source_pin': snapshot,
          'differences': {name: len(report['differences']) for name, report in reports.items()},
          'reports_sha256': {name: sha(E / (name + '.json')) for name in reports},
          'compiled_manifest_sha256': sha(E / 'compiled-manifest.json'),
          'compiled_archive_sha256': sha(E / 'compiled.tar.gz'),
          'scope': 'Actual finite numeric leaf/nested equality and ordering observations. Raw key cardinalities remain separate; no compiler preservation theorem.',
          'compiler_proof_authority': False})
    write(E / 'state.json', {'status': 'completed', 'completed': completed, 'sdk_pin': pin})
except BaseException as error:
    write(E / 'state.json', {'status': 'failed', 'completed': completed, 'error': str(error), 'sdk_pin': pin})
    raise
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
    write(E / 'retirement.json', {'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists(),
                                'compiled_directory_retired': not build.exists()})
