"""Check universal modulus mathematics; no BL/solver correspondence is claimed."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/floor-modulus-model'
E.mkdir(exist_ok=True)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


tool = read(P / 'evidence/graph-selection-model/qualification.json')['tool_pin']
lean = Path(tool['path']) / 'bin/lean'
assert sha(lean) == tool['binary_sha256']
assert subprocess.check_output(['nix', 'hash', 'path', tool['path']], text=True).strip() == tool['narHash']
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [P / 'metatheory/FloorModulus.lean',
           *sorted((P / 'metatheory/floor-modulus-controls').glob('*.lean')),
           P / 'metatheory/FloorModulusDependencies.lean', Path(__file__)]
digests = {}
for path in sources:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    if path.suffix == '.lean':
        assert not re.search(r'\b(sorry|axiom|native_decide)\b', path.read_text())
    digests[name] = sha(path)
write(E / 'source-pin.json', {'code_commit': commit, 'source_sha256': digests})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
checked = []
standard = {'propext', 'Classical.choice', 'Quot.sound'}
# Exact reviewed footprints, not a blanket admission of every standard axiom.
# The floor equivalences and their corollaries use imported Std integer laws;
# the separately printed dependency audit identifies that library boundary.
choice = {'propext', 'Classical.choice', 'Quot.sound'}
constructive = {'propext', 'Quot.sound'}
expected_ledger = {
    'FormalFloorModulus.repaired_mod_eq_floor': choice,
    'FormalFloorModulus.repaired_quot_eq_floor': choice,
    'FormalFloorModulus.reconstruction': choice,
    'FormalFloorModulus.positive_bounds': constructive,
    'FormalFloorModulus.negative_bounds': constructive,
    'FormalFloorModulus.congruence': choice,
    'FormalFloorModulus.zero_is_failure': {'propext'},
    'FormalFloorModulus.successful_outcome': choice,
    'FormalFloorModulus.defined_iff_nonzero': {'propext'},
    'FormalFloorModulus.negative_divisor_counterexample': set(),
}
for index, source in enumerate(sources[:-1]):
    output = E / (source.stem + '.olean')
    output.unlink(missing_ok=True)
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=2G',
               '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=300',
               '--property=KillMode=control-group', '--setenv=LEAN_PATH=' + str(E),
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
    dependency_audit = source.stem == 'FloorModulusDependencies'
    accepted = index == 0 or dependency_audit
    if accepted:
        assert code == 0 and output.exists() and 'error:' not in text, text[-4000:]
        reports = re.findall(r"'([^']+)' (?:depends on axioms: \[([^]]*)\]|does not depend on any axioms)", text)
        assert len(reports) == (8 if dependency_audit else 10), reports
        if not dependency_audit:
            assert {theorem for theorem, _ in reports} == set(expected_ledger)
        for theorem, raw in reports:
            assumptions = re.findall(r'[\w.]+', raw)
            if dependency_audit:
                assert set(assumptions) <= standard, (theorem, assumptions)
            else:
                assert set(assumptions) == expected_ledger[theorem], (theorem, assumptions)
            audits.append({'theorem': theorem, 'axioms': assumptions})
    else:
        assert code != 0 and not output.exists() and text.count('error:') == 1
        assert 'error: Tactic `rfl` failed' in text, text[-2500:]
    checked.append({'source': str(source.relative_to(R)), 'source_sha256': sha(source),
                    'exit_code': code, 'accepted': accepted, 'dependency_audit': dependency_audit, 'axiom_audits': audits,
                    'log_sha256': sha(log), 'olean_sha256': sha(output) if output.exists() else None})
    print(json.dumps({'stage': source.stem, 'status': 'accepted' if accepted else 'rejected-as-required'}), flush=True)
assert all(sha(R / name) == digest for name, digest in digests.items())
report = {'schema': 'bl.floor-modulus-model-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'tool_pin': tool,
          'source_pin': read(E / 'source-pin.json'), 'checks': checked,
          'universal_and_example_theorems': 10, 'refusal_controls': 2,
          'standard_library_dependency_audits': 8,
          'declared_axiom_ledger': {name: sorted(axioms) for name, axioms in expected_ledger.items()},
          'compiler_proof_authority': False,
          'scope': 'Universal integer floor-modulus and quotient correction, reconstruction, sign/range, congruence and explicit zero failure in a separate Lean model. No execution or preservation theorem for BL, its compiler/renderer, Z3 or OxiZ.'}
write(E / 'qualification.json', report)
print(json.dumps({'status': 'passed', 'theorems': 10, 'refusal_controls': 2, 'compiler_proof_authority': False}))
