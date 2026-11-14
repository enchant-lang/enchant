"""Check the narrative-only wide chapter without replacing historical receipts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess, sys, tempfile, time, urllib.request

P = Path(__file__).resolve().parent
R = P.parent.parent
H = P / 'evidence/obligation-presentation'
E = P / 'evidence/wide-owner-presentation'
E.mkdir(exist_ok=True)
stage, = sys.argv[1:]
assert stage in ('check', 'browser')

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

assert not (E / (stage + '-exit.json')).exists(), 'Archive the earlier attempt before repeating it.'
pin, parent, kit = read(P / 'sdk-pin.json'), read(H / 'dossier-qualification.json'), read(H / 'kit-state.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert parent['kit_state_sha256'] == sha(H / 'kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
document = P / 'ATLAS.bl.org'
old_commit = read(H / 'dossier-check-source-pin.json')['code_commit']
previous = subprocess.check_output(['git', 'show', old_commit + ':research/formal-logic/ATLAS.bl.org'], cwd=R)
assert hashlib.sha256(previous).hexdigest() == parent['document_sha256']
def cells(text):
    return re.findall(r'(?ms)^#\+begin_src beam-lisp[^\n]*\n.*?^#\+end_src\s*$', text)
def results(text):
    return re.findall(r'(?m)^#\+RESULTS:[^\n]*\n(?:(?:[:|].*|\[\[.*)\n)*', text)
assert len(cells(document.read_text())) == 94
assert cells(previous.decode()) == cells(document.read_text()), 'This refresh permits narrative changes only.'
assert results(previous.decode()) == results(document.read_text()), 'Original results must stay exact.'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
paths = [Path(__file__), document, P / 'wide-request-browser.mjs', P / 'browser-driver.mjs',
         P / 'sdk-pin.json', P / 'dossier-local.css', P / 'presentation.css',
         H / 'dossier-qualification.json', H / 'kit-state.json',
         *sorted((P / 'src').rglob('*.bl')), *sorted((P / 'dossier').rglob('*.bl'))]
digests = {}
for path in paths:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
snapshot = {'code_commit': commit, 'sdk_pin': pin, 'document_sha256': sha(document),
            'source_sha256': digests, 'parent_presentation_sha256': sha(H / 'dossier-qualification.json'),
            'kit_state_sha256': sha(H / 'kit-state.json'), 'cell_sources_unchanged': True, 'results_unchanged': True}
write(stage + '-source-pin.json', snapshot)
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
runtime = None
if stage == 'check':
    runtime = Path(tempfile.mkdtemp(prefix='formal-wide-dossier-refresh-'))
    imports = [P / 'src', P / 'dossier', *[Path(kit['root']) / name / 'kit' for name in
                                        ('bl-org-dossier', 'codebase-review', 'research-elements')]]
    command = ['timeout', '--kill-after=15', '1200', 'env', '-u', 'BEAM_LISP_PATH',
               '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', 'XDG_RUNTIME_DIR=' + str(runtime),
               'BEAM_LISP_PATH=' + ':'.join(map(str, imports)), pin['sdk'] + '/bin/bl', '--cold']
    for path in imports:
        command += ['-p', str(path)]
    command += ['doc', 'run', str(document), '--check']
else:
    assert read(E / 'check-exit.json')['exit_code'] == 0
    assert read(E / 'check-source-pin.json')['document_sha256'] == snapshot['document_sha256']
    tools = read(H / 'browser-tools.json')
    for tool in tools.values():
        assert subprocess.check_output(['nix-store', '--query', '--hash', tool['package']], text=True).strip() == tool['nar_hash']
    write('browser-tools.json', tools)
    state = subprocess.check_output(['systemctl', '--user', 'show', 'work-enchant-formal-review.service',
                                     '--property=ActiveState,SubState,ExecMainPID'], text=True)
    state = dict(line.split('=', 1) for line in state.splitlines())
    assert state['ActiveState'] == 'active' and state['SubState'] == 'running'
    args = Path('/proc/' + state['ExecMainPID'] + '/cmdline').read_bytes().split(b'\0')
    assert (pin['sdk'] + '/boot.exs').encode() in args
    responses = {}
    for name, url in [('local', 'http://127.0.0.1:24089/'), ('tailnet', 'https://work.tailcb5318.ts.net:18100/')]:
        with urllib.request.urlopen(url, timeout=60) as response:
            body = response.read()
            assert response.status == 200 and b'id="one-request-more-theories"' in body
            responses[name] = {'url': url, 'status': response.status, 'sha256': hashlib.sha256(body).hexdigest()}
    write('host.json', {'state': state, 'responses': responses, 'document_sha256': sha(document)})
    command = ['timeout', '--kill-after=15', '300', 'env', 'CHROMIUM_BIN=' + tools['chromium']['executable'],
               tools['node']['executable'], str(P / 'wide-request-browser.mjs'),
               'http://127.0.0.1:24089', str(E / 'browser')]
write(stage + '-command.json', command)
started = time.monotonic()
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    if runtime:
        shutil.rmtree(runtime)
write(stage + '-exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
                            'private_runtime_retired': runtime is None or not runtime.exists(),
                            'document_sha256': sha(document)})
assert code == 0, (E / (stage + '-checks.txt')).read_text()[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
if stage == 'check':
    assert '94 cells, 0 cell errors' in (E / 'check-checks.txt').read_text()
else:
    audit = read(E / 'browser/audit.json')
    assert audit['passed'] is True and len(audit['checks']) >= 35 and len(audit['screenshots']) == 12
write(stage + '-qualification.json', {'schema': 'bl.wide-owner-dossier-refresh.v1', 'status': 'passed',
                                     'stage': stage, 'recorded_utc': datetime.now(timezone.utc).isoformat(),
                                     'source_pin': snapshot, 'scope': 'Narrative-only wide chapter; original 94 cell sources and results '
                                     'are byte-identical to the qualified obligation presentation. '
                                     'This receipt records the selected stage only. Actual visual review is separate.'})
print(json.dumps({'status': 'passed', 'stage': stage, 'document_sha256': snapshot['document_sha256']}))
