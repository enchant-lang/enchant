"""Reopen the preceding scalar corpus with its original producer pin."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/obligation-integration'
D = E / 'previous-scalar-readers'
D.mkdir(exist_ok=True)
B = P / 'evidence/scalar-integration'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')
pin, producer = read(E / 'sdk-candidate.json'), read(E / 'baseline-sdk-pin.json')
assert read(P / 'sdk-pin.json') == producer
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
linkage = read(E / 'build-linkage.json')
assert linkage['status'] == 'bound' and linkage['sdk_pin'] == pin
for name, digest in linkage['source_sha256'].items():
    assert sha(R / name) == digest == sha(Path(pin['sdk']) / 'lib/beam_lisp-0.1.0' / name)
parent = read(B / 'records-qualification.json')
assert parent['status'] == 'passed' and parent['sdk_pin'] == producer
assert read(E / 'focused-exit.json')['exit_code'] == 0
fixture = B / 'corpus.json'
assert sha(fixture) == parent['checks']['capture']['output_sha256']
script = P / 'scalar-reader.bl'
inputs = [Path(__file__), script, fixture, B / 'records-qualification.json', E / 'sdk-candidate.json', E / 'baseline-sdk-pin.json']
commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=R, text=True).strip()
digests = {}
for source in inputs:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git','show',commit + ':' + name],cwd=R) == source.read_bytes()
    digests[name] = sha(source)
results = []
for stage, mode in [('one','read'),('two','read'),('controls','controls')]:
    runtime = Path(tempfile.mkdtemp(prefix='formal-prior-scalar-runtime-'))
    cwd = Path(tempfile.mkdtemp(prefix='formal-prior-scalar-consumer-'))
    output = D / (stage + '.json')
    output.unlink(missing_ok=True)
    command = ['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
               '--unit=work-formal-obligation-previous-scalar-' + stage + '-' + pin['engine_fingerprint'][:12],
               '--working-directory=' + str(cwd), '--property=MemoryMax=4G','--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=1200','--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + str(runtime),'env','-u','BEAM_LISP_PATH',
               '-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',pin['sdk'] + '/bin/bl','--cold',
               'run',str(script),'--',str(fixture),str(output),mode,str(E / 'baseline-sdk-pin.json')]
    write(D / (stage + '-source-pin.json'), {'code_commit':commit,'source_sha256':digests,'sdk_pin':pin,'recorded_producer_sdk_pin':producer})
    write(D / (stage + '-command.json'),command)
    (D / (stage + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'],text=True))
    start=time.monotonic()
    try:
        with (D / (stage + '-checks.txt')).open('w') as stream:
            code=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT).returncode
    finally:
        shutil.rmtree(runtime)
        shutil.rmtree(cwd)
    write(D / (stage + '-exit.json'), {'exit_code':code,'elapsed_seconds':time.monotonic()-start,
          'runtime_retired':not runtime.exists(),'consumer_cwd_retired':not cwd.exists()})
    assert code==0 and output.exists(),stage
    result=read(output)
    assert result['sdk']==pin['sdk'] and result['recorded-producer-sdk']==producer['sdk']!=pin['sdk']
    assert result['sdk-only'] and result['research-import-path'] is False and result['source-payload-execution'] is False
    assert result['solver-exchanges']==result['oracle-calls']==0
    assert result['checked-native-execution'] is False and result['compiler-proof-authority'] is False
    assert all(sha(R / name)==digest for name,digest in digests.items())
    results.append(result)
    print(json.dumps({'stage':stage,'status':'passed','solver_exchanges':0}),flush=True)
subprocess.run([sys.executable, str(P / 'qualify-obligation-previous-scalar-readers.py')], cwd=R, check=True)
