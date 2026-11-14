"""Qualify one local full-reference reuse on the frozen wide library batch."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, subprocess, sys, tempfile, time

P = Path(__file__).resolve().parent
R = P.parent.parent
B = P / 'evidence/wide-owner-prototype/native-smoke'
phase, = sys.argv[1:]
assert phase in ('identities', 'narrow')
E = P / 'evidence/wide-reference-reuse' / phase
E.mkdir(parents=True, exist_ok=True)
assert all(path.is_dir() and path.name.startswith('before-') for path in E.iterdir()), 'Archive an earlier attempt.'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
pin, native = read(P / 'sdk-pin.json'), read(B / 'qualification.json')
assert native['status'] == 'passed' and native['qualified_runtime_sdk'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
assert native['projection_sha256'] == sha(B / 'projection.json')
for suffix in ('reader-one', 'reader-two'):
    receipt = read(B / suffix / 'qualification.json')
    assert receipt['status'] == 'passed' and receipt['packets'] == 20 and receipt['sdk_pin'] == pin
    terminal = read(B / suffix / 'owner-terminal.json')['state']
    assert terminal['SubState'] == 'exited' and terminal['MainPID'] == '0'
    assert terminal['Result'] == 'success' and terminal['ExecMainStatus'] == '0'
original = Path(pin['source']) / 'priv/lib/formal/request-evidence.bl'
override = P / 'prototypes/wide-owner/formal/request-evidence.bl'
expected = original.read_text().replace('        judgment (obligation/judge vacuity logical checked-premise)]',
    '        judgment (obligation/judge vacuity logical checked-premise)\n'
    '        ;; The checked immutable carrier has one content reference per recheck.\n'
    '        ;; Reuse that exact full-data reference; no format or authority changes.\n'
    '        evidence-reference (graph/of e)]')
expected = expected.replace(':evidence-reference (graph/of e) :checking-policy policy',
                            ':evidence-reference evidence-reference :checking-policy policy')
expected = expected.replace(':checking-reference (graph/of [(request/reference r) (graph/of e) policy])',
                            ':checking-reference (graph/of [(request/reference r) evidence-reference policy])')
assert override.read_text() == expected and expected.count('(graph/of e)') == 1
projection = [row for row in read(B / 'projection.json') if row['saved'].startswith('projected/imports/')]
assert len(projection) == 35
modules = {}
for row in projection:
    assert sha(Path(row['source'])) == row['source_sha256'] and sha(B / row['saved']) == row['projected_sha256']
    old = re.search(r'\(ns\s+([^\s)]+)', Path(row['source']).read_text()).group(1)
    new = re.search(r'\(ns\s+([^\s)]+)', (B / row['saved']).read_text()).group(1)
    modules[old] = new
if phase == 'identities':
    tests = [P / 'prototypes/wide-owner/wide-owner-pure-check.bl',
             P / 'prototypes/wide-readers/reference-reuse-check.bl']
else:
    tests = [R / 'test/bl/formal' / (name + '.bl') for name in [
        'managed_graph_test', 'retained_configuration_test', 'request_test',
        'word_request_test', 'word_owner_test', 'word_owner_admission_test',
        'scalar_text_interface_test', 'scalar_text_owner_test',
        'request_evidence_test', 'obligation_evidence_test', 'evidence_effect_test', 'evidence_oracle_test']]
files = [Path(__file__), override, *tests]
if phase == 'identities': files += sorted((P / 'src').rglob('*.bl'))
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in files:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
                         'base_native_qualification_sha256': sha(B / 'qualification.json'),
                         'base_projected_modules': projection, 'original_evidence_source_sha256': sha(original),
                         'exact_local_reuse_only': True, 'in_sdk': False, 'sdk_produced': False})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
root = Path(tempfile.mkdtemp(prefix='formal-wide-reference-reuse-'))
cwd, xdg, imports, checks = (root / name for name in ('consumer', 'xdg', 'imports', 'checks'))
cwd.mkdir(); xdg.mkdir(mode=0o700); imports.mkdir(); checks.mkdir()
for row in projection:
    target = imports / Path(row['saved']).relative_to('projected/imports')
    target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(B / row['saved'], target)
projections = []
def project(source, destination, namespace=None):
    content, changes = source.read_text(), []
    for old, new in sorted(modules.items(), key=lambda item: -len(item[0])):
        for pattern in [r'(\(ns\s+)' + re.escape(old) + r'(?=\s|\))', r'(\[)' + re.escape(old) + r'(?=\s|\])']:
            selected = namespace if namespace and pattern.startswith(r'(\(ns') else new
            content, count = re.subn(pattern, lambda match: match.group(1) + selected, content)
            if count: changes.append({'pattern': pattern, 'namespace': selected, 'count': count})
    content = re.sub(r'\[formal\.wide-batch\.oracle\s*\]', '[formal.wide-batch.oracle :as oracle]', content)
    destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(content)
    saved = E / 'projected' / destination.relative_to(root)
    saved.parent.mkdir(parents=True, exist_ok=True); saved.write_text(content)
    projections.append({'source': str(source), 'source_sha256': sha(source), 'changes': changes,
                        'saved': str(saved.relative_to(E)), 'projected_sha256': sha(saved)})
project(override, imports / 'formal/wide-batch/request-evidence.bl')
if phase == 'identities':
    project(original, imports / 'formal/reference-baseline/request-evidence.bl', 'formal.reference-baseline.request-evidence')
for path in tests: project(path, checks / path.name)
write('projection.json', projections)
for descriptor in read(B / 'observations.json')['packets']:
    assert sha(B / 'packets' / descriptor['file']) == descriptor['sha256']
command = ['timeout', '--kill-after=15', '3600', 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', 'XDG_RUNTIME_DIR=' + str(xdg),
           'BL_TEST_TIMEOUT=1200', 'FORMAL_REFERENCE_REUSE_INPUT=' + str(B / 'observations.json'),
           'FORMAL_REFERENCE_REUSE_PACKETS=' + str(B / 'packets'),
           'FORMAL_REFERENCE_REUSE_OUTPUT=' + str(E / 'reference-observations.json'),
           'FORMAL_WIDE_OWNER_OUTPUT=' + str(E / 'pure-observations.json'),
           pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports)]
if phase == 'identities': command += ['-p', str(P / 'src')]
command += ['test', *[str(checks / path.name) for path in tests]]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
finally: shutil.rmtree(root)
log = (E / 'checks.txt').read_text()
green = f'{len(tests)} file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json', {'exit_code': code, 'complete_green_summary': green,
                    'elapsed_seconds': time.monotonic() - started, 'private_runtime_retired': not root.exists()})
assert code == 0 and green, log[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
counts = re.findall(r'✓\s+(formal\.[^\s]+)\s+(\d+) passed', log)
assert len(counts) == len(tests) and sum(int(count) for _, count in counts) >= (450 if phase == 'identities' else 500)
if phase == 'identities':
    observed = read(E / 'reference-observations.json')
    assert observed['sdk'] == pin['sdk'] and len(observed['entered-tests']) == 3 and len(observed['observations']) == 31
    assert observed['reference-format-changed'] is False
    assert all(row['entire-result-identical'] is True and row['before']['graph-of-calls'] == row['after']['graph-of-calls'] + 1
               for row in observed['observations'])
    pure = read(E / 'pure-observations.json')
    assert len(pure['entered-tests']) == 7 and pure['native-exchanges'] == pure['oracle-calls'] == 0
    assert all(type(row['native-exchanges']) is int and row['native-exchanges'] == 0 for row in pure['native-windows'])
write('qualification.json', {'schema': 'bl.wide-evidence-reference-reuse.v1', 'status': 'passed', 'phase': phase,
                            'recorded_utc': datetime.now(timezone.utc).isoformat(), 'source_pin': read(E / 'source-pin.json'),
                            'sdk_pin': pin, 'assertions': sum(int(count) for _, count in counts), 'files': len(tests),
                            'in_sdk': False, 'sdk_produced': False, 'reference_format_changed': False,
                            'scope': 'One exact full-data reference is computed once and reused locally. '
                                     'Identities compares full old/new checking results on 20 native packets, nine proof/premise/policy cases '
                                     'and two legacy/limited reads, alongside all 187 pure question vocabularies. '
                                     'Narrow is the separate unchanged twelve-file request/owner/effect regression stage. '
                                     'This receipt records only its named phase. Immutable SDK qualification remains separate.'})
print(json.dumps({'status': 'passed', 'phase': phase, 'assertions': sum(int(count) for _, count in counts)}))
