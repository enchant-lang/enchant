"""Run one qualified migration stage at a time on its exact candidate SDK."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/migrations'
pin = json.loads((E / 'sdk-candidate.json').read_text())
sdk = pin['sdk']
stage = sys.argv[1]
prior = P / 'evidence/query-preparation'
cleanup = []

def private_runtime():
    path = tempfile.mkdtemp(prefix='formal-migration-' + stage + '-')
    cleanup.append(path)
    return path

if stage in ('preceding-focused', 'regression', 'preparation-focused'):
    inherited = 'focused' if stage == 'preparation-focused' else stage
    command = json.loads((prior / (inherited + '-command.json')).read_text())
    command = [value.replace(json.loads((prior / 'sdk-candidate.json').read_text())['sdk'], sdk)
               .replace(str(prior / 'regression'), str(E / 'regression')) for value in command]
    runtime = private_runtime()
    command = ['--setenv=XDG_RUNTIME_DIR=' + runtime if value.startswith('--setenv=XDG_RUNTIME_DIR=') else value
               for value in command]
    if stage == 'regression':
        (E / 'regression').mkdir(exist_ok=True)
elif stage == 'focused':
    runtime = private_runtime()
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + str(R), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + runtime,
               'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', '-u', 'BEAM_LISP_PATH',
               sdk + '/bin/bl', '--cold', 'test', 'test/bl/reload/formal_migration_test.bl',
               'test/bl/reload/migrate_test.bl', 'test/bl/reload/verify_adversarial_test.bl']
elif stage in ('examples', 'ledger-write', 'ledger-read'):
    directory = tempfile.mkdtemp(prefix='formal-migration-consumer-')
    cleanup.append(directory)
    runtime = private_runtime()
    arguments = ['examples', str(E / 'examples.json')] if stage == 'examples' else [
        stage.removeprefix('ledger-'), str(E / 'durable-ledger'), str(E / (stage + '.json'))]
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
               '--working-directory=' + directory, '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=900', '--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + runtime,
               'env', '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY', '-u', 'BEAM_LISP_PATH',
               sdk + '/bin/bl', '--cold', 'run', str(P / 'migration-check.bl'), '--', *arguments]
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
print(json.dumps({'stage': stage, 'exit_code': status}))
raise SystemExit(status)
