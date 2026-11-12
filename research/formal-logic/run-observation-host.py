"""Move the existing authorized review host to the exact checked SDK."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/observation-semantics'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

pin = read(P / 'sdk-pin.json')
assert pin == read(E / 'qualification.json')['sdk_pin'] and read(E / 'qualification.json')['status'] == 'passed'
assert read(E / 'dossier-check-exit.json')['exit_code'] == 0
assert read(E / 'dossier-check-exit.json')['document_sha256'] == sha(P / 'ATLAS.bl.org')
kit = read(E / 'kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
relative = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=R) == Path(__file__).read_bytes()
service = 'work-enchant-formal-review.service'
launcher = Path('/home/othman/.local/state/workstation/enchant-formal-review/run.sh')
before = launcher.read_bytes()
assert str(R).encode() in before and b'review-serve.bl' in before
(E / 'host-previous-launcher.sh').write_bytes(before)
(E / 'host-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
stop = ['systemctl', '--user', 'stop', service]
subprocess.run(stop, check=True)
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--working-directory=' + str(R), '--property=MemoryMax=1G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=180', '--property=KillMode=control-group',
           'env', 'WORK_BL=' + pin['sdk'] + '/bin/bl', '/home/othman/.nix-profile/bin/work',
           'serve', 'enchant-formal-review', '--http', '24089', '--cwd', str(R),
           '--env-file', '/home/othman/.config/baton-dossier/service.env', '--memory', '2G',
           '--ready-timeout', '120', '--', 'env', 'FORMAL_REVIEW_PROFILE=0',
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(P / 'src'),
           '-p', str(Path(kit['root']) / 'bl-org-dossier/kit'),
           '-p', str(Path(kit['root']) / 'codebase-review/kit'),
           'run', str(P / 'review-serve.bl'), '--', str(P / 'ATLAS.bl.org')]
(E / 'host-launch-exit.json').unlink(missing_ok=True)
(E / 'host-launch-command.json').write_text(json.dumps(command, indent=2) + '\n')
(E / 'host-launch-source-pin.json').write_text(json.dumps(
    {'code_commit': commit, 'source_sha256': {relative: sha(Path(__file__))},
     'sdk_pin': pin, 'document_sha256': sha(P / 'ATLAS.bl.org'), 'kit_state_sha256': sha(E / 'kit-state.json')}, indent=2) + '\n')
started = time.monotonic()
with (E / 'host-launch-checks.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
(E / 'host-launch-exit.json').write_text(json.dumps(
    {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
     'controller_sdk': pin['sdk'], 'previous_launcher_sha256': hashlib.sha256(before).hexdigest(),
     'current_launcher_sha256': sha(launcher)}, indent=2) + '\n')
print(json.dumps({'stage': 'host-launch', 'exit_code': code}))
raise SystemExit(code)
