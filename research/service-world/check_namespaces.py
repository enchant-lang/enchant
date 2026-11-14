#!/usr/bin/env python3
"""Two exact SDK VMs; the application uses ordinary require and function calls."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import json

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--provider-sdk', required=True, type=Path)
parser.add_argument('--consumer-sdk', required=True, type=Path)
args = parser.parse_args()
for sdk in (args.provider_sdk, args.consumer_sdk):
    if not str(sdk.resolve()).startswith('/nix/store/') or not (sdk / 'bin/bl').is_file():
        parser.error('Expected an immutable SDK selection')
if args.provider_sdk.resolve() == args.consumer_sdk.resolve():
    parser.error('Use distinct SDK selections')
with tempfile.TemporaryDirectory(prefix='enchant-namespace-') as temporary:
    root = Path(temporary)
    (root / 'provider.bl').write_text((ROOT / 'test/fixtures/catalog.bl').read_text())
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    env = {**os.environ, 'BL_DAEMON': 'off', 'PORT': str(port), 'SERVICE_WORLD_FIXTURE_DIR': str(root),
           'SERVICE_WORLD_FIXTURE_URL': f'http://127.0.0.1:{port}/realms/v1', 'SERVICE_WORLD_SOURCE': str(ROOT)}
    common = ['--cold', '-p', str(ROOT / 'src')]
    server = None
    with (root / 'server.log').open('w+') as log:
        try:
            server = subprocess.Popen([str(args.provider_sdk / 'bin/bl'), *common,
                                       'run', str(ROOT / 'test/namespace_server.bl')],
                                      cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 90
            while not (root / 'ready').exists():
                if server.poll() is not None or time.monotonic() > deadline:
                    log.seek(0)
                    raise RuntimeError('Namespace provider failed: ' + log.read()[-3000:])
                time.sleep(0.1)
            subprocess.run([str(args.consumer_sdk / 'bin/bl'), *common,
                            'test', str(ROOT / 'test/namespace_remote_test.bl')],
                           cwd=root, env=env, timeout=120, check=True)
        finally:
            if server is not None and server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait(timeout=10)
    print(json.dumps({'result': 'passed', 'interface': 'ordinary require and function calls',
                      'providerSdk': str(args.provider_sdk.resolve()), 'consumerSdk': str(args.consumer_sdk.resolve()),
                      'providerStopped': True, 'temporaryAuthority': True}))
