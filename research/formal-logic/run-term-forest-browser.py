"""Warm the current prototype dossier, then run full and focused browser checks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/term-forest'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


pin = read(P / 'sdk-pin.json')
baseline = read(P / 'evidence/graph-consumers/dossier-qualification.json')
assert baseline['sdk_pin'] == pin
for name, digest in baseline['host_sources']['source_sha256'].items():
    assert sha(R / name) == digest, 'host/full-audit source changed: ' + name
kit = read(P / 'evidence/graph-consumers/kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest, 'kit source changed: ' + name
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
names = ['ATLAS.bl.org', 'TERM-FOREST.md', 'TERM-FOREST-PLAN.md', 'src/formal/term-forest.bl',
         'src/formal/term-forest-examples.bl', 'term-forest-browser.mjs', 'run-term-forest-browser.py',
         'qualify-term-forest-dossier.py', 'story-audit.mjs', 'browser-driver.mjs']
sources = {}
for name in names:
    path = P / name
    relative = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=R) == path.read_bytes()
    sources[relative] = sha(path)
write(E / 'dossier-source-pin.json', {'code_commit': commit, 'source_sha256': sources,
                                    'document_sha256': sha(P / 'ATLAS.bl.org'), 'sdk_pin': pin,
                                    'kit_state_sha256': sha(P / 'evidence/graph-consumers/kit-state.json')})
raw = subprocess.check_output(['systemctl', '--user', 'show', 'work-enchant-formal-review.service',
                               '--property=ActiveState,SubState,ExecMainPID,MemoryMax'], text=True)
state = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
assert state['ActiveState'] == 'active' and state['SubState'] == 'running' and state['MemoryMax'] == '2147483648'
assert state['ExecMainPID'] == baseline['host']['state']['ExecMainPID']
boots = [value.decode() for value in Path('/proc/' + state['ExecMainPID'] + '/cmdline').read_bytes().split(b'\0') if value.endswith(b'/boot.exs')]
assert boots == [pin['sdk'] + '/boot.exs']
with urllib.request.urlopen('http://127.0.0.1:24089/', timeout=60) as response:
    body = response.read()
    status = response.status
assert status == 200 and b'Keep typed arguments shared' in body and b'story-term-forest' in body
assert sha(P / 'ATLAS.bl.org') == read(E / 'dossier-source-pin.json')['document_sha256']
write(E / 'dossier-host.json', {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'state': state,
      'live_process_sdk_boot': boots[0], 'same_service_as_preceding_full_audit': True,
      'document_sha256': sha(P / 'ATLAS.bl.org'), 'http': {'status': status, 'bytes': len(body),
      'sha256': hashlib.sha256(body).hexdigest(), 'new_preview_present': True}})
for stage, script, folder, ceiling in [('full', 'story-audit.mjs', 'full-browser', 900),
                                      ('focused', 'term-forest-browser.mjs', 'focused-browser', 300)]:
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=2G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
               '/home/othman/.nix-profile/bin/node', str(P / script),
               'http://127.0.0.1:24089', str(E / folder)]
    write(E / (stage + '-browser-command.json'), command)
    (E / (stage + '-browser-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    with (E / (stage + '-browser-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(E / (stage + '-browser-exit.json'), {'exit_code': code})
    print(json.dumps({'stage': stage, 'browser_exit_code': code}), flush=True)
    if code:
        raise SystemExit(code)
