"""One serial indexed-ledger projection check on an explicit selected SDK."""
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
E = P / 'evidence/indexed-ledger-prototype'
S = P / 'prototypes/indexed-ledger'
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
projection = read(S / 'projection.json')
assert projection['sdk_pin'] == pin
assert projection['patch_sha256'] == sha(P / 'proposals/indexed-ledger-read.patch')
for part in projection['changes']:
    assert sha(R / part['source']) == sha(Path(pin['source']) / part['source']) == part['source_sha256']
    assert sha(R / part['projection']) == part['projection_sha256']
assert read(P / 'evidence/retained-request/records-qualification.json')['status'] == 'passed'
for path in [*sorted(S.rglob('*.bl')), S / 'README.md', S / 'projection.json', Path(__file__),
             P / 'prepare-indexed-ledger-prototype.py', P / 'proposals/indexed-ledger-read.patch',
             P / 'evidence/retained-request/corpus.json', P / 'evidence/retained-request/records-qualification.json', P / 'sdk-pin.json']:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'sdk_pin': pin, 'source_sha256': digests})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
runtime = Path(tempfile.mkdtemp(prefix='formal-indexed-ledger-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-indexed-ledger-consumer-'))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-indexed-ledger-prototype-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=2G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=600', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime),
           '--setenv=INDEXED_LEDGER_CORPUS=' + str(P / 'evidence/retained-request/corpus.json'), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(S), 'test', str(S / 'indexed-ledger-check.bl')]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
text = (E / 'checks.txt').read_text()
green = '1 file(s) passed, 0 failed, 0 incoherent' in text and 'not green' not in text
write('exit.json', {'process_exit_code': code, 'complete_green_test_summary': green,
      'elapsed_seconds': time.monotonic() - started, 'runtime_retired': not runtime.exists(),
      'consumer_cwd_retired': not cwd.exists()})
assert code == 0 and green, text[-6000:]
rows = re.findall(r'✓\s+(formal.indexed-ledger-prototype-check)\s+(\d+) passed', text)
assert len(rows) == 1
counts = {name: int(total) for name, total in rows}
assert all(sha(R / name) == digest for name, digest in digests.items())
write('qualification.json', {'schema': 'bl.indexed-ledger-prototype-qualification.v1', 'status': 'passed',
      'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
      'source_pin': read(E / 'source-pin.json'), 'assertions': sum(counts.values()), 'assertion_runs': counts,
      'log_sha256': sha(E / 'checks.txt'), 'exit_sha256': sha(E / 'exit.json'),
      'compiler_proof_authority': False,
      'scope': 'Project-only exact namespace projection of indexed ledger lookup and request reopening, actual twelve-record fixture, one-row normalization traces and corruption isolation. No durable fresh-process or production SDK qualification is claimed.'})
print(json.dumps({'status': 'passed', 'assertions': sum(counts.values())}))
