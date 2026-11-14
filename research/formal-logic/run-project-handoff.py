"""Validate and render the Org-native handoff on the qualified selected SDK."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys, tempfile, time
P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/project-handoff'
E.mkdir(exist_ok=True)
assert not (E / 'exit.json').exists(), 'Retain an earlier attempt before repeating.'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
pin = read(P / 'sdk-pin.json')
assert read(P / 'evidence/obligation-integration/qualification.json')['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
kit_state = read(P / 'evidence/obligation-presentation/kit-state.json')
kit = Path(kit_state['root']) / 'bl-org-dossier/kit'
for name, digest in kit_state['rendering_source_sha256'].items():
    assert sha(Path(kit_state['root']) / name) == digest
for name in ['dossier/roster.bl', 'dossier/roster/model.bl', 'dossier/roster/view.bl', 'roster.css', 'roster.js']:
    assert sha(kit / name) == sha(Path('/home/othman/projects/enchanted-skills/bl-org-dossier/kit') / name)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
paths = [Path(__file__), P / 'PROJECT.bl.org', P / 'render-project-handoff.bl', P / 'sdk-pin.json',
         P / 'src/formal/review-svg.bl']
digests = {}
for path in paths:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
links = sorted(set(re.findall(r'\[\[file:([^\]]+)\]', (P / 'PROJECT.bl.org').read_text())))
for name in links: assert (P / name).is_file()
write('source-pin.json', {'code_commit': commit, 'sdk_pin': pin, 'source_sha256': digests,
      'kit_state_sha256': sha(P / 'evidence/obligation-presentation/kit-state.json'),
      'kit_root': str(kit), 'links': links})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
root = Path(tempfile.mkdtemp(prefix='formal-project-handoff-'))
cwd, xdg = root / 'consumer', root / 'xdg'
cwd.mkdir(); xdg.mkdir(mode=0o700)
command = ['timeout', '--kill-after=15', '360', 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', 'XDG_RUNTIME_DIR=' + str(xdg),
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(kit), '-p', str(P / 'src'),
           'run', str(P / 'render-project-handoff.bl'), '--', str(P), str(kit), str(E)]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
finally: shutil.rmtree(root)
write('exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
                    'private_runtime_retired': not root.exists()})
assert code == 0, (E / 'checks.txt').read_text()[-4000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
v = read(E / 'model.json')
assert v['status'] == 'passed' and v['tasks'] == 18 and v['workstreams'] == 9
write('qualification.json', {'status': 'passed', 'scope': 'Org task graph, exact file links, zero executable cells, '
      'unchanged document check and read-only captured roster rendering. Browser inspection is separate; '
      'no new runtime, theory, SDK or authenticated review workflow qualification.',
      'source_pin': read(E / 'source-pin.json'), 'tasks': 18, 'workstreams': 9,
      'model_sha256': sha(E / 'model.json'), 'html_sha256': sha(E / 'index.html')})
print(json.dumps({'status': 'passed', 'tasks': 18, 'workstreams': 9, 'sdk_changed': False}))
