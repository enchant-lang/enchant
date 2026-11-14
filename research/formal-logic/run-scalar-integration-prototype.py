"""Check coherent canonical sources through explicit namespace projections on the selected SDK."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
stage = sys.argv[1]
assert stage in ('pure', 'owners', 'legacy')
E = P / 'evidence/scalar-integration-prototype' / stage
E.mkdir(parents=True, exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

pin = read(P / 'sdk-pin.json')
assert read(P / 'evidence/word-integration/qualification.json')['sdk_pin'] == pin
assert read(P / 'evidence/word-integration/qualification.json')['status'] == 'passed'
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
modules = {name: 'formal.scalar-batch.' + name.split('formal.', 1)[1] for name in
           ['formal.backend', 'formal.coordinates', 'formal.evaluate', 'formal.graph-execution',
            'formal.graph-question', 'formal.graph-terms', 'formal.logic', 'formal.point-profile',
            'formal.request', 'formal.request-answer', 'formal.request-point', 'formal.request-record',
            'formal.request-runtime', 'formal.resources.word', 'formal.resources.text',
            'formal.scalar-text', 'formal.scalar-text-value', 'formal.finite-word-certificate', 'formal.request-evidence']}
modules['veritas.ledger'] = 'formal.scalar-batch.ledger'
tests = {
 'pure': ['test/bl/formal/scalar_text_graph_test.bl', 'test/bl/formal/scalar_text_resource_test.bl',
          'test/bl/formal/scalar_text_interface_test.bl', 'test/bl/formal/finite_word_certificate_test.bl',
          'test/bl/formal/request_evidence_test.bl', 'test/bl/formal/word_graph_test.bl'],
 'owners': ['test/bl/formal/scalar_text_owner_test.bl', 'test/bl/formal/evidence_effect_test.bl',
            'test/bl/formal/word_owner_test.bl', 'test/bl/formal/request_test.bl',
            'test/bl/formal/managed_graph_test.bl', 'research/formal-logic/retained-request-check.bl'],
 'legacy': ['test/bl/formal/shared_evaluator_test.bl', 'test/bl/formal/graph_admission_test.bl',
            'test/bl/formal/graph_keys_test.bl', 'test/bl/formal/graph_ops_test.bl',
            'test/bl/formal/graph_context_test.bl', 'test/bl/formal/word_request_test.bl'],
}[stage]
module_paths = {name: R / ('priv/lib/' + name.replace('.', '/') + '.bl') for name in modules}
inputs = [*module_paths.values(), *[R / name for name in tests], Path(__file__), P / 'sdk-pin.json']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in inputs:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'base_sdk_pin': pin, 'sdk_produced': False})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
runtime = Path(tempfile.mkdtemp(prefix='formal-scalar-batch-prototype-'))
imports, checks, xdg = runtime / 'imports', runtime / 'checks', runtime / 'xdg'
imports.mkdir(); checks.mkdir(); xdg.mkdir(mode=0o700)
projections = []

def project(source, destination, extra=None):
    text = source.read_text()
    changes = []
    mapping = dict(modules)
    mapping.update(extra or {})
    for old, new in sorted(mapping.items(), key=lambda pair: -len(pair[0])):
        for pattern in [r'(\(ns\s+)' + re.escape(old) + r'(?=\s|\))',
                        r'(\[)' + re.escape(old) + r'(?=\s|\])']:
            text, count = re.subn(pattern, lambda m: m.group(1) + new, text)
            if count:
                changes.append({'pattern': pattern, 'replacement_namespace': new, 'count': count})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)
    saved = E / 'projected' / destination.relative_to(runtime)
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(text)
    projections.append({'source': str(source.relative_to(R)), 'source_sha256': sha(source),
                        'transformations': changes, 'projected_sha256': sha(destination),
                        'saved': str(saved.relative_to(E))})

for name, source in module_paths.items():
    project(source, imports / (modules[name].replace('.', '/') + '.bl'))
paths = []
for name in tests:
    target = checks / Path(name).name
    project(R / name, target, {'formal.indexed-ledger-prototype': modules['veritas.ledger'],
                             'formal.indexed-request-record-prototype': modules['formal.request-record']})
    paths.append(str(target))
write('projection.json', projections)
command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
           '--unit=work-formal-scalar-integration-' + stage + '-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(runtime), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=1200', '--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(xdg),
            '--setenv=SCALAR_OWNER_OUTPUT=' + str(E / 'native.json'),
           '--setenv=TEXT_NATIVE_OUTPUT=' + str(E / 'term-native.json'),
           '--setenv=WORD_EXHAUSTION_NATIVE_OUTPUT=' + str(E / 'word-native.json'),
           '--setenv=EVIDENCE_BUNDLE_OUTPUT=' + str(E / 'bundle-corpus.json'),
           'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
           'BEAM_LISP_PATH=' + str(imports), pin['sdk'] + '/bin/bl', '--cold', '-p', str(imports), 'test', *paths]
write('command.json', command)
(E / 'qualification.json').unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as log:
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
log = (E / 'checks.txt').read_text()
green = f'{len(tests)} file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json', {'process_exit_code': code, 'complete_green_test_summary': green,
      'elapsed_seconds': time.monotonic() - started, 'runtime_retired': not runtime.exists()})
assert code == 0 and green, log[-7000:]
assert all(sha(R / name) == digest for name, digest in digests.items())
assert all(sha(E / row['saved']) == row['projected_sha256'] for row in projections)
counts = {name: int(total) for name, total in re.findall(r'✓\s+([\w.-]+)\s+(\d+) passed', log)}
assert len(counts) == len(tests)
write('qualification.json', {'schema': 'bl.scalar-integration-prototype.v1', 'status': 'passed', 'stage': stage,
      'recorded_utc': datetime.now(timezone.utc).isoformat(), 'base_sdk_pin': pin,
      'source_pin': read(E / 'source-pin.json'), 'projections': projections, 'assertion_runs': counts,
      'assertions': sum(counts.values()), 'log_sha256': sha(E / 'checks.txt'), 'exit': read(E / 'exit.json'),
      'sdk_produced': False, 'compiler_proof_authority': False,
      'scope': 'Explicit namespace/import projections of coherent canonical runtime sources beside the selected SDK. No production artifact, native-history authentication or compiler preservation proof is established.'})
print(json.dumps({'status': 'passed', 'stage': stage, 'assertions': sum(counts.values()), 'sdk_produced': False}))
