"""Observe request/checking overhead on one exact saved native candidate."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tempfile, time

P = Path(__file__).resolve().parent
R = P.parent.parent
B = P / 'evidence/wide-owner-prototype/native-smoke'
E = P / 'evidence/wide-owner-prototype/reader-profile'
assert not E.exists(), 'Archive an earlier profile attempt before repeating it.'
E.mkdir()
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
q, pin = read(B / 'qualification.json'), read(P / 'sdk-pin.json')
assert q['status'] == 'passed' and q['qualified_runtime_sdk'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
source = P / 'prototypes/wide-readers/profile-reader.bl'
packet = read(B / 'observations.json')['packets'][0]
assert packet['file'] == '0-z3.json' and sha(B / 'packets' / packet['file']) == packet['sha256']
projection = [row for row in read(B / 'projection.json') if row['saved'].startswith('projected/imports/')]
assert len(projection) == 35 and q['projection_sha256'] == sha(B / 'projection.json')
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in [Path(__file__), source]:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
                         'producer_qualification_sha256': sha(B / 'qualification.json'),
                         'packet': packet, 'projected_modules': projection})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
root = Path(tempfile.mkdtemp(prefix='formal-wide-reader-profile-'))
cwd, xdg, imports = (root / name for name in ('consumer', 'xdg', 'imports'))
cwd.mkdir(); xdg.mkdir(mode=0o700); imports.mkdir()
for row in projection:
    assert sha(B / row['saved']) == row['projected_sha256']
    target = imports / Path(row['saved']).relative_to('projected/imports')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(B / row['saved'], target)
command = ['timeout', '--kill-after=15', '900', 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', 'XDG_RUNTIME_DIR=' + str(xdg),
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports), 'run', str(source), '--',
           str(B / 'packets' / packet['file']), str(E / 'observations.json')]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(root)
write('exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started, 'private_runtime_retired': not root.exists()})
assert code == 0, (E / 'checks.txt').read_text()[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
result = read(E / 'observations.json')
assert result['status'] == 'passed' and result['sdk'] == pin['sdk']
assert len(result['measurements']) == 7 and result['oracle-calls'] == 0
assert all(type(row['elapsed-us']) is int and row['elapsed-us'] >= 0 for row in result['measurements'])
assert all(type(row['call-counts']['native-exchange']) is int and row['call-counts']['native-exchange'] == 0 for row in result['measurements'])
assert result['packet-reference'] == packet['packet-reference']
write('qualification.json', {'schema': 'bl.wide-reader-profile-qualification.v1', 'status': 'passed',
                            'source_pin': read(E / 'source-pin.json'), 'observations_sha256': sha(E / 'observations.json'),
                            'scope': 'Seven serial operation windows on one exact native candidate, including first/warmed reopen and component checks. '
                                     'Actual function call counts and wall times with trace instrumentation; no native/oracle exchanges. '
                                     'This is diagnostic evidence on this host, not a speed comparison, physical cost proof or new mathematical capability.'})
print(json.dumps({'status': 'passed', 'windows': 7}))
