"""Existing narrow semantics must survive the frozen wide library batch."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess, sys, tempfile, time

P = Path(__file__).resolve().parent
R = P.parent.parent
producer = P / 'evidence/wide-owner-prototype/native-smoke'
E = P / 'evidence/wide-owner-prototype/narrow-regressions'
assert not E.exists(), 'Archive a previous attempt before repeating this gate.'
E.mkdir()

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

q = read(producer / 'qualification.json')
pin = read(P / 'sdk-pin.json')
assert q['status'] == 'passed' and q['qualified_runtime_sdk'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert sha(producer / 'projection.json') == q['projection_sha256']
terminal = read(producer / 'owner-terminal.json')
terminal = terminal.get('state', terminal)
assert terminal['SubState'] == 'exited' and terminal['MainPID'] == '0'
assert terminal['Result'] == 'success' and terminal['ExecMainStatus'] == '0'
projection = [row for row in read(producer / 'projection.json') if row['saved'].startswith('projected/imports/')]
assert len(projection) == 35
names = [
    'managed_graph_test', 'retained_configuration_test', 'request_test',
    'word_request_test', 'word_owner_test', 'word_owner_admission_test',
    'scalar_text_interface_test', 'scalar_text_owner_test',
    'request_evidence_test', 'obligation_evidence_test', 'evidence_effect_test', 'evidence_oracle_test',
]
files = [R / 'test/bl/formal' / (name + '.bl') for name in names]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in [Path(__file__), *files]:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
modules = {}
for row in projection:
    source, projected = Path(row['source']), producer / row['saved']
    assert sha(source) == row['source_sha256'] and sha(projected) == row['projected_sha256']
    old = re.search(r'\(ns\s+([^\s)]+)', source.read_text()).group(1)
    new = re.search(r'\(ns\s+([^\s)]+)', projected.read_text()).group(1)
    modules[old] = new
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
                         'producer_qualification_sha256': sha(producer / 'qualification.json'),
                         'producer_projection_sha256': sha(producer / 'projection.json'),
                         'projected_modules': projection, 'in_sdk': False, 'sdk_produced': False})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
root = Path(tempfile.mkdtemp(prefix='formal-wide-narrow-regressions-'))
cwd, xdg, imports, checks = (root / name for name in ('consumer', 'xdg', 'imports', 'checks'))
cwd.mkdir(); xdg.mkdir(mode=0o700); imports.mkdir(); checks.mkdir()
for row in projection:
    relative = Path(row['saved']).relative_to('projected/imports')
    target = imports / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(producer / row['saved'], target)
test_projection = []
for source in files:
    content, changes = source.read_text(), []
    for old, new in sorted(modules.items(), key=lambda item: -len(item[0])):
        pattern = r'(\[)' + re.escape(old) + r'(?=\s|\])'
        content, count = re.subn(pattern, lambda match: match.group(1) + new, content)
        if count:
            changes.append({'namespace': old, 'projected_namespace': new, 'count': count})
    content = re.sub(r'\[formal\.wide-batch\.oracle\s*\]', '[formal.wide-batch.oracle :as oracle]', content)
    target = checks / source.name
    target.write_text(content)
    saved = E / 'projected-checks' / source.name
    saved.parent.mkdir(exist_ok=True)
    saved.write_text(content)
    test_projection.append({'source': str(source), 'source_sha256': sha(source),
                            'projected_sha256': sha(saved), 'saved': str(saved.relative_to(E)),
                            'namespace_changes': changes})
write('test-projection.json', test_projection)
command = ['timeout', '--kill-after=15', '3600', 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           'XDG_RUNTIME_DIR=' + str(xdg), 'BL_TEST_TIMEOUT=1200',
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports), 'test',
           *[str(checks / source.name) for source in files]]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(root)
log = (E / 'checks.txt').read_text()
green = f'{len(files)} file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json', {'exit_code': code, 'complete_green_summary': green,
                    'elapsed_seconds': time.monotonic() - started, 'private_runtime_retired': not root.exists()})
assert code == 0 and green, log[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
assert all(sha(producer / row['saved']) == row['projected_sha256'] for row in projection)
counts = re.findall(r'✓\s+(formal\.[^\s]+)\s+(\d+) passed', log)
assert len(counts) == len(files) and sum(int(count) for _, count in counts) >= 500
write('qualification.json', {'schema': 'bl.wide-owner-narrow-regressions.v1', 'status': 'passed',
                            'recorded_utc': datetime.now(timezone.utc).isoformat(), 'sdk_pin': pin,
                            'source_pin': read(E / 'source-pin.json'), 'test_projection_sha256': sha(E / 'test-projection.json'),
                            'assertions': sum(int(count) for _, count in counts), 'files': len(files),
                            'namespace_counts': dict(counts), 'in_sdk': False, 'sdk_produced': False,
                            'scope': 'Unchanged existing test bodies with require namespaces projected to the exact wide library batch: '
                                     'numeric graph owners, retained custody, portable requests, word and scalar-text request/owner boundaries, '
                                     'proof/premise/acceptance policy, evidence handlers and oracle effects. '
                                     'This is a project projection qualification; canonical immutable SDK integration is a separate gate.'})
print(json.dumps({'status': 'passed', 'files': len(files), 'assertions': sum(int(count) for _, count in counts)}))
