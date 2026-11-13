"""One capped focused gate on the one immutable numeric candidate."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
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

stage, = sys.argv[1:]
pin = read(E / 'sdk-candidate.json')
sdk = Path(pin['sdk'])
assert sha(sdk / 'artifact.json') == pin['descriptor_sha256']
assert read(P / 'sdk-pin.json') == read(E / 'baseline/sdk-pin.json')
runtime_names = ['priv/boot/rt.bl', 'priv/host/decimal.bl', 'priv/host/num.bl',
                 'priv/lib/decimal.bl', 'priv/lib/js/rt.mjs', 'priv/lib/js/host-leaves.mjs',
                 'priv/lib/js/leaves.mjs', 'priv/lib/system/smt.bl']
for name in runtime_names:
    assert sha(R / name) == sha(Path(pin['source']) / name) == sha(sdk / 'lib/beam_lisp-0.1.0' / name)
files = []
project = False
ceiling = 900
if stage == 'focused':
    files = ['test/bl/numeric_equality_test.bl', 'test/bl/host_num_test.bl',
             'test/bl/host_decimal_test.bl', 'test/bl/decimal_oracle_port_test.bl',
             'test/bl/decimal_codec_port_test.bl', 'test/bl/system/smt_mod_test.bl',
             'test/bl/system/smt_quot_rem_test.bl']
elif stage == 'datom':
    files = ['test/bl/datom/sequential_key_test.bl', 'test/bl/datom/query_composite_join_test.bl',
             'test/bl/datom/offline_unique_test.bl']
elif stage == 'managed':
    files = ['test/bl/formal/shared_evaluator_test.bl', 'test/bl/formal/graph_admission_test.bl',
             'test/bl/formal/managed_graph_test.bl', 'test/bl/formal/request_test.bl',
             'test/bl/formal/graph_keys_test.bl']
elif stage == 'regression':
    project = True
    old = read(P / 'evidence/managed-graph/regression-command.json')
    files = old[old.index('test') + 1:]
    assert len(files) == 31
elif stage == 'native':
    project = True
    ceiling = 3600
    files = ['research/formal-logic/graph-consumers-check.bl']
elif stage in ('compiler-floor', 'preflight', 'preflight-controls', 'js-unit'):
    pass
else:
    raise ValueError(stage)
fixture_names = (['priv/host/num.bl', 'priv/host/decimal.bl', 'priv/host/decimal_inspect.bl']
                 if stage == 'focused' else [])
names = runtime_names + files + fixture_names + [str(Path(__file__).relative_to(R))]
if project:
    names += [str(path.relative_to(R)) for path in sorted((P / 'src').rglob('*.bl'))]
if stage == 'compiler-floor':
    names += ['scripts/check-produced-compiler.py']
elif stage == 'preflight':
    names += ['scripts/sdk-preflight', 'scripts/sdk-preflight.bl']
elif stage == 'preflight-controls':
    names += ['test/scripts/sdk_preflight.py']
elif stage == 'js-unit':
    names += ['test/js/numeric-equality.test.mjs', 'test/js/decimal-api.test.mjs',
              'test/js/rt.test.mjs', 'test/js/leaves.test.mjs',
              'research/formal-logic/evidence/numeric-semantics/float-format.json',
              'research/formal-logic/evidence/numeric-semantics/float-format-exit.json',
              'research/formal-logic/decimal-format-probe.bl']
    for path in (R / 'priv/lib/js').glob('*.mjs'):
        name = str(path.relative_to(R))
        assert sha(path) == sha(sdk / 'lib/beam_lisp-0.1.0' / name)
        names.append(name)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for name in sorted(set(names)):
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == (R / name).read_bytes()
    sources[name] = sha(R / name)
runtime = Path(tempfile.mkdtemp(prefix='formal-numeric-gate-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-numeric-gate-consumer-'))
# Host ABI tests compile their pinned source relative to BeamLisp/cwd.
# Supply exactly those immutable SDK files, without adding checkout code paths.
for name in fixture_names:
    packaged = sdk / 'lib/beam_lisp-0.1.0' / name
    assert sha(packaged) == sources[name]
    target = cwd / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(packaged, target)
cap = '4G'
if files:
    request = [str(sdk / 'bin/bl'), '--cold']
    if project:
        request += ['-p', str(P / 'src')]
    request += (['run', str(R / files[0]), '--', str(E / 'native.json')] if stage == 'native'
                else ['test', *[str(R / name) for name in files]])
elif stage == 'compiler-floor':
    request = [sys.executable, str(R / 'scripts/check-produced-compiler.py'), '--sdk', str(sdk),
               '--out', str(E / 'produced-compiler.json')]
elif stage == 'preflight':
    request = [sys.executable, str(R / 'scripts/sdk-preflight'), '--sdk', str(sdk),
               '--root', pin['source'], '--out', str(E / 'source-preflight.json')]
elif stage == 'preflight-controls':
    request = [sys.executable, str(R / 'test/scripts/sdk_preflight.py'), '--sdk', str(sdk)]
elif stage == 'js-unit':
    tools = read(P / 'evidence/observation-semantics/browser-tools.json')
    assert subprocess.check_output(['nix-store', '--query', '--hash', tools['node']['package']], text=True).strip() == tools['node']['nar_hash']
    # The unit test imports checkout JS source; bind it to the exact candidate
    # bytes here. SDK-only/direct and actual compiled routes are separate gates.
    request = [tools['node']['executable'], '--test', '--test-concurrency=1', str(R / 'test/js/numeric-equality.test.mjs'),
               str(R / 'test/js/decimal-api.test.mjs'), str(R / 'test/js/rt.test.mjs'),
               str(R / 'test/js/leaves.test.mjs')]
    cap, ceiling = '2G', 120
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-numeric-' + stage + '-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=' + cap, '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime)]
if stage == 'regression':
    (E / 'regression').mkdir(exist_ok=True)
    command += ['--setenv=ENCHANT_FORMAL_EVIDENCE_ROOT=' + str(E / 'regression')]
command += ['env', '-u', 'BEAM_LISP_PATH', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', *request]
write(E / (stage + '-source-pin.json'), {'code_commit': commit, 'sdk_pin': pin, 'source_sha256': sources})
write(E / (stage + '-command.json'), command)
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
(E / (stage + '-exit.json')).unlink(missing_ok=True)
if stage == 'native':
    (E / 'native.json').unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
assert all(sha(R / name) == digest for name, digest in sources.items())
write(E / (stage + '-exit.json'), {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
      'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists()})
print(json.dumps({'stage': stage, 'exit_code': code}), flush=True)
raise SystemExit(code)
