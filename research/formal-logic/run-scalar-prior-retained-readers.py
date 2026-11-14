"""Reopen the preceding numeric retained corpus with its original producer pin."""
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
E = P / 'evidence/scalar-integration'
D = E / 'prior-retained-readers'
D.mkdir(exist_ok=True)
B = P / 'evidence/retained-request'
def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2) + '\n')
producer_path = P / 'evidence/word-integration/baseline-sdk-pin.json'
pin, producer = read(E / 'sdk-candidate.json'), read(producer_path)
assert read(P / 'sdk-pin.json') == read(E / 'baseline-sdk-pin.json')
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
script = P / 'prior-retained-reader.bl'
inputs = [Path(__file__), script, fixture, B / 'records-qualification.json', E / 'sdk-candidate.json', E / 'baseline-sdk-pin.json', producer_path]
commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=R, text=True).strip()
digests = {}
for source in inputs:
    name = str(source.relative_to(R))
    assert subprocess.check_output(['git','show',commit + ':' + name],cwd=R) == source.read_bytes()
    digests[name] = sha(source)
results = []
for stage, mode in [('one','read'),('two','read'),('controls','controls')]:
    runtime = Path(tempfile.mkdtemp(prefix='formal-prior-retained-runtime-'))
    cwd = Path(tempfile.mkdtemp(prefix='formal-prior-retained-consumer-'))
    output = D / (stage + '.json')
    output.unlink(missing_ok=True)
    command = ['systemd-run','--user','--quiet','--collect','--wait','--pipe','--expand-environment=no',
               '--unit=work-formal-scalar-prior-retained-' + stage + '-' + pin['engine_fingerprint'][:12],
               '--working-directory=' + str(cwd), '--property=MemoryMax=4G','--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=1200','--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + str(runtime),'env','-u','BEAM_LISP_PATH',
               '-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',pin['sdk'] + '/bin/bl','--cold',
               'run',str(script),'--',str(fixture),str(output),mode,str(producer_path)]
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
assert results[0]['process']!=results[1]['process'] and results[0]['cwd']!=results[1]['cwd']
assert results[0]['rows']==results[1]['rows']==read(B / 'reader-one.json')['rows']
assert len(results[0]['rows'])==12 and results[0]['ledger'] is None and results[1]['ledger'] is None
assert len(results[2]['controls'])==12 and all(row['status']=='refused' for row in results[2]['controls'])
assert results[2]['rehashed-invalid-coordinate']=='independently-invalid'
write(E / 'prior-retained-readers-qualification.json',{'schema':'bl.scalar-sdk-prior-retained-readers.v1','status':'passed',
      'sdk_pin':pin,'recorded_producer_sdk_pin':producer,'source_sha256':digests,'code_commit':commit,
      'records':12,'fresh_sdk_only_readers':2,'refusal_controls':12,'solver_exchanges':0,'oracle_calls':0,
      'artifact_sha256':{str(f.relative_to(D)):sha(f) for f in sorted(D.glob('*')) if f.is_file()},
      'checked_native_execution':False,'compiler_proof_authority':False,
      'scope':'Actual prior numeric retained/fresh/supplied packets replayed with the new SDK. Producer and checker remain separate. The retired prior durable store is not recreated or claimed as reopened here.'})
