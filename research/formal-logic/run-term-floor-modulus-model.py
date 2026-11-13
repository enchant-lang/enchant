"""Check the arithmetic-to-typed-term connection, reusing pinned parent models."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/term-floor-modulus-model'
E.mkdir(exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

tool = read(P / 'metatheory/tool-pin.json')
floor = read(P / 'evidence/floor-modulus-model/qualification.json')
assert floor['status'] == 'passed' and floor['tool_pin'] == tool
lean = Path(tool['path']) / 'bin/lean'
assert sha(lean) == tool['binary_sha256']
assert subprocess.check_output(['nix', 'hash', 'path', tool['path']], text=True).strip() == tool['narHash']
parents = {}
for name in ('terms', 'refutation'):
    pin_path = P / ('metatheory/' + name + '-pin.json')
    pin = read(pin_path)
    for part in ('source', 'compiled'):
        assert sha(P / pin[part]['path']) == pin[part]['sha256']
    parents[name] = {'pin': pin, 'pin_sha256': sha(pin_path)}
floor_check = floor['checks'][0]
assert sha(R / floor_check['source']) == floor_check['source_sha256']
assert sha(P / 'evidence/floor-modulus-model/FloorModulus.olean') == floor_check['olean_sha256']
parents['floor'] = {'qualification_sha256': sha(P / 'evidence/floor-modulus-model/qualification.json'),
                    'source_sha256': floor_check['source_sha256'], 'olean_sha256': floor_check['olean_sha256']}
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [P / 'metatheory/TermFloorModulus.lean', P / 'metatheory/TermFloorModulusDependencies.lean',
           *sorted((P / 'metatheory/term-floor-modulus-controls').glob('*.lean'))]
inputs = [*sources, Path(__file__), P / 'metatheory/tool-pin.json',
          P / 'metatheory/terms-pin.json', P / 'metatheory/refutation-pin.json']
digests = {}
for path in inputs:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    if path.suffix == '.lean':
        assert not re.search(r'\b(sorry|axiom|native_decide)\b', path.read_text())
    digests[name] = sha(path)
write(E / 'source-pin.json', {'code_commit': commit, 'source_sha256': digests, 'parents': parents})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
expected = {
    'known_value': {'propext'},
    'known_floor_value': {'propext', 'Classical.choice', 'Quot.sound'},
    'zero_failure': {'propext'},
    'missing_left': {'propext'},
    'missing_right': {'propext'},
    # Reflexivity still inherits the named partial evaluator's propext.
    'negative_divisor_example': {'propext'},
}
expected = {'FormalTermFloorModulus.' + name: values for name, values in expected.items()}
dependencies = {'FormalTerms.Term.eval': {'propext'},
                'FormalTermFloorModulus.floorModTerm': set(),
                'FormalTerms.modulus': set(), 'FormalRefutation.pOr': set()}
checked = []
paths = [E, P / 'evidence/term-refutation', P / 'evidence/refutation-kernel', P / 'evidence/floor-modulus-model']
for index, source in enumerate(sources):
    output = E / (source.stem + '.olean')
    output.unlink(missing_ok=True)
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=2G',
               '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=300',
               '--property=KillMode=control-group', '--setenv=LEAN_PATH=' + ':'.join(map(str, paths)),
               str(lean), '--root=' + str(source.parent), '-o', str(output), str(source)]
    write(E / (source.stem + '-command.json'), command)
    log = E / (source.stem + '-checks.txt')
    started = time.monotonic()
    with log.open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(E / (source.stem + '-exit.json'), {'exit_code': code, 'olean_present': output.exists(),
                                           'elapsed_seconds': time.monotonic() - started})
    text = log.read_text()
    audits = []
    dependency_audit = source.stem == 'TermFloorModulusDependencies'
    accepted = index == 0 or dependency_audit
    if accepted:
        assert code == 0 and output.exists() and 'error:' not in text, text[-5000:]
        reports = re.findall(r"'([^']+)' (?:depends on axioms: \[([^]]*)\]|does not depend on any axioms)", text)
        ledger = dependencies if dependency_audit else expected
        assert len(reports) == len(ledger) and {name for name, _ in reports} == set(ledger), reports
        for theorem, raw in reports:
            axioms = re.findall(r'[\w.]+', raw)
            assert set(axioms) == ledger[theorem], (theorem, axioms)
            audits.append({'theorem': theorem, 'axioms': axioms})
    else:
        assert code != 0 and not output.exists() and text.count('error:') == 1
        assert 'error: Tactic `rfl` failed' in text, text[-2500:]
    checked.append({'source': str(source.relative_to(R)), 'source_sha256': sha(source),
                    'exit_code': code, 'accepted': accepted, 'dependency_audit': dependency_audit, 'axiom_audits': audits,
                    'log_sha256': sha(log), 'olean_sha256': sha(output) if output.exists() else None})
    print(json.dumps({'stage': source.stem, 'status': 'accepted' if accepted else 'rejected-as-required'}), flush=True)
assert all(sha(R / name) == digest for name, digest in digests.items())
write(E / 'qualification.json', {
    'schema': 'bl.term-floor-modulus-model-qualification.v1', 'status': 'passed',
    'recorded_utc': datetime.now(timezone.utc).isoformat(), 'tool_pin': tool,
    'source_pin': read(E / 'source-pin.json'), 'checks': checked,
    'universal_and_example_theorems': 6, 'refusal_controls': 2,
    'definition_dependency_audits': 4,
    'declared_axiom_ledger': {name: sorted(values) for name, values in expected.items()},
    'declared_definition_dependencies': {name: sorted(values) for name, values in dependencies.items()},
    'compiler_proof_authority': False,
    'scope': 'Connection between the pinned partial typed mathematical term evaluator and the floor-modulus arithmetic model, including zero failure and missing operands. No BL decoder, graph constructor, renderer, compiler, concrete exception or native solver correspondence theorem.'})
print(json.dumps({'status': 'passed', 'theorems': 6, 'refusal_controls': 2}))
