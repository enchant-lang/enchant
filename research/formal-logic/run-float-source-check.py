"""Run one bounded qualification stage against the exact binary64 candidate SDK."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/float-source'
prior = P / 'evidence/migrations'
pin = json.loads((E / 'sdk-candidate.json').read_text())
sdk = pin['sdk']
stage = sys.argv[1]
cleanup = []

def command_for(arguments, consumer=False):
    runtime = tempfile.mkdtemp(prefix='formal-float-' + stage + '-')
    cleanup.append(runtime)
    cwd = str(R)
    if consumer:
        cwd = tempfile.mkdtemp(prefix='formal-float-consumer-')
        cleanup.append(cwd)
    return ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
            '--working-directory=' + cwd, '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
            '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
            '--setenv=XDG_RUNTIME_DIR=' + runtime,
            'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', '-u', 'BEAM_LISP_PATH',
            sdk + '/bin/bl', '--cold', *arguments]

if stage in ('preceding-focused', 'regression', 'preparation-focused', 'migration-focused'):
    inherited = 'focused' if stage == 'migration-focused' else stage
    command = json.loads((prior / (inherited + '-command.json')).read_text())
    command = [value.replace(json.loads((prior / 'sdk-candidate.json').read_text())['sdk'], sdk)
               .replace(str(prior / 'regression'), str(E / 'regression')) for value in command]
    runtime = tempfile.mkdtemp(prefix='formal-float-' + stage + '-')
    cleanup.append(runtime)
    command = ['--setenv=XDG_RUNTIME_DIR=' + runtime if value.startswith('--setenv=XDG_RUNTIME_DIR=') else value
               for value in command]
    if stage == 'regression':
        (E / 'regression').mkdir(exist_ok=True)
elif stage == 'focused':
    command = command_for(['test', 'test/bl/formal/beam_float_test.bl', 'test/bl/system/sorts_test.bl',
                           'test/bl/system/seam_test.bl', 'test/bl/system/native_eligible_test.bl'])
elif stage == 'arithmetic-sdk':
    command = command_for(['test', str(P / 'test/ieee_arithmetic_test.bl')])
elif stage in ('examples', 'ledger-write', 'ledger-read'):
    arguments = ['examples', str(E / 'examples.json')] if stage == 'examples' else [
        stage.removeprefix('ledger-'), str(E / 'durable-ledger'), str(E / (stage + '.json'))]
    command = command_for(['run', str(P / 'float-source-check.bl'), '--', *arguments], consumer=True)
elif stage == 'compiler-floor':
    command = ['python3', 'scripts/check-produced-compiler.py', '--sdk', sdk, '--out', str(E / 'produced-compiler.json')]
elif stage == 'preflight':
    command = ['scripts/sdk-preflight', '--sdk', sdk, '--root', pin['source'], '--out', str(E / 'source-preflight.json')]
elif stage == 'preflight-controls':
    command = ['python3', 'test/scripts/sdk_preflight.py', '--sdk', sdk]
else:
    raise ValueError('unknown stage: ' + stage)

(E / (stage + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
with (E / (stage + '-memory-before.txt')).open('w') as output:
    subprocess.run([R / 'scripts/bl-mem'], stdout=output, check=True)
try:
    with (E / (stage + '-checks.txt')).open('w') as output:
        status = subprocess.run(command, cwd=R, stdout=output, stderr=subprocess.STDOUT).returncode
finally:
    for path in cleanup:
        shutil.rmtree(path)
    (E / (stage + '-runtime.json')).write_text(json.dumps(
        {'paths': cleanup, 'retired': all(not Path(path).exists() for path in cleanup)}, indent=2) + '\n')
(E / (stage + '-exit.json')).write_text(json.dumps({'stage': stage, 'exit_code': status}) + '\n')
print(json.dumps({'stage': stage, 'exit_code': status}))
raise SystemExit(status)
