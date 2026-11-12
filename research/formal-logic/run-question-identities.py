"""Compare full canonical questions on the preceding and candidate SDKs, sequentially."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

P=Path(__file__).resolve().parent
R=P.parent.parent
E=P/'evidence/float-source'
program=P/'question-identities.bl'
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
pins={k:json.loads((E/name).read_text()) for k,name in [('baseline','baseline-sdk-pin.json'),('current','sdk-candidate.json')]}
original=subprocess.check_output(['git','show','093a4cfa9:research/formal-logic/src/formal/floating.bl'],cwd=R)
assert original==(R/'priv/lib/formal/floating.bl').read_bytes()
results={}
for label,pin in pins.items():
    root=Path(tempfile.mkdtemp(prefix='formal-question-identities-'+label+'-'))
    runtime=root/'runtime';runtime.mkdir()
    imports=root/'imports';(imports/'formal').mkdir(parents=True)
    if label=='baseline': (imports/'formal/floating.bl').write_bytes(original)
    command=['systemd-run','--user','--quiet','--collect','--wait','--pipe',
             '--working-directory='+str(R),'--property=MemoryMax=4G','--property=MemorySwapMax=0',
             '--property=RuntimeMaxSec=300','--property=KillMode=control-group',
             '--setenv=XDG_RUNTIME_DIR='+str(runtime),
             'env','-u','BEAM_LISP_PATH','-u','ENCHANT_FORMAL_WORKER','-u','ENCHANT_Z3_LIBRARY',
             pin['sdk']+'/bin/bl','--cold','-p',str(imports),'-p',str(P/'src'),
             'run',str(program),'--',str(E/('question-identities-'+label+'.json'))]
    (E/('question-identities-'+label+'-command.json')).write_text(json.dumps(command,indent=2)+'\n')
    with (E/('question-identities-'+label+'-memory-before.txt')).open('w') as output:
        subprocess.run([str(R/'scripts/bl-mem')],stdout=output,check=True)
    try:
        with (E/('question-identities-'+label+'-checks.txt')).open('w') as output:
            result=subprocess.run(command,cwd=R,stdout=output,stderr=subprocess.STDOUT).returncode
    finally:
        shutil.rmtree(root)
    (E/('question-identities-'+label+'-exit.json')).write_text(json.dumps({'exit_code':result,'runtime_retired':not root.exists()})+'\n')
    if result: raise SystemExit(result)
    results[label]=json.loads((E/('question-identities-'+label+'.json')).read_text())
    print(json.dumps({'stage':label,'exit_code':result}),flush=True)
assert results['baseline']==results['current']
assert len(results['current']['rows'])==187
report={'schema':'enchant.formal.complete-question-identity-qualification.v1','status':'passed','checkpoint':41,
        'sdk_pins':pins,'full_canonical_questions':187,'equal':True,
        'managed_query_calls':0,'managed_query_scope':'question-construction',
        'baseline_import':{'historical_commit':'093a4cfa9','old_path':'research/formal-logic/src/formal/floating.bl',
                           'production_path':'priv/lib/formal/floating.bl','sha256':hashlib.sha256(original).hexdigest(),
                           'identical_bytes':True,'temporary_import_retired':True},
        'source_commit':head,'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
        'scope':'Complete canonical formal.query data, not only a root-term digest. No native solver executions in this comparison.',
        'compiler_proof_authority':False}
(E/'complete-question-identity-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'passed','complete_questions':187,'baseline_and_current_identical':True}))
