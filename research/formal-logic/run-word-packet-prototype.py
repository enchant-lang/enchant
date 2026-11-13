"""Cold packet API check, reusing the exact already checked namespace projections."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-integration-prototype/packets'
B = E.parent / 'pure'
E.mkdir(exist_ok=True)
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')
base = read(B / 'qualification.json')
pin = read(P / 'sdk-pin.json')
assert base['status'] == 'passed' and base['base_sdk_pin'] == pin
for name, digest in base['source_pin']['source_sha256'].items():
    assert sha(R / name) == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in [Path(__file__), P / 'word-packet-reader.bl', P / 'evidence/retained-request/corpus.json']:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'base_sdk_pin': pin,
                        'projection_qualification_sha256': sha(B / 'qualification.json')})
runtime = Path(tempfile.mkdtemp(prefix='formal-cold-packet-prototype-'))
imports, cwd, xdg = runtime / 'imports', runtime / 'consumer', runtime / 'xdg'
imports.mkdir(); cwd.mkdir(); xdg.mkdir(mode=0o700)
for row in base['projections']:
    if '/imports/' not in row['saved']:
        continue
    source = B / row['saved']
    assert sha(source) == row['projected_sha256']
    target = imports / Path(row['saved']).relative_to('projected/imports')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
source = P / 'word-packet-reader.bl'
text = source.read_text()
assert text.count('[formal.request-record :as record]') == 1
text = text.replace('[formal.request-record :as record]', '[formal.word-batch.request-record :as record]')
program = runtime / 'reader.bl'
program.write_text(text)
(E / 'projected-reader.bl').write_text(text)
write('projection.json', {'source': str(source.relative_to(R)), 'source_sha256': sha(source),
      'replacement': ['[formal.request-record :as record]', '[formal.word-batch.request-record :as record]'],
      'projected_sha256': sha(program)})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=600', '--property=KillMode=control-group', '--setenv=XDG_RUNTIME_DIR=' + str(xdg),
           'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', 'BEAM_LISP_PATH=' + str(imports),
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports), 'run', str(program), '--',
           str(P / 'evidence/retained-request/corpus.json'), str(E / 'packets.json')]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
write('exit.json', {'exit_code': code, 'runtime_retired': not runtime.exists(), 'elapsed_seconds': time.monotonic() - started})
assert code == 0, (E / 'checks.txt').read_text()[-5000:]
result = read(E / 'packets.json')
assert result['records'] == 12 and result['manual-schema-preload'] is False
assert result['source-payload-execution'] is False
assert all(sha(R / name) == digest for name, digest in digests.items())
write('qualification.json', {'schema': 'bl.closed-packet-prototype-qualification.v1', 'status': 'passed',
      'recorded_utc': datetime.now(timezone.utc).isoformat(), 'base_sdk_pin': pin,
      'source_pin': read(E / 'source-pin.json'), 'records': 12, 'manual_schema_preload': False,
      'result_sha256': sha(E / 'packets.json'), 'exit': read(E / 'exit.json'),
      'compiler_proof_authority': False,
      'scope': 'One fresh process imports the record API and reads the actual twelve saved graph packets using exact checked namespace projections. No SDK-only or formal exchange-counter qualification is claimed.'})
print(json.dumps({'status': 'passed', 'records': 12, 'manual_schema_preload': False}))
