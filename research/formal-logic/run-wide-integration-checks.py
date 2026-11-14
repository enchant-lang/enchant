"""One serial gate on the exact built wide SDK; the project pin stays qualified."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys, tempfile, time

P = Path(__file__).resolve().parent
R = P.parent.parent
B = P / 'evidence/wide-integration'
phase, = sys.argv[1:]
assert phase in ('preflight', 'pure', 'narrow', 'native', 'reader-one', 'reader-two',
                 'word-packets', 'text-packets', 'proof-packets', 'obligation-packets')
E = B / phase
E.mkdir(exist_ok=True)
assert all(path.is_dir() and path.name.startswith('before-') for path in E.iterdir()), 'Retain an earlier gate before retrying.'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
pin, baseline, linkage = read(B / 'sdk-candidate.json'), read(B / 'baseline-sdk-pin.json'), read(B / 'build-linkage.json')
assert read(P / 'sdk-pin.json') == baseline
assert linkage['status'] == 'bound' and linkage['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
for name, row in linkage['source_changes'].items():
    assert sha(R / name) == row['after'] == sha(Path(pin['source']) / name)
files, project, ceiling = [], False, 1800
if phase == 'pure':
    files = [P / 'prototypes/wide-owner/wide-owner-pure-check.bl']; project = True
elif phase == 'narrow':
    files = [R / 'test/bl/formal' / (name + '.bl') for name in [
        'managed_graph_test', 'retained_configuration_test', 'request_test',
        'word_request_test', 'word_owner_test', 'word_owner_admission_test',
        'scalar_text_interface_test', 'scalar_text_owner_test',
        'request_evidence_test', 'obligation_evidence_test', 'evidence_effect_test', 'evidence_oracle_test']]
    ceiling = 3600
elif phase == 'native':
    files = [P / 'prototypes/wide-owner/wide-owner-native-check.bl']; project = True; ceiling = 21600
    assert read(B / 'pure/qualification.json')['status'] == read(B / 'narrow/qualification.json')['status'] == 'passed'
    (E / 'packets').mkdir()
elif phase.startswith('reader-'):
    files = [P / 'prototypes/wide-readers/candidate-reader.bl']; ceiling = 7200
    native = read(B / 'native/qualification.json')
    assert native['status'] == 'passed' and native['questions'] == 187 and native['candidate_packets'] == 376
    producer = read(B / 'native/observations.json')
    assert native['observations_sha256'] == sha(B / 'native/observations.json')
    for packet in producer['packets']:
        assert re.fullmatch(r'\d+-(z3|oxiz)\.json', packet['file'])
        assert sha(B / 'native/packets' / packet['file']) == packet['sha256']
    write('corpus.json', {'schema': 'bl.wide-owner-candidate-corpus.v1', 'producer-results': False,
                         'in-sdk': False, 'compiler-proof-authority': False, 'packets': producer['packets']})
elif phase != 'preflight':
    files = [P / {'word-packets': 'word-packet-reader.bl', 'text-packets': 'scalar-packet-reader.bl',
                  'proof-packets': 'evidence-packet-reader.bl', 'obligation-packets': 'obligation-packet-reader.bl'}[phase]]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
inputs = [Path(__file__), *files, R / 'scripts/sdk-preflight', R / 'scripts/sdk-preflight.bl']
if project: inputs += sorted((P / 'src').rglob('*.bl'))
digests = {}
for path in inputs:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
                         'qualified_baseline': baseline, 'build_linkage_sha256': sha(B / 'build-linkage.json'),
                         'project_source_imports': project})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
root = Path(tempfile.mkdtemp(prefix='formal-wide-sdk-gate-'))
cwd, xdg = root / 'consumer', root / 'xdg'
cwd.mkdir(); xdg.mkdir(mode=0o700)
environment = ['XDG_RUNTIME_DIR=' + str(xdg), 'BL_TEST_TIMEOUT=1200']
if phase == 'preflight':
    request = [sys.executable, str(R / 'scripts/sdk-preflight'), '--sdk', pin['sdk'],
               '--root', pin['source'], '--out', str(E / 'observations.json')]
else:
    request = [pin['sdk'] + '/bin/bl', '--cold']
    if project: request += ['-p', str(P / 'src')]
    if phase in ('pure', 'narrow', 'native'):
        request += ['test', *map(str, files)]
        environment += ['FORMAL_WIDE_OWNER_OUTPUT=' + str(E / 'observations.json')]
        if phase == 'native':
            environment += ['BL_TEST_TIMEOUT=21540', 'FORMAL_WIDE_OWNER_SAMPLE=all',
                'FORMAL_WIDE_OWNER_BASELINE=' + str(P / 'evidence/obligation-integration/native.json'),
                'FORMAL_WIDE_OWNER_PACKETS=' + str(E / 'packets')]
    elif phase.startswith('reader-'):
        # Only import names change. The check body runs against installed SDK
        # namespaces with no prototype or application imports.
        content = files[0].read_text().replace('[formal.wide-batch.oracle', '[oracle').replace('[formal.wide-batch.', '[formal.')
        adapted = root / 'candidate-reader.bl'; adapted.write_text(content)
        (E / 'canonical-candidate-reader.bl').write_text(content)
        write('reader-adaptation.json', {'source_sha256': sha(files[0]), 'adapted_sha256': sha(adapted),
                                         'scope': 'Require namespace spelling only; no test body or profile values change.'})
        request += ['run', str(adapted), '--', str(E / 'corpus.json'),
                    str(B / 'native/packets'), str(E / 'observations.json')]
    else:
        corpus = {'word-packets': P / 'evidence/retained-request/corpus.json',
                  'text-packets': P / 'evidence/obligation-integration/text-native.json',
                  'proof-packets': P / 'evidence/obligation-integration/bundle-corpus.json',
                  'obligation-packets': P / 'evidence/obligation-integration/obligation-corpus.json'}[phase]
        write('historical-input.json', {'path': str(corpus), 'sha256': sha(corpus), 'producer_identity': 'retained historical data'})
        request += ['run', str(files[0]), '--', str(corpus), str(E / 'observations.json')]
command = ['timeout', '--kill-after=15', str(ceiling), 'env', '-u', 'BEAM_LISP_PATH',
           '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', *environment, *request]
write('command.json', command)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT).returncode
finally: shutil.rmtree(root)
log = (E / 'checks.txt').read_text()
tests = phase in ('pure', 'narrow', 'native')
green = (f'{len(files)} file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log) if tests else None
write('exit.json', {'exit_code': code, 'complete_green_summary': green,
                    'elapsed_seconds': time.monotonic() - started, 'private_runtime_retired': not root.exists()})
assert code == 0 and (not tests or green), log[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
details = {}
if tests:
    counts = re.findall(r'✓\s+(formal\.[^\s]+)\s+(\d+) passed', log)
    assert len(counts) == len(files)
    details['assertions'] = sum(int(count) for _, count in counts)
    assert details['assertions'] >= {'pure': 424, 'narrow': 745, 'native': 5000}[phase]
if phase == 'pure':
    v = read(E / 'observations.json')
    assert v['sdk'] == pin['sdk'] and len(v['entered-tests']) == 7
    assert type(v['native-exchanges']) is int and v['native-exchanges'] == v['oracle-calls'] == 0
elif phase == 'native':
    v = read(E / 'observations.json')
    assert v['sdk'] == pin['sdk'] and len(v['rows']) == 187 and len(v['packets']) == 376
    assert len(v['entered-tests']) == 4
    for packet in v['packets']: assert sha(E / 'packets' / packet['file']) == packet['sha256']
    differences = [dict(id=row['id'], **outcome) for row in v['rows'] for outcome in row['outcomes'] if outcome['status-changed']]
    write('native-status-differences.json', differences)
    details.update(questions=187, candidate_packets=376, raw_status_differences=len(differences), observations_sha256=sha(E / 'observations.json'))
elif phase.startswith('reader-'):
    v = read(E / 'observations.json')
    assert v['status'] == 'passed' and v['sdk'] == pin['sdk'] and v['packets'] == len(v['rows']) == 376
    assert type(v['native-exchanges']) is int and v['native-exchanges'] == v['oracle-calls'] == 0
    assert v['negative-controls'] == 8 and v['manual-schema-preload'] is False and v['warmed-atoms-stable'] is True
    details.update(packets=376, native_exchanges=0, oracle_calls=0, checks=v['checks'])
elif phase.endswith('-packets'):
    v = read(E / 'observations.json')
    assert type(v['native-exchanges']) is int and v['native-exchanges'] == v['oracle-calls'] == 0
    assert v['sdk'] == pin['sdk']
write('qualification.json', {'schema': 'bl.wide-integration-gate.v1', 'status': 'passed', 'phase': phase,
                            'sdk_pin': pin, 'source_pin': read(E / 'source-pin.json'), **details,
                            'scope': 'One named gate on the immutable candidate. Project selection and whole SDK qualification remain separate.',
                            'compiler_proof_authority': False})
print(json.dumps({'status': 'passed', 'phase': phase, **details}))
