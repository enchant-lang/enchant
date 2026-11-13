"""Check the current dossier and actual upgraded host, focused before full."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/observation-semantics'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

focused_only = sys.argv[1:] == ['--focused-only']
assert not sys.argv[1:] or focused_only
pin = read(P / 'sdk-pin.json')
assert pin == read(E / 'qualification.json')['sdk_pin'] == read(E / 'sdk-candidate.json')
assert read(E / 'qualification.json')['status'] == 'passed'
kit = read(E / 'kit-state.json')
browser_tools = {}
for name, executable in (('node', 'node'), ('chromium', 'chromium')):
    path = Path('/home/othman/.nix-profile/bin') / executable
    path = path.resolve(strict=True)
    assert str(path).startswith('/nix/store/')
    root = Path(*path.parts[:4])
    retention = R / ('.bl/formal-dossier-' + name)
    subprocess.run(['nix-store', '--add-root', retention, '--indirect', '--realise', root],
                   check=True, stdout=subprocess.DEVNULL)
    browser_tools[name] = {'executable': str(path), 'package': str(root),
                          'nar_hash': subprocess.check_output(['nix-store', '--query', '--hash', root], text=True).strip()}
write(E / 'browser-tools.json', browser_tools)
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
names = {str(path.relative_to(R)) for path in (P / 'src').rglob('*.bl')}
names.update(str((P / name).relative_to(R)) for name in (
    'ATLAS.bl.org', 'sdk-pin.json', 'GRAPH-OBSERVATIONS.md', 'INTEGER-PREFLIGHT.md',
    'TERM-FOREST-RESOURCE-PLAN.md', 'run-observation-browser.py', 'observation-browser.mjs',
    'story-audit.mjs', 'browser-driver.mjs', 'review-serve.bl', 'dossier-local.css', 'presentation.css'))
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = {}
for name in sorted(names):
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    sources[name] = hashlib.sha256(body).hexdigest()
snapshot = {'code_commit': commit, 'source_sha256': sources, 'sdk_pin': pin,
            'document_sha256': sha(P / 'ATLAS.bl.org'), 'kit_state_sha256': sha(E / 'kit-state.json')}
if focused_only:
    previous = read(E / 'full-browser-source-pin.json')
    assert previous['sdk_pin'] == pin and previous['document_sha256'] == snapshot['document_sha256']
    assert previous['kit_state_sha256'] == snapshot['kit_state_sha256']
    assert read(E / 'full-browser-exit.json')['exit_code'] == 0
    for name, digest in previous['source_sha256'].items():
        if name not in ('research/formal-logic/observation-browser.mjs', 'research/formal-logic/run-observation-browser.py'):
            assert sha(R / name) == digest
else:
    write(E / 'full-browser-source-pin.json', snapshot)
    (E / 'full-browser-exit.json').unlink(missing_ok=True)
write(E / 'dossier-source-pin.json', snapshot)
raw = subprocess.check_output(['systemctl', '--user', 'show', 'work-enchant-formal-review.service',
                               '--property=ActiveState,SubState,ExecMainPID,MemoryMax'], text=True)
state = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
assert state['ActiveState'] == 'active' and state['SubState'] == 'running' and state['MemoryMax'] == '2147483648'
boots = [x.decode() for x in Path('/proc/' + state['ExecMainPID'] + '/cmdline').read_bytes().split(b'\0') if x.endswith(b'/boot.exs')]
assert boots == [pin['sdk'] + '/boot.exs']
process_kit = [x.decode().split('=', 1)[1] for x in
               Path('/proc/' + state['ExecMainPID'] + '/environ').read_bytes().split(b'\0')
               if x.startswith(b'FORMAL_REVIEW_KIT_ROOT=')]
assert process_kit == [kit['root']], 'actual host must select the immutable kit'
with urllib.request.urlopen('http://127.0.0.1:24089/', timeout=60) as response:
    body, status = response.read(), response.status
assert status == 200 and b'let-observations-demand-only-what-they-display' in body and b'cell-story-graph-observations' in body
write(E / 'dossier-host.json', {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'state': state,
      'live_process_sdk_boot': boots[0], 'live_process_kit_root': process_kit[0], 'kit_commit': kit['commit'],
      'document_sha256': sha(P / 'ATLAS.bl.org'), 'http': {'status': status, 'bytes': len(body),
      'sha256': hashlib.sha256(body).hexdigest()}, 'review_url': 'https://work.tailcb5318.ts.net:18100/'})
stages = [('focused', 'observation-browser.mjs', 300)]
if not focused_only:
    stages.append(('full', 'story-audit.mjs', 900))
for stage, script, ceiling in stages:
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=2G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
               '--setenv=FORMAL_BROWSER_EXECUTABLE=' + browser_tools['chromium']['executable'],
               browser_tools['node']['executable'], str(P / script), 'http://127.0.0.1:24089', str(E / (stage + '-browser'))]
    (E / (stage + '-browser-exit.json')).unlink(missing_ok=True)
    write(E / (stage + '-browser-command.json'), command)
    (E / (stage + '-browser-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    with (E / (stage + '-browser-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(E / (stage + '-browser-exit.json'), {'exit_code': code})
    print(json.dumps({'stage': stage, 'browser_exit_code': code}), flush=True)
    if code:
        raise SystemExit(code)
