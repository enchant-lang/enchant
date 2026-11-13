"""Exercise the new owner and shared composer through explicit source projections."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/retained-owner-prototype'
E.mkdir(exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

pin = read(P / 'sdk-pin.json')
numeric = read(P / 'evidence/numeric-semantics/qualification.json')
assert numeric['status'] == 'passed' and numeric['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
composition = read(P / 'evidence/retained-question-prototype/qualification.json')
assert composition['status'] == 'passed' and composition['base_sdk_pin'] == pin
module = R / 'priv/lib/formal/retained-question.bl'
assert sha(module) == composition['source_pin']['source_sha256'][str(module.relative_to(R))]
modules = {
    'formal/retained-question.bl': (module, []),
    'formal/prototype-graph-execution.bl': (R / 'priv/lib/formal/graph-execution.bl', [
        ['(ns formal.graph-execution', '(ns formal.prototype-graph-execution']]),
    'formal/prototype-backend.bl': (R / 'priv/lib/formal/backend.bl', [
        ['(ns formal.backend ', '(ns formal.prototype-backend '],
        ['[formal.graph-execution :as graph-execution]', '[formal.prototype-graph-execution :as graph-execution]']]),
}
tests = [R / 'test/bl/formal/managed_graph_test.bl', R / 'test/bl/formal/retained_configuration_test.bl',
         P / 'retained-question-check.bl']
inputs = [*(value[0] for value in modules.values()), *tests, Path(__file__), P / 'sdk-pin.json']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in inputs:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'base_sdk_pin': pin,
                          'composition_qualification_sha256': sha(P / 'evidence/retained-question-prototype/qualification.json'),
                          'sdk_produced': False})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
runtime = Path(tempfile.mkdtemp(prefix='formal-retained-owner-'))
imports, checks, xdg = runtime / 'imports', runtime / 'checks', runtime / 'xdg'
(imports / 'formal').mkdir(parents=True)
checks.mkdir()
xdg.mkdir(mode=0o700)
projections = []

def project(source, destination, replacements):
    text = source.read_text()
    for old, new in replacements:
        assert text.count(old) == 1, (source, old)
        text = text.replace(old, new, 1)
    destination.write_text(text)
    saved = E / ('projected-' + destination.name)
    saved.write_text(text)
    projections.append({'source': str(source.relative_to(R)), 'source_sha256': sha(source),
                        'replacements': replacements, 'projected_sha256': sha(destination), 'saved': saved.name})

for name, (source, replacements) in modules.items():
    project(source, imports / name, replacements)
paths = []
for source in tests:
    replacements = [] if source == tests[-1] else [['[formal.backend :as backend]', '[formal.prototype-backend :as backend]']]
    if source == tests[0]:
        replacements += [['[formal.graph-execution :as execution]', '[formal.prototype-graph-execution :as execution]']]
    destination = checks / source.name
    project(source, destination, replacements)
    paths.append(str(destination))
write('projection.json', projections)
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-retained-owner-prototype-check-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(runtime), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(xdg), 'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           'BEAM_LISP_PATH=' + str(imports), pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports), 'test', *paths]
write('command.json', command)
(E / 'qualification.json').unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
write('exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
                    'runtime_retired': not runtime.exists()})
log = (E / 'checks.txt').read_text()
assert code == 0 and '3 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log, log[-7000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
for projection in projections:
    assert sha(E / projection['saved']) == projection['projected_sha256']
write('qualification.json', {
    'schema': 'bl.retained-owner-prototype-qualification.v1', 'status': 'passed',
    'recorded_utc': datetime.now(timezone.utc).isoformat(), 'source_pin': read(E / 'source-pin.json'),
    'projections': projections, 'base_sdk_pin': pin, 'sdk_produced': False,
    'command_sha256': sha(E / 'command.json'), 'log_sha256': sha(E / 'checks.txt'), 'exit': read(E / 'exit.json'),
    'compiler_proof_authority': False,
    'scope': 'Three source modules with explicit namespace/import projections alongside the qualified SDK. Existing managed native-owner controls, new authoritative metadata reads and label normalization, plus complete graph compatibility with the unchanged canonical owners. No replacement SDK, retained language request, historical execution authentication or compiler preservation theorem is established.'})
print(json.dumps({'status': 'passed', 'files': 3, 'sdk_produced': False}))
