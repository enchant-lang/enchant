"""Qualify selective structural interpretation, independently of the BL runtime."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/graph-selection-model'
BASE = P / 'evidence/graph-table-model'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


base = read(P / 'metatheory/graph-table-pin.json')
tool = base['tool']
lean = Path(tool['path']) / 'bin/lean'
assert sha(lean) == tool['binary_sha256']
assert sha(P / base['source']['path']) == base['source']['sha256']
assert sha(P / base['compiled']['path']) == base['compiled']['sha256']
assert sha(P / base['qualification']['path']) == base['qualification']['sha256']
assert read(P / base['qualification']['path'])['status'] == 'passed'
E.mkdir(exist_ok=True)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [P / 'metatheory/GraphSelection.lean', P / 'metatheory/GraphSelectionExamples.lean',
           *sorted((P / 'metatheory/graph-selection-controls').glob('*.lean')), Path(__file__)]
source_pin = {}
for source in sources:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes(), name
    source_pin[name] = sha(source)
write(E / 'source-pin.json', {'code_commit': commit, 'source_sha256': source_pin})
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))


def check(source, expected, audits=0):
    name = source.stem
    output = E / (name + '.olean')
    output.unlink(missing_ok=True)
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=2G',
               '--property=MemorySwapMax=0', '--property=RuntimeMaxSec=300',
               '--property=KillMode=control-group', '--setenv=LEAN_PATH=' + str(E) + ':' + str(BASE),
               str(lean), '--root=' + str(source.parent), '-o', str(output), str(source)]
    write(E / (name + '-command.json'), command)
    log = E / (name + '-checks.txt')
    with log.open('w') as stream:
        code = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT).returncode
    write(E / (name + '-exit.json'), {'exit_code': code, 'olean_present': output.exists()})
    text = log.read_text()
    if expected:
        assert code == 0 and output.exists() and 'error:' not in text, (name, code, text[-3000:])
        assert 'sorry' not in text and 'native_decide' not in text, (name, 'untrusted proof shortcut')
        reports = re.findall(r"'([^']+)' (?:depends on axioms: \[([^]]*)\]|does not depend on any axioms)", text)
        assert len(reports) == audits, (name, 'axiom audit count', len(reports), audits)
        for result, axioms in reports:
            assert set(re.findall(r'[\w.]+', axioms)) <= {'propext', 'Quot.sound'}, (result, axioms)
    else:
        assert code != 0 and 'error:' in text and not output.exists(), (name, 'expected actual proof rejection')
    result = {'source': str(source.relative_to(R)), 'source_sha256': sha(source),
              'exit_code': code, 'expected_acceptance': expected, 'log_sha256': sha(log),
              'axiom_audits': audits, 'olean_sha256': sha(output) if output.exists() else None}
    print(json.dumps({'stage': name, 'status': 'accepted' if expected else 'rejected-as-required'}), flush=True)
    return result


positive = [check(sources[0], True, 7), check(sources[1], True, 5)]
negative = [check(source, False) for source in sources[2:-1]]
assert len(negative) == 4
for name, digest in source_pin.items():
    assert sha(R / name) == digest, 'source changed while checking: ' + name
report = {'schema': 'enchant.formal.graph-selection-model-qualification.v1', 'status': 'passed',
          'recorded_utc': datetime.now(timezone.utc).isoformat(), 'tool_pin': tool,
          'base_graph_table_pin': base, 'source_pin': read(E / 'source-pin.json'),
          'general_theorems': 7, 'example_theorems': 5, 'negative_controls': 4,
          'positive': positive, 'negative': negative,
          'scope': 'Constructive selective fold over finite structural tables; conditional agreement for dependency-closed admitted selections. No theorem about BL reachable/decode loops, runtime atom admission, container equality, budgets, bytes, typed terms or compiler preservation.',
          'compiler_proof_authority': False}
write(E / 'qualification.json', report)
print(json.dumps({'status': 'passed', 'general': 7, 'examples': 5, 'negative_controls': 4}))
