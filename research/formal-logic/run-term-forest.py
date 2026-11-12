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
if stage == 'focused':
    request = ['test', str(P / 'test/term_forest_test.bl')]
elif stage == 'corpus':
    request = ['run', str(P / 'term-forest-check.bl'), '--', str(E / 'corpus.json')]
elif stage == 'native':
    request = ['run', str(P / 'term-forest-native.bl'), '--', str(E / 'native.json')]
elif stage == 'sharing':
    request = ['run', str(P / 'term-forest-sharing.bl'), '--', str(E / 'sharing.json')]
else:
    raise ValueError(stage)
runtime = Path(tempfile.mkdtemp(prefix='formal-term-forest-runtime-'))
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [P / 'src/formal/term-forest.bl', P / 'test/term_forest_test.bl', P / 'term-forest-check.bl',
           P / 'term-forest-native.bl', P / 'term-forest-sharing.bl',
           P / 'src/formal/term-forest-examples.bl', Path(__file__), P / 'sdk-pin.json']
digests = {}
for source in sources:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = hashlib.sha256(source.read_bytes()).hexdigest()
(E / (stage + '-source-pin.json')).write_text(json.dumps({'code_commit': commit, 'source_sha256': digests,
                                                        'sdk_pin': pin}, indent=2) + '\n')
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
           '--working-directory=' + str(R), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), str(Path(pin['sdk']) / 'bin/bl'),
           '--cold', '-p', str(P / 'src'), *request]
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
