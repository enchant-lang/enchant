"""One serial, capped stage using the exact graph candidate SDK."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/graph-consumers'
prior = P / 'evidence/question-graphs'
pin = json.loads((E / 'sdk-candidate.json').read_text())
sdk = pin['sdk']
stage = sys.argv[1]
cleanup = []
def command_for(arguments, consumer=False):
    runtime = tempfile.mkdtemp(prefix='formal-graph-consumer-' + stage + '-')
    cleanup.append(runtime)
    cwd = str(R)
    if consumer:
        cwd = tempfile.mkdtemp(prefix='formal-graph-consumer-consumer-')
        cleanup.append(cwd)
    return ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
            '--working-directory=' + cwd, '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
            '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
            '--setenv=XDG_RUNTIME_DIR=' + runtime,
            'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', '-u', 'BEAM_LISP_PATH',
            sdk + '/bin/bl', '--cold', *arguments]
if stage == 'focused':
    command = command_for(['test', 'test/bl/formal/graph_ops_test.bl', 'test/bl/formal/graph_context_test.bl', 'test/bl/veritas/graph_ledger_test.bl', 'test/bl/formal/data_graph_test.bl', 'test/bl/formal/point_test.bl', 'test/bl/formal/float_points_test.bl'])
elif stage == 'facade':
    command = command_for(['-p', str(P/'src'), 'test', str(P/'test/graph_facade_test.bl'), str(P/'test/facade_test.bl'), str(P/'test/api_test.bl'), 'test/bl/system/formal_answer_test.bl', 'test/bl/system/formal_oracle_test.bl', 'test/bl/system/formal_effect_test.bl', 'test/bl/veritas/ledger_test.bl'])
elif stage == 'corpus':
    command = command_for(['-p', str(P/'src'), 'run', str(P/'graph-consumers-check.bl'), '--', str(E/'corpus.json')])
elif stage == 'writer':
    command = command_for(['run', str(P/'graph-ledger-writer.bl'), '--', str(E/'durable-ledger'), str(E/'writer.json')], consumer=True)
elif stage in ('consumer-one','consumer-two'):
    command = command_for(['run', str(P/'graph-ledger-consumer.bl'), '--', str(E/'durable-ledger'), str(E/(stage+'.json'))], consumer=True)
elif stage == 'regression':
    command = json.loads((prior/'regression-command.json').read_text())
    old = json.loads((prior/'sdk-candidate.json').read_text())['sdk']
    command = [x.replace(old, sdk).replace(str(prior/'regression'),str(E/'regression')) for x in command]
    runtime = tempfile.mkdtemp(prefix='formal-graph-consumer-regression-'); cleanup.append(runtime)
    command = ['--setenv=XDG_RUNTIME_DIR='+runtime if x.startswith('--setenv=XDG_RUNTIME_DIR=') else x for x in command]
    (E/'regression').mkdir(exist_ok=True)
elif stage == 'compiler-floor':
    command = ['python3', 'scripts/check-produced-compiler.py', '--sdk', sdk, '--out', str(E/'produced-compiler.json')]
elif stage == 'preflight':
    command = ['scripts/sdk-preflight','--sdk',sdk,'--root',pin['source'],'--out',str(E/'source-preflight.json')]
elif stage == 'preflight-controls':
    command = ['python3','test/scripts/sdk_preflight.py','--sdk',sdk]
else: raise ValueError(stage)
(E/(stage+'-command.json')).write_text(json.dumps(command,indent=2)+'\n')
with (E/(stage+'-memory-before.txt')).open('w') as f: subprocess.run([R/'scripts/bl-mem'],stdout=f,check=True)
try:
    with (E/(stage+'-checks.txt')).open('w') as f:
        status = subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT).returncode
finally:
    for path in cleanup: shutil.rmtree(path)
    (E/(stage+'-runtime.json')).write_text(json.dumps({'paths':cleanup,'retired':all(not Path(x).exists() for x in cleanup)},indent=2)+'\n')
(E/(stage+'-exit.json')).write_text(json.dumps({'stage':stage,'exit_code':status})+'\n')
print(json.dumps({'stage':stage,'exit_code':status}))
raise SystemExit(status)
