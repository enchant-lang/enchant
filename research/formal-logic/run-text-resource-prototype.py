"""Check text planning against actual primitives on the exact qualified word SDK."""
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
E = P / 'evidence/text-resource-prototype'
E.mkdir(exist_ok=True)
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value): (E / name).write_text(json.dumps(value, indent=2) + '\n')
pin = read(P / 'sdk-pin.json')
parent = read(P / 'evidence/word-integration/qualification.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == pin
assert read(P / 'evidence/word-integration/promotion.json')['selected'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
prototype = P / 'prototypes/text-resources'
files = [Path(__file__), *prototype.rglob('*.bl')]
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
digests = {}
for source in files:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == source.read_bytes()
    digests[name] = sha(source)
write('source-pin.json', {'sdk_pin':pin, 'code_commit':commit, 'source_sha256':digests,
      'parent_qualification_sha256':sha(P / 'evidence/word-integration/qualification.json')})
runtime = Path(tempfile.mkdtemp(prefix='formal-text-resource-runtime-'))
cwd = Path(tempfile.mkdtemp(prefix='formal-text-resource-consumer-'))
command = ['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
           '--unit=work-formal-text-resource-' + pin['engine_fingerprint'][:12],
           '--working-directory=' + str(cwd), '--property=MemoryMax=4G','--property=MemorySwapMax=0',
           '--property=RuntimeMaxSec=600','--property=KillMode=control-group',
           '--setenv=XDG_RUNTIME_DIR=' + str(runtime),'env','-u','BEAM_LISP_PATH',
           '-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',pin['sdk'] + '/bin/bl','--cold',
           '-p',str(prototype),'test',str(prototype / 'text-resource-check.bl')]
write('command.json',command)
(E / 'memory-before.txt').write_text(subprocess.check_output([R / 'scripts/bl-mem'],text=True))
(E / 'qualification.json').unlink(missing_ok=True)
started = time.monotonic()
try:
    with (E / 'checks.txt').open('w') as stream:
        code = subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
finally:
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
log = (E / 'checks.txt').read_text()
green = '1 file(s) passed, 0 failed, 0 incoherent' in log and 'not green' not in log
write('exit.json',{'process_exit_code':code,'complete_green_test_summary':green,
      'elapsed_seconds':time.monotonic()-started,'runtime_retired':not runtime.exists(),'consumer_cwd_retired':not cwd.exists()})
assert code == 0 and green
assert all(sha(R / name) == digest for name,digest in digests.items())
counts = re.findall(r'✓\s+formal.text-resource-check\s+(\d+) passed',log)
assert len(counts) == 1
write('qualification.json',{'schema':'bl.text-resource-prototype-qualification.v1','status':'passed',
      'sdk_pin':pin,'code_commit':commit,'source_sha256':digests,'assertions':int(counts[0]),
      'in_sdk':False,'managed_text_profile':False,'compiler_proof_authority':False,
      'checked_native_execution':False,'planning_control':'actual private codepoint conversion counter, calibrated with SDK str-len',
      'artifact_sha256':{name:sha(E / name) for name in ['source-pin.json','command.json','checks.txt','exit.json']},
      'scope':'Text byte/temporary/work envelopes compared to actual SDK primitives, explicit codepoint versus grapheme units, exact budgets and pre-decoding refusal controls. No managed text profile, native capability addition, resource-cost theorem, Source equivalence or compiler authority is established.'})
print(json.dumps({'status':'passed','assertions':int(counts[0]),'in_sdk':False}))
