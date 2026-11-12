"""Warm the edited document once, then exercise its actual browser presentation."""
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/graph-consumers'
subprocess.run(['python3', P / 'capture-graph-consumers-host.py'], cwd=R, check=True)
subprocess.run(['python3', P / 'check-graph-consumers-media.py'], cwd=R, check=True)
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--working-directory=' + str(R), '--property=MemoryMax=2G',
           '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=900',
           '--property=KillMode=control-group', '/home/othman/.nix-profile/bin/node',
           str(P / 'story-audit.mjs'), 'http://127.0.0.1:24089', str(E / 'browser-audit')]
(E / 'browser-command.json').write_text(json.dumps(command, indent=2) + '\n')
(E / 'browser-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
with (E / 'browser-checks.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
(E / 'browser-exit.json').write_text(json.dumps({'exit_code': code}, indent=2) + '\n')
print(json.dumps({'browser_exit_code': code}), flush=True)
raise SystemExit(code)
