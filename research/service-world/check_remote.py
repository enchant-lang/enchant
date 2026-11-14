#!/usr/bin/env python3
"""Two real SDK VMs, private authority/data, bounded lifetime, complete cleanup."""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--provider-sdk', required=True, type=Path)
parser.add_argument('--consumer-sdk', required=True, type=Path)
args = parser.parse_args()
for sdk in (args.provider_sdk, args.consumer_sdk):
    if not str(sdk.resolve()).startswith('/nix/store/') or not (sdk / 'bin/bl').is_file():
        parser.error('SDKs must be immutable Nix selections')
if args.provider_sdk.resolve() == args.consumer_sdk.resolve():
    parser.error('Use two distinct SDK selections to qualify version skew')

with tempfile.TemporaryDirectory(prefix='enchant-service-world-') as temporary:
    root = Path(temporary)
    (root / 'a').mkdir()
    token = secrets.token_hex(32)
    (root / 'token').write_text(token)
    (root / 'token').chmod(0o600)
    expiry = int(time.time() * 1000) + 300_000
    authority = ('{:world "qa/world" :tokens {' + json.dumps(token)
                 + ' {:subject "team-machine-next" :world "qa/world" :expires-at ' + str(expiry)
                 + ' :grants [{:scope "qa-place" :folder ' + json.dumps(str(root / 'a'))
                 + ' :tree true :contract "workstation.service" :operations #{"inspect"}}]}}}')
    (root / 'authority.edn').write_text(authority)
    (root / 'authority.edn').chmod(0o600)
    (root / 'catalog.json').write_text(json.dumps([
        {'id': 'different-name.owner', 'name': 'Different name', 'folder': str(root / 'a'),
         'owner': 'owner', 'url': 'https://station.example/', 'listening': True},
        {'id': 'private.owner', 'name': 'Private', 'folder': str(root / 'ab'),
         'owner': 'owner', 'url': None, 'listening': True},
    ]))
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    env = {**os.environ, 'BL_DAEMON': 'off', 'PORT': str(port),
           'SERVICE_WORLD_FIXTURE_DIR': str(root),
           'SERVICE_WORLD_FIXTURE_URL': f'http://127.0.0.1:{port}/services/v1'}
    common = ['--cold', '-p', str(ROOT / 'src')]
    server = None
    with (root / 'provider.log').open('w+') as log:
        try:
            server = subprocess.Popen([str(args.provider_sdk / 'bin/bl'), *common,
                                       'run', str(ROOT / 'test/fixture_server.bl')],
                                      cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=True)
            deadline = time.monotonic() + 90
            while not (root / 'ready').exists():
                if server.poll() is not None or time.monotonic() >= deadline:
                    log.seek(0)
                    raise RuntimeError('Provider failed readiness: ' + log.read()[-4000:])
                time.sleep(0.1)
            subprocess.run([str(args.consumer_sdk / 'bin/bl'), *common,
                            'test', str(ROOT / 'test/remote_test.bl')],
                           cwd=root, env=env, timeout=120, check=True)
            print(json.dumps({'result': 'passed', 'providerSdk': str(args.provider_sdk.resolve()),
                              'consumerSdk': str(args.consumer_sdk.resolve()),
                              'transport': 'authenticated loopback HTTP', 'temporaryData': True}))
        finally:
            if server is not None and server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait(timeout=10)
