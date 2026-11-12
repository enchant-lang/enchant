"""Run fresh dossier cells/checks only after this exact candidate qualifies."""
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
E = P / 'evidence/observation-semantics'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

stage = sys.argv[1]
assert stage in ('inputs', 'cells', 'check')
pin = read(P / 'sdk-pin.json')
assert pin == read(E / 'sdk-candidate.json') == read(E / 'qualification.json')['sdk_pin']
assert read(E / 'qualification.json')['status'] == 'passed'
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
kit = read(E / 'kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
names = {str(path.relative_to(R)) for path in (P / 'src').rglob('*.bl')}
names.update(str((P / name).relative_to(R)) for name in ('ATLAS.bl.org', 'sdk-pin.json', 'run-observation-dossier.py', 'dossier-inputs-check.bl'))
sources = {}
for name in sorted(names):
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    sources[name] = hashlib.sha256(body).hexdigest()
runtime = Path(tempfile.mkdtemp(prefix='formal-observation-dossier-runtime-'))
imports = [str(P / 'src'), str(Path(kit['root']) / 'bl-org-dossier/kit'),
           str(Path(kit['root']) / 'codebase-review/kit')]
request = [str(Path(pin['sdk']) / 'bin/bl'), '--cold']
for path in imports:
    request += ['-p', path]
request += (['run', str(P / 'dossier-inputs-check.bl')] if stage == 'inputs'
            else ['doc', 'run', str(P / 'ATLAS.bl.org')])
if stage == 'check':
    request.append('--check')
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--working-directory=' + str(R), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=1200', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           'BEAM_LISP_PATH=' + ':'.join(imports), *request]
prefix = 'dossier-' + stage
(E / (prefix + '-exit.json')).unlink(missing_ok=True)
(E / (prefix + '-source-pin.json')).write_text(json.dumps(
    {'code_commit': commit, 'source_sha256': sources, 'sdk_pin': pin,
     'kit_state_sha256': sha(E / 'kit-state.json'), 'project_import_paths': imports}, indent=2) + '\n')
(E / (prefix + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
(E / (prefix + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
started = time.monotonic()
try:
    with (E / (prefix + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
(E / (prefix + '-exit.json')).write_text(json.dumps(
    {'exit_code': code, 'runtime_retired': not runtime.exists(),
     'elapsed_seconds': time.monotonic() - started, 'document_sha256': sha(P / 'ATLAS.bl.org')}, indent=2) + '\n')
print(json.dumps({'stage': prefix, 'exit_code': code}))
raise SystemExit(code)
