"""One serial project prototype check on an explicit selected SDK."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-resource-prototype'
S = P / 'prototypes/word-resources'
E.mkdir(exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

pin = read(P / 'sdk-pin.json')
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in [*sorted(S.rglob('*.bl')), S / 'README.md', Path(__file__), P / 'sdk-pin.json']:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'sdk_pin': pin, 'source_sha256': digests})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
runtime = Path(tempfile.mkdtemp(prefix='formal-word-plan-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-word-plan-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-word-resource-prototype-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=2G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=300', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(S), 'test', str(S / 'word-resource-check.bl'), str(S / 'word-coordinate-check.bl')]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
text = (E / 'checks.txt').read_text()
green = '2 file(s) passed, 0 failed, 0 incoherent' in text and 'not green' not in text
write('exit.json', {'process_exit_code': code, 'complete_green_test_summary': green,
      'elapsed_seconds': time.monotonic() - started, 'runtime_retired': not runtime.exists(),
      'consumer_cwd_retired': not cwd.exists()})
assert code == 0 and green, text[-6000:]
rows = re.findall(r'✓\s+(formal.word-(?:resource|coordinate)-prototype-check)\s+(\d+) passed', text)
assert len(rows) == 2
counts = {name: int(total) for name, total in rows}
assert all(sha(R / name) == digest for name, digest in digests.items())
write('qualification.json', {'schema': 'bl.word-resource-prototype-qualification.v1', 'status': 'passed',
      'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
      'source_pin': read(E / 'source-pin.json'), 'assertions': sum(counts.values()), 'assertion_runs': counts,
      'log_sha256': sha(E / 'checks.txt'), 'exit_sha256': sha(E / 'exit.json'),
      'compiler_proof_authority': False,
      'scope': 'Project-only declared-width resource planner and graph coordinate reader. No managed graph/profile admission, complete request reservation or runtime-cost theorem is claimed.'})
print(json.dumps({'status': 'passed', 'assertions': sum(counts.values())}))
