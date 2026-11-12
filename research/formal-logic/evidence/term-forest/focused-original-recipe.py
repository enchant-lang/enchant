"""Serial project-only preparation checks against the existing immutable SDK."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/term-forest'
E.mkdir(exist_ok=True)
pin = json.loads((P / 'sdk-pin.json').read_text())
assert hashlib.sha256((Path(pin['sdk']) / 'artifact.json').read_bytes()).hexdigest() == pin['descriptor_sha256']
stage = sys.argv[1]
assert stage == 'focused'
runtime = Path(tempfile.mkdtemp(prefix='formal-term-forest-runtime-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--working-directory=' + str(R), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), str(Path(pin['sdk']) / 'bin/bl'),
           '--cold', '-p', str(P / 'src'), 'test', str(P / 'test/term_forest_test.bl')]
(E / (stage + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
(E / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
try:
    with (E / (stage + '-checks.txt')).open('w') as stream:
        code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
(E / (stage + '-exit.json')).write_text(json.dumps({'exit_code': code, 'runtime_retired': not runtime.exists()}, indent=2) + '\n')
print(json.dumps({'stage': stage, 'exit_code': code}))
raise SystemExit(code)
