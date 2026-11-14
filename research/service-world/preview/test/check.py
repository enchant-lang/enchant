#!/usr/bin/env python3
"""Own one bounded native fixture listener and stop it after real browser checks."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SDK = Path('/nix/store/bq1pgk5rmpp8q40v3yd4x2zzk3cmjwyg-beam-lisp-sdk-selection')
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0))
    port = probe.getsockname()[1]
base = f'http://127.0.0.1:{port}'
env = dict(os.environ, PORT=str(port), CONNECTED_BASE_URL=base, BL_DAEMON='off')
server = None
with tempfile.TemporaryDirectory(prefix='connected-rehearsal-') as temporary:
    with (Path(temporary) / 'server.log').open('w+') as log:
        try:
            server = subprocess.Popen([str(SDK / 'bin/bl'), '--cold', 'run', 'serve.bl'],
                                      cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=True)
            until = time.monotonic() + 90
            while True:
                try:
                    with urllib.request.urlopen(base + '/health', timeout=2) as response:
                        data = json.load(response)
                    assert data.get('fixture') and data.get('app') == 'connected-workspace-rehearsal'
                    break
                except (OSError, ValueError):
                    if server.poll() is not None or time.monotonic() > until:
                        log.seek(0)
                        raise RuntimeError('Rehearsal did not start: ' + log.read()[-5000:])
                    time.sleep(0.2)
            subprocess.run(['node', str(ROOT / 'test/browser.cjs')], cwd=ROOT, env=env,
                           timeout=300, check=True)
        finally:
            if server is not None and server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait(timeout=10)
print(json.dumps({'result': 'passed', 'temporaryListenerStopped': True,
                  'sdk': str(SDK), 'temporaryDirectoryRemoved': True}))
