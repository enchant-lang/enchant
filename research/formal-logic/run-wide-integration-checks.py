"""One serial gate on the exact built wide SDK; the project pin stays qualified."""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys, tempfile, time

P = Path(__file__).resolve().parent
R = P.parent.parent
B = P / 'evidence/wide-integration'
phase, = sys.argv[1:]
assert phase in ('preflight', 'pure', 'narrow', 'compatibility', 'legacy', 'regression', 'native', 'reader-one', 'reader-two',
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
test_phases = ('pure', 'narrow', 'compatibility', 'legacy', 'regression', 'native')
expected_counts = None
if phase == 'pure':
    files = [P / 'prototypes/wide-owner/wide-owner-pure-check.bl']; project = True
elif phase == 'narrow':
    files = [R / 'test/bl/formal' / (name + '.bl') for name in [
        'managed_graph_test', 'retained_configuration_test', 'request_test',
        'word_request_test', 'word_owner_test', 'word_owner_admission_test',
        'scalar_text_interface_test', 'scalar_text_owner_test',
        'request_evidence_test', 'obligation_evidence_test', 'evidence_effect_test', 'evidence_oracle_test']]
    ceiling = 3600
elif phase == 'compatibility':
    # Complete the preceding 59-file qualification without repeating the
    # twelve narrow files. Keep the exact old test bodies and expected counts.
    files = [R / 'test/bl/formal' / (name + '.bl') for name in [
        'graph_integer_certificate_test', 'finite_feasibility_test',
        'scalar_text_graph_test', 'scalar_text_resource_test', 'finite_word_certificate_test',
        'word_graph_test', 'request_lookup_test']]
    files += [P / (name + '.bl') for name in ['retained-question-check',
        'retained-composition-check', 'retained-answer-check', 'retained-request-check']]
    ceiling = 3600
elif phase == 'legacy':
    files = [R / 'test/bl/formal' / (name + '.bl') for name in [
        'shared_evaluator_test', 'graph_admission_test', 'graph_keys_test',
        'graph_ops_test', 'graph_context_test']]
    ceiling = 3600
elif phase == 'regression':
    old = read(P / 'evidence/numeric-semantics/regression-command.json')
    files = [R / name for name in old[old.index('test') + 1:]]
    assert len(files) == 31
    project = True; ceiling = 3600
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
                         'in-sdk': True, 'compiler-proof-authority': False, 'packets': producer['packets']})
elif phase != 'preflight':
    files = [P / {'word-packets': 'word-packet-reader.bl', 'text-packets': 'scalar-packet-reader.bl',
                  'proof-packets': 'evidence-packet-reader.bl', 'obligation-packets': 'obligation-packet-reader.bl'}[phase]]
if phase in ('compatibility', 'legacy', 'regression'):
    parent = read(P / 'evidence/obligation-integration/qualification.json')
    assert parent['status'] == 'passed' and parent['sdk_pin'] == baseline
    prior = {name: count for rows in parent['assertion_runs'].values() for name, count in rows.items()}
    namespaces = [re.search(r'\(ns\s+([^\s)]+)', path.read_text()).group(1) for path in files]
    assert len(set(namespaces)) == len(files)
    expected_counts = {namespace: prior[namespace] for namespace in namespaces}
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
inputs = [Path(__file__), *files, R / 'scripts/sdk-preflight', R / 'scripts/sdk-preflight.bl']
if expected_counts is not None:
    inputs += [P / 'evidence/obligation-integration/qualification.json']
if phase == 'regression': inputs += [P / 'evidence/numeric-semantics/regression-command.json']
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
    if phase in test_phases:
        selected_files = files
        if phase in ('pure', 'native'):
            # The same assertion body now calls installed SDK namespaces.
            # Correct only the writer's former project-provenance label.
            content = files[0].read_text()
            assert content.count(':in-sdk false') == 1
            content = content.replace(':in-sdk false', ':in-sdk true')
            adapted = root / files[0].name; adapted.write_text(content)
            (E / ('canonical-' + files[0].name)).write_text(content)
            write('sdk-test-adaptation.json', {'source_sha256': sha(files[0]), 'adapted_sha256': sha(adapted),
                                              'scope': 'Runtime provenance flag only; unchanged assertions, profile values and imports.'})
            selected_files = [adapted]
        request += ['test', *map(str, selected_files)]
        environment += ['FORMAL_WIDE_OWNER_OUTPUT=' + str(E / 'observations.json')]
        if phase == 'native':
            environment += ['BL_TEST_TIMEOUT=21540', 'FORMAL_WIDE_OWNER_SAMPLE=all',
                'FORMAL_WIDE_OWNER_BASELINE=' + str(P / 'evidence/obligation-integration/native.json'),
                'FORMAL_WIDE_OWNER_PACKETS=' + str(E / 'packets')]
    elif phase.startswith('reader-'):
        # Only import names change. The check body runs against installed SDK
        # namespaces with no prototype or application imports.
        content = files[0].read_text().replace('[formal.wide-batch.oracle', '[oracle').replace('[formal.wide-batch.', '[formal.')
        old_scope = '(= false (get input "in-sdk") (get input "compiler-proof-authority"))'
        assert content.count(old_scope) == 1 and content.count(':in-sdk false') == 1
        content = content.replace(old_scope, '(and (= true (get input "in-sdk")) (= false (get input "compiler-proof-authority")))')
        content = content.replace(':in-sdk false', ':in-sdk true').replace('"explicit prototype scope"', '"explicit SDK scope"')
        adapted = root / 'candidate-reader.bl'; adapted.write_text(content)
        (E / 'canonical-candidate-reader.bl').write_text(content)
        write('reader-adaptation.json', {'source_sha256': sha(files[0]), 'adapted_sha256': sha(adapted),
                                         'scope': 'Require namespace spelling and actual runtime provenance labels only. '
                                                  'Mathematical/refusal assertions and profile values stay unchanged.'})
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
tests = phase in test_phases
green = (f'{len(files)} file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log) if tests else None
write('exit.json', {'exit_code': code, 'complete_green_summary': green,
                    'elapsed_seconds': time.monotonic() - started, 'private_runtime_retired': not root.exists()})
assert code == 0 and (not tests or green), log[-6000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
details = {}
if tests:
    counts = re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)
    assert len(counts) == len(files)
    details['assertions'] = sum(int(count) for _, count in counts)
    if expected_counts is not None:
        assert {name: int(count) for name, count in counts} == expected_counts
        details['unchanged_assertion_counts'] = expected_counts
    else: assert details['assertions'] >= {'pure': 424, 'narrow': 745, 'native': 5000}[phase]
if phase == 'pure':
    v = read(E / 'observations.json')
    assert v['sdk'] == pin['sdk'] and v['in-sdk'] is True and len(v['entered-tests']) == 7
    assert type(v['native-exchanges']) is int and v['native-exchanges'] == v['oracle-calls'] == 0
elif phase == 'native':
    v = read(E / 'observations.json')
    assert v['sdk'] == pin['sdk'] and v['in-sdk'] is True and len(v['rows']) == 187 and len(v['packets']) == 376
    assert len(v['entered-tests']) == 4
    for packet in v['packets']: assert sha(E / 'packets' / packet['file']) == packet['sha256']
    differences = [dict(id=row['id'], **outcome) for row in v['rows'] for outcome in row['outcomes'] if outcome['status-changed']]
    write('native-status-differences.json', differences)
    details.update(questions=187, candidate_packets=376, raw_status_differences=len(differences), observations_sha256=sha(E / 'observations.json'))
elif phase.startswith('reader-'):
    v = read(E / 'observations.json')
    assert v['status'] == 'passed' and v['sdk'] == pin['sdk'] and v['in-sdk'] is True and v['packets'] == len(v['rows']) == 376
    assert type(v['native-exchanges']) is int and v['native-exchanges'] == v['oracle-calls'] == 0
    assert v['negative-controls'] == 8 and v['manual-schema-preload'] is False and v['warmed-atoms-stable'] is True
    details.update(packets=376, native_exchanges=0, oracle_calls=0, checks=v['checks'])
elif phase.endswith('-packets'):
    v = read(E / 'observations.json')
    if phase == 'word-packets':
        # This older twelve-record program did not instrument transport.
        # Record only the checks it actually makes; do not invent zero counts.
        assert v['records'] == 12 and v['manual-schema-preload'] is False
        assert v['compiler-proof-authority'] is False
        details.update(records=12, native_exchange_measurement='not-installed-in-this-historical-reader')
    else:
        assert type(v['native-exchanges']) is int and v['native-exchanges'] == v['oracle-calls'] == 0
        assert v['sdk'] == pin['sdk']
write('qualification.json', {'schema': 'bl.wide-integration-gate.v1', 'status': 'passed', 'phase': phase,
                            'sdk_pin': pin, 'source_pin': read(E / 'source-pin.json'), **details,
                            'scope': 'One named gate on the immutable candidate. Project selection and whole SDK qualification remain separate.',
                            'compiler_proof_authority': False})
print(json.dumps({'status': 'passed', 'phase': phase, **details}))
