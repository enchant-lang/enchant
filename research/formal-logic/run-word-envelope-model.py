"""Check mathematical word envelopes; no implementation or runtime-cost proof is claimed."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/word-envelope-model'
E.mkdir(exist_ok=True)

def read(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n')

tool = read(P / 'metatheory/tool-pin.json')
lean = Path(tool['path']) / 'bin/lean'
assert sha(lean) == tool['binary_sha256']
assert subprocess.check_output(['nix', 'hash', 'path', tool['path']], text=True).strip() == tool['narHash']
sources = [P / 'metatheory/WordEnvelope.lean', P / 'metatheory/WordEnvelopeDependencies.lean', *sorted((P / 'metatheory/word-envelope-controls').glob('*.lean'))]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for path in [*sources, Path(__file__), P / 'metatheory/tool-pin.json']:
    name = str(path.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == path.read_bytes()
    if path.suffix == '.lean':
        assert not re.search(r'\b(sorry|axiom|native_decide)\b', path.read_text())
    digests[name] = sha(path)
write('source-pin.json', {'code_commit': commit, 'source_sha256': digests})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
expected = {'FormalWordEnvelope.' + name: set() for name in
            ['capacity_positive', 'wrapped_value_bound', 'addition_temporary_bound',
             'multiplication_temporary_bound', 'zero_width_refused', 'wrapped_result_does_not_bound_temporary']}
expected['FormalWordEnvelope.multiplication_temporary_bound'] = {'propext'}
dependencies = {name: set() for name in ['FormalWordEnvelope.capacity', 'FormalWordEnvelope.wrap',
                'FormalWordEnvelope.admittedWidth', 'Nat.pow_add', 'Nat.mul_le_mul_left',
                'Nat.mul_lt_mul_of_pos_right', 'Nat.lt_of_le_of_lt', 'Nat.mod_lt', 'Nat.two_pow_pos']}
dependencies['Nat.pow_add'] = {'propext'}
checks = []
for index, source in enumerate(sources):
    output = E / (source.stem + '.olean')
    output.unlink(missing_ok=True)
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=2G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=300', '--property=KillMode=control-group', '--setenv=LEAN_PATH=' + str(E),
               str(lean), '--root=' + str(source.parent), '-o', str(output), str(source)]
    write(source.stem + '-command.json', command)
    log = E / (source.stem + '-checks.txt')
    started = time.monotonic()
    with log.open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(source.stem + '-exit.json', {'exit_code': code, 'olean_present': output.exists(),
                                       'elapsed_seconds': time.monotonic() - started})
    text = log.read_text()
    audits = []
    dependency_audit = source.stem == 'WordEnvelopeDependencies'
    accepted = index == 0 or dependency_audit
    if accepted:
        assert code == 0 and output.exists() and 'error:' not in text, text[-4000:]
        reports = re.findall(r"'([^']+)' (?:depends on axioms: \[([^]]*)\]|does not depend on any axioms)", text)
        ledger = dependencies if dependency_audit else expected
        assert len(reports) == len(ledger) and {name for name, _ in reports} == set(ledger), reports
        for name, raw in reports:
            axioms = re.findall(r'[\w.]+', raw)
            assert set(axioms) == ledger[name], (name, axioms)
            audits.append({'theorem': name, 'axioms': axioms})
    else:
        assert code != 0 and not output.exists() and text.count('error:') == 1
        assert 'decide' in text and 'false' in text, text[-2000:]
    checks.append({'source': str(source.relative_to(R)), 'source_sha256': sha(source), 'accepted': accepted,
                   'dependency_audit': dependency_audit, 'exit_code': code, 'log_sha256': sha(log), 'olean_sha256': sha(output) if output.exists() else None,
                   'axiom_audits': audits})
    print(json.dumps({'stage': source.stem, 'status': 'accepted' if accepted else 'refused-as-required'}), flush=True)
assert all(sha(R / name) == digest for name, digest in digests.items())
write('qualification.json', {'schema': 'bl.word-envelope-model-qualification.v1', 'status': 'passed',
      'recorded_utc': datetime.now(timezone.utc).isoformat(), 'tool_pin': tool, 'source_pin': read(E / 'source-pin.json'),
      'checks': checks, 'theorems': 6, 'dependency_audits': 9, 'false_claim_controls': 2,
      'declared_axiom_ledger': {name: sorted(values) for name, values in expected.items()},
      'declared_dependency_ledger': {name: sorted(values) for name, values in dependencies.items()},
      'compiler_proof_authority': False,
      'scope': 'Mathematical modular result and intermediate arithmetic magnitude bounds, plus explicit positive-width admission. No BL bit-vector implementation, allocation/work-cost, compiler or native solver correspondence theorem.'})
print(json.dumps({'status': 'passed', 'theorems': 6, 'false_claim_controls': 2}))
