"""One immutable SDK candidate for actual owner graph execution."""
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-graph'
E.mkdir(exist_ok=True)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
names = ['priv/lib/formal/evaluate.bl', 'priv/lib/formal/backend.bl',
         'priv/lib/formal/graph-question.bl', 'priv/lib/formal/graph-execution.bl',
         'test/bl/formal/shared_evaluator_test.bl', 'test/bl/formal/graph_admission_test.bl',
         'test/bl/formal/managed_graph_test.bl', str(Path(__file__).relative_to(R))]
digests = {}
for name in names:
    body = (R / name).read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    digests[name] = hashlib.sha256(body).hexdigest()
fingerprint = subprocess.check_output(['scripts/prepare-checkout-sdk', '--fingerprint'], cwd=R, text=True).strip()
(E / 'sdk-source-pin.json').write_text(json.dumps({'code_commit': commit, 'engine_fingerprint': fingerprint,
                                                'source_sha256': digests}, indent=2) + '\n')
(E / 'baseline-sdk-pin.json').write_bytes((P / 'sdk-pin.json').read_bytes())
(E / 'sdk-build-memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
command = ['scripts/prepare-checkout-sdk']
(E / 'sdk-build-command.json').write_text(json.dumps(command, indent=2) + '\n')
(E / 'sdk-build-exit.json').unlink(missing_ok=True)
with (E / 'sdk-build.txt').open('w') as stream:
    code = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
(E / 'sdk-build-exit.json').write_text(json.dumps({'exit_code': code}) + '\n')
if code:
    raise SystemExit(code)
assert fingerprint == subprocess.check_output(['scripts/prepare-checkout-sdk', '--fingerprint'], cwd=R, text=True).strip()
sdk = (R / '.bl/sdks' / fingerprint / 'result-sdk').resolve(strict=True)
source = (R / '.bl/sdks' / fingerprint / 'source-engine').resolve(strict=True)
assert str(sdk).startswith('/nix/store/') and str(source).startswith('/nix/store/')
for name in names[:4]:
    assert hashlib.sha256((source / name).read_bytes()).hexdigest() == digests[name]
candidate = {'sdk': str(sdk), 'descriptor_sha256': hashlib.sha256((sdk / 'artifact.json').read_bytes()).hexdigest(),
             'source': str(source), 'base_commit': commit, 'engine_fingerprint': fingerprint}
(E / 'sdk-candidate.json').write_text(json.dumps(candidate, indent=2) + '\n')
print(json.dumps({'status': 'candidate-built', 'sdk': str(sdk), 'project_pin_changed': False}))
