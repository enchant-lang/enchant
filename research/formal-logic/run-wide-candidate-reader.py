"""Fresh candidate readers use the exact qualified wide namespace projection."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess, sys, tempfile, time

P = Path(__file__).resolve().parent
R = P.parent.parent
phase, reader = sys.argv[1:]
assert phase in ('native-smoke', 'native') and reader in ('one', 'two')
producer = P / 'evidence/wide-owner-prototype' / phase
E = producer / ('reader-' + reader)
assert not E.exists(), 'Archive an earlier reader attempt before repeating it.'
E.mkdir()

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

qualified = read(producer / 'qualification.json')
pin = read(P / 'sdk-pin.json')
assert qualified['status'] == 'passed' and qualified['qualified_runtime_sdk'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert qualified['observations_sha256'] == sha(producer / 'observations.json')
assert qualified['projection_sha256'] == sha(producer / 'projection.json')
terminal = read(producer / 'owner-terminal.json')
terminal = terminal.get('state', terminal)
assert terminal['SubState'] == 'exited' and terminal['MainPID'] == '0'
assert terminal['Result'] == 'success' and terminal['ExecMainStatus'] == '0'
observed = read(producer / 'observations.json')
assert len(observed['packets']) == qualified['candidate_packets']
for packet in observed['packets']:
    assert re.fullmatch(r'\d+-(z3|oxiz)\.json', packet['file'])
    assert sha(producer / 'packets' / packet['file']) == packet['sha256']
source = P / 'prototypes/wide-readers/candidate-reader.bl'
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in (Path(__file__), source):
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
projection = [row for row in read(producer / 'projection.json') if row['saved'].startswith('projected/imports/')]
assert len(projection) == 35
for row in projection:
    assert sha(producer / row['saved']) == row['projected_sha256']
    assert sha(Path(row['source'])) == row['source_sha256']
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
                        'producer_qualification_sha256': sha(producer / 'qualification.json'),
                        'producer_projection_sha256': sha(producer / 'projection.json'),
                        'projected_modules': projection, 'in_sdk': False, 'sdk_produced': False})
write('corpus.json', {'schema': 'bl.wide-owner-candidate-corpus.v1', 'producer-results': False,
                     'in-sdk': False, 'compiler-proof-authority': False, 'packets': observed['packets']})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
root = Path(tempfile.mkdtemp(prefix='formal-wide-candidate-reader-'))
cwd, xdg, imports = root / 'consumer', root / 'xdg', root / 'imports'
cwd.mkdir(); xdg.mkdir(mode=0o700); imports.mkdir()
for row in projection:
    relative = Path(row['saved']).relative_to('projected/imports')
    target = imports / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(producer / row['saved'], target)
command = ['timeout', '--kill-after=15', '3600', 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', 'XDG_RUNTIME_DIR=' + str(xdg),
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports), 'run', str(source), '--',
           str(E / 'corpus.json'), str(producer / 'packets'), str(E / 'observations.json')]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(root)
write('exit.json', {'exit_code': code, 'elapsed_seconds': time.monotonic() - started,
                    'private_runtime_retired': not root.exists()})
assert code == 0, (E / 'checks.txt').read_text()[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
assert all(sha(producer / row['saved']) == row['projected_sha256'] for row in projection)
result = read(E / 'observations.json')
assert result['status'] == 'passed' and result['sdk'] == pin['sdk']
assert result['packets'] == qualified['candidate_packets'] == len(result['rows'])
assert result['checks'] >= 14 * result['packets']
assert result['negative-controls'] == 8 and result['manual-schema-preload'] is False
assert result['warmed-atoms-stable'] is True and result['forged-native-report'] == 'unprivileged-claim'
assert type(result['native-exchanges']) is int and result['native-exchanges'] == result['oracle-calls'] == 0
assert all(row['logical-status'] == 'not-established' and row['consumer-status'] != 'accepted' for row in result['rows'])
write('qualification.json', {'schema': 'bl.wide-owner-candidate-reader-qualification.v1', 'status': 'passed',
                            'recorded_utc': datetime.now(timezone.utc).isoformat(), 'reader': reader,
                            'sdk_pin': pin, 'source_pin': read(E / 'source-pin.json'),
                            'observations_sha256': sha(E / 'observations.json'), 'packets': result['packets'],
                            'checks': result['checks'], 'negative_controls': 8,
                            'native_exchanges': 0, 'oracle_calls': 0, 'in_sdk': False,
                            'scope': 'Fresh process, frozen namespace projection and SDK only; no project generators. '
                                     'Original packet bytes and request/subject references, current pure admission, '
                                     'native claims with no installed replay or proof, refused stored success and changed binding, '
                                     'invented native status and identity remain unauthenticated claims. '
                                     'Zero current proof/premise allowances and stable warmed atoms. '
                                     'This prototype does not qualify immutable SDK integration or independent array/sequence/quantifier proofs.'})
print(json.dumps({'status': 'passed', 'reader': reader, 'packets': result['packets'], 'checks': result['checks']}))
