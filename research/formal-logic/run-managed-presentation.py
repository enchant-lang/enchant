"""Fresh SDK request dossier execution and actual browser checks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-presentation'
C = P / 'evidence/managed-graph'
I = P / 'evidence/managed-integration'
E.mkdir(exist_ok=True)
O = P / 'evidence/observation-semantics'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

stage = sys.argv[1]
assert stage in ('inputs', 'cells', 'check', 'browser', 'focused')
pin = read(P / 'sdk-pin.json')
code = read(C / 'qualification.json')
assert code['status'] == 'passed' and code['sdk_pin'] == pin
integration = read(I / 'qualification.json')
assert integration['status'] == 'passed' and integration['sdk_pin'] == pin
assert sha(Path(pin['sdk']) / 'artifact.json') == pin['descriptor_sha256']
kit = read(O / 'kit-state.json')
for name, digest in kit['rendering_source_sha256'].items():
    assert sha(Path(kit['root']) / name) == digest
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
sources = [*(P / 'src').rglob('*.bl'), P / 'ATLAS.bl.org', P / 'sdk-pin.json', Path(__file__),
           P / 'dossier-inputs-check.bl', P / 'managed-request-browser.mjs', P / 'story-audit.mjs',
           P / 'browser-driver.mjs', P / 'REQUEST-INTERFACE.md', P / 'MANAGED-GRAPH.md', C / 'qualification.json', I / 'qualification.json']
digests = {}
for source in sorted(sources):
    name = str(source.relative_to(R))
    body = source.read_bytes()
    assert subprocess.check_output(['git', 'show', commit + ':' + name], cwd=R) == body
    digests[name] = hashlib.sha256(body).hexdigest()
snapshot = {'code_commit': commit, 'source_sha256': digests, 'sdk_pin': pin,
            'kit_state_sha256': sha(O / 'kit-state.json'), 'document_sha256': sha(P / 'ATLAS.bl.org')}

def run(name, command, runtime=None):
    (E / (name + '-exit.json')).unlink(missing_ok=True)
    write(E / (name + '-source-pin.json'), snapshot)
    write(E / (name + '-command.json'), command)
    (E / (name + '-memory-before.txt')).write_text(subprocess.check_output([R / 'scripts/bl-mem'], text=True))
    started = time.monotonic()
    try:
        with (E / (name + '-checks.txt')).open('w') as stream:
            result = subprocess.run(command, cwd=R, stdout=stream, stderr=subprocess.STDOUT).returncode
    finally:
        if runtime:
            shutil.rmtree(runtime)
    write(E / (name + '-exit.json'), {'exit_code': result, 'runtime_retired': not runtime or not runtime.exists(),
          'elapsed_seconds': time.monotonic() - started, 'document_sha256': sha(P / 'ATLAS.bl.org')})
    print(json.dumps({'stage': name, 'exit_code': result}), flush=True)
    if result:
        raise SystemExit(result)

if stage in ('inputs', 'cells', 'check'):
    runtime = Path(tempfile.mkdtemp(prefix='formal-managed-dossier-'))
    imports = [str(P / 'src'), str(Path(kit['root']) / 'bl-org-dossier/kit'),
               str(Path(kit['root']) / 'codebase-review/kit')]
    request = [pin['sdk'] + '/bin/bl', '--cold']
    for path in imports:
        request += ['-p', path]
    request += (['run', str(P / 'dossier-inputs-check.bl')] if stage == 'inputs'
                else ['doc', 'run', str(P / 'ATLAS.bl.org')])
    if stage == 'check':
        request.append('--check')
    command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe', '--expand-environment=no',
               '--unit=work-formal-managed-dossier-' + stage + '-' + pin['engine_fingerprint'][:12],
               '--working-directory=' + str(R), '--property=MemoryMax=4G', '--property=MemorySwapMax=0',
               '--property=RuntimeMaxSec=1200', '--property=KillMode=control-group',
               '--setenv=XDG_RUNTIME_DIR=' + str(runtime), 'env', '-u', 'BEAM_LISP_PATH',
               '-u', 'ENCHANT_FORMAL_WORKER', '-u', 'ENCHANT_Z3_LIBRARY',
               'BEAM_LISP_PATH=' + ':'.join(imports), *request]
    run('dossier-' + stage, command, runtime)
else:
    assert read(E / 'dossier-check-exit.json')['exit_code'] == 0
    assert read(E / 'dossier-check-exit.json')['document_sha256'] == snapshot['document_sha256']
    for name, digest in read(E / 'dossier-check-source-pin.json')['source_sha256'].items():
        # Browser assertions and this orchestrator are not executable cell
        # dependencies. Their actual versions are bound by each browser pin.
        if name not in ('research/formal-logic/managed-request-browser.mjs',
                        'research/formal-logic/run-managed-presentation.py'):
            assert sha(R / name) == digest
    browser_tools = read(O / 'browser-tools.json')
    for name, tool in browser_tools.items():
        assert Path(tool['executable']).is_file()
        assert subprocess.check_output(['nix-store', '--query', '--hash', tool['package']], text=True).strip() == tool['nar_hash']
    write(E / 'browser-tools.json', browser_tools)
    raw = subprocess.check_output(['systemctl', '--user', 'show', 'work-enchant-formal-review.service',
                                   '--property=ActiveState,SubState,ExecMainPID,MemoryMax'], text=True)
    state = dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)
    assert state['ActiveState'] == 'active' and state['SubState'] == 'running' and state['MemoryMax'] == '2147483648'
    boots = [x.decode() for x in Path('/proc/' + state['ExecMainPID'] + '/cmdline').read_bytes().split(b'\0') if x.endswith(b'/boot.exs')]
    process_kit = [x.decode().split('=', 1)[1] for x in Path('/proc/' + state['ExecMainPID'] + '/environ').read_bytes().split(b'\0')
                   if x.startswith(b'FORMAL_REVIEW_KIT_ROOT=')]
    assert boots == [pin['sdk'] + '/boot.exs'] and process_kit == [kit['root']]
    responses = {}
    for name, url in (('local', 'http://127.0.0.1:24089/'), ('tailnet', 'https://work.tailcb5318.ts.net:18100/')):
        with urllib.request.urlopen(url, timeout=60) as response:
            body, status = response.read(), response.status
        assert status == 200 and b'one-portable-request-either-backend' in body
        assert b'cell-story-formal-request' in body and b'graph-source-cursors' in body
        responses[name] = {'url': url, 'status': status, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
    write(E / 'dossier-host.json', {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'state': state,
          'sdk_boot': boots[0], 'kit_root': process_kit[0], 'document_sha256': snapshot['document_sha256'], 'responses': responses})
    stages = [('focused-browser', 'managed-request-browser.mjs', 300)]
    if stage == 'browser':
        stages.append(('full-browser', 'story-audit.mjs', 900))
    for name, script, ceiling in stages:
        command = ['systemd-run', '--user', '--quiet', '--collect', '--wait', '--pipe',
                   '--unit=work-formal-managed-dossier-' + name + '-' + pin['engine_fingerprint'][:12],
                   '--working-directory=' + str(R), '--property=MemoryMax=2G', '--property=MemorySwapMax=0',
                   '--property=RuntimeMaxSec=' + str(ceiling), '--property=KillMode=control-group',
                   '--setenv=FORMAL_BROWSER_EXECUTABLE=' + browser_tools['chromium']['executable'],
                   browser_tools['node']['executable'], str(P / script), 'http://127.0.0.1:24089', str(E / name)]
        run(name, command)
