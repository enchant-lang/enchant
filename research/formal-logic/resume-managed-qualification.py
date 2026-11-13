"""Adopt the still-running native unit after its outer command lost supervision.

RefUnit holds the original service object until its real exit code is read.
This never starts/restarts that unit. The remaining stages run serially in a
separate durable supervisor, using the unchanged committed qualification runner.
"""
import ctypes
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/managed-graph'
unit, invocation = sys.argv[1:3]
assert unit == 'run-p297808-i4491174.service'
assert invocation == '0f1bddbe3ee245449efe8c5c6d43b406'

def read(path):
    return json.loads(path.read_text())

def write(path, value):
    temporary = path.with_name(path.name + '.pending')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def state():
    command = ['systemctl', '--user', 'show', unit]
    for name in ('Id', 'ActiveState', 'SubState', 'MainPID', 'Result', 'ExecMainCode', 'ExecMainStatus',
                 'WorkingDirectory', 'InvocationID', 'ExecMainStartTimestampMonotonic', 'ExecStart',
                 'MemoryMax', 'MemorySwapMax', 'RuntimeMaxUSec', 'KillMode'):
        command += ['-p', name]
    result = subprocess.check_output(command, text=True)
    return dict(line.split('=', 1) for line in result.splitlines() if '=' in line)

commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R, text=True).strip()
relative = str(Path(__file__).relative_to(R))
assert subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=R) == Path(__file__).read_bytes()
source = read(E / 'paired-native-corpus-source-pin.json')
for name, digest in source['source_sha256'].items():
    assert sha(R / name) == digest, name
original = read(E / 'paired-native-corpus-command.json')
cwd = Path(next(value.split('=', 1)[1] for value in original if value.startswith('--working-directory=')))
runtime = Path(next(value.split('=', 2)[2] for value in original if value.startswith('--setenv=XDG_RUNTIME_DIR=')))
assert cwd.parent == runtime.parent == Path('/tmp')
assert cwd.name.startswith('formal-managed-consumer-') and runtime.name.startswith('formal-managed-runtime-')

# Keep one user-bus connection open. Unit references are released on disconnect;
# a one-shot busctl RefUnit would therefore not protect the terminal receipt.
library = Path(shutil.which('systemctl')).resolve().parent.parent / 'lib/libsystemd.so.0'
buslib = ctypes.CDLL(str(library))
bus = ctypes.c_void_p()
buslib.sd_bus_open_user.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
buslib.sd_bus_open_user.restype = ctypes.c_int
assert buslib.sd_bus_open_user(ctypes.byref(bus)) >= 0
buslib.sd_bus_call_method.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                                    ctypes.c_char_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p]
buslib.sd_bus_call_method.restype = ctypes.c_int
buslib.sd_bus_unref.argtypes = [ctypes.c_void_p]
buslib.sd_bus_unref.restype = ctypes.c_void_p

def reference(method):
    result = buslib.sd_bus_call_method(bus, b'org.freedesktop.systemd1', b'/org/freedesktop/systemd1',
                b'org.freedesktop.systemd1.Manager', method.encode(), None, None, b's', unit.encode())
    if result < 0:
        raise RuntimeError(f'{method} failed: {result}')

held = False
try:
    reference('RefUnit')
    held = True
    first = state()
    assert first['Id'] == unit and first['InvocationID'] == invocation
    assert first['ActiveState'] in ('active', 'deactivating')
    assert first['WorkingDirectory'] == str(cwd)
    assert first['MemoryMax'] == str(4 * 1024**3) and first['MemorySwapMax'] == '0'
    assert first['RuntimeMaxUSec'] == '1h' and first['KillMode'] == 'control-group'
    assert source['sdk_pin']['sdk'] + '/bin/bl' in original
    for value in (str(P / 'graph-consumers-check.bl'), str(E / 'paired-native-corpus.json')):
        assert value in first['ExecStart'] and value in original
    write(E / 'paired-native-corpus-adoption-source-pin.json',
          {'code_commit': commit, 'recipe': relative, 'recipe_sha256': sha(Path(__file__)),
           'original_source_pin_sha256': sha(E / 'paired-native-corpus-source-pin.json'),
           'unit': unit, 'invocation': invocation, 'initial_state': first,
           'outer_exec_handle': 48097, 'outer_handle_exit_code': 143,
           'scope': 'Original native service held and observed, never restarted; outer runner exit was not a check result.'})
    while True:
        observed = state()
        assert observed['InvocationID'] == invocation
        write(E / 'paired-native-corpus-adoption-state.json',
              {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'state': observed})
        if observed['ActiveState'] in ('inactive', 'failed'):
            break
        time.sleep(3)
    success = observed['Result'] == 'success' and observed['ExecMainCode'] == '1' and observed['ExecMainStatus'] == '0'
    code = 0 if success else (int(observed['ExecMainStatus']) or 125)
    if observed['ExecMainCode'] != '1' and code:
        code += 128
    write(E / 'paired-native-corpus-adoption-terminal.json', observed)
    journal = subprocess.check_output(['journalctl', '--user', '-u', unit, '--no-pager', '-o', 'json'], text=True)
    events = []
    for line in journal.splitlines():
        event = json.loads(line)
        if event.get('USER_INVOCATION_ID') == invocation:
            events.append({key: event[key] for key in ('MESSAGE', 'MESSAGE_ID', '__REALTIME_TIMESTAMP',
                           'USER_UNIT', 'USER_INVOCATION_ID', 'EXIT_CODE', 'EXIT_STATUS', 'JOB_RESULT') if key in event})
    write(E / 'paired-native-corpus-adoption-journal.json', events)
    assert observed['MainPID'] == '0'
    shutil.rmtree(runtime)
    shutil.rmtree(cwd)
    write(E / 'paired-native-corpus-exit.json',
          {'exit_code': code, 'runtime_retired': not runtime.exists(), 'consumer_cwd_retired': not cwd.exists(),
           'elapsed_seconds': time.monotonic() - int(observed['ExecMainStartTimestampMonotonic']) / 1_000_000,
           'elapsed_scope': 'Actual original service lifetime, plus terminal observation/cleanup.',
           'exit_source': 'retained-original-systemd-service',
           'adoption_terminal_sha256': sha(E / 'paired-native-corpus-adoption-terminal.json'),
           'original_runner_completion': 'not-observed-outer-handle-ended-143'})
    print(json.dumps({'stage': 'paired-native-corpus', 'exit_code': code, 'same_original_unit': True}), flush=True)
finally:
    if held:
        reference('UnrefUnit')
    buslib.sd_bus_unref(bus)
if code:
    raise SystemExit(code)
assert len(read(E / 'paired-native-corpus.json')['rows']) == 187
for stage in ('managed-native-corpus', 'managed-reader-one', 'managed-reader-two', 'managed-reader-controls'):
    write(E / 'durable-supervisor-state.json', {'stage': stage, 'status': 'running',
          'recorded_utc': datetime.now(timezone.utc).isoformat()})
    code = subprocess.run(['python3', str(P / 'run-managed-graph.py'), stage], cwd=R).returncode
    if code:
        write(E / 'durable-supervisor-state.json', {'stage': stage, 'status': 'failed', 'exit_code': code})
        raise SystemExit(code)
write(E / 'durable-supervisor-state.json', {'status': 'completed', 'exit_code': 0,
      'recorded_utc': datetime.now(timezone.utc).isoformat()})
