#!/usr/bin/env python3
"""Qualify a visible, bounded wait on a busy SDK preparation without a VM.

A held preparation lock names its holder to the waiter, the wait ends with
exit 75 after BL_SDK_LOCK_WAIT seconds, BL_SDK_REUSE_CURRENT=1 selects the
published current SDK under that SDK's own fingerprint, and a released lock
lets the waiter continue into normal selection.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk', type=Path, required=True)
parser.add_argument('--engine', type=Path, required=True)
parser.add_argument('--wrapper', type=Path,
                    default=Path(__file__).resolve().parents[2] / 'scripts/prepare-checkout-sdk')
args = parser.parse_args()
engine = args.engine.resolve(strict=True)
sdk = args.sdk.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='bl-sdk-lock-wait-') as temporary:
    root = Path(temporary) / 'tree'
    shutil.copytree(engine, root)
    for path in [root, *root.rglob('*')]:
        path.chmod(path.stat().st_mode | 0o200)
    wrapper = root / 'scripts/prepare-checkout-sdk'
    shutil.copyfile(args.wrapper, wrapper)
    wrapper.chmod(0o755)
    tools = Path(temporary) / 'tools'
    tools.mkdir()
    for name in ('nix-build', 'systemd-run'):
        tool = tools / name
        tool.write_text('#!/bin/sh\necho "unexpected producer: $0" >&2\nexit 99\n')
        tool.chmod(0o755)
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])
    env.pop('BL_SDK_REUSE_CURRENT', None)
    sdks = root / '.bl/sdks'
    sdks.mkdir(parents=True)
    # A published SDK under a fingerprint that is not the tree's.
    published = 'a' * 64
    (sdks / published).mkdir()
    (sdks / published / 'result-sdk').symlink_to(sdk, target_is_directory=True)
    (sdks / 'current-sdk').symlink_to(sdk, target_is_directory=True)

    def jobs():
        return list(sdks.glob('*/job-*'))

    # Another caller holds the preparation lock and has named itself.
    holder = subprocess.Popen(['flock', '-x', str(sdks / 'preparation.lock'), 'sleep', '120'],
                              start_new_session=True)
    try:
        deadline = time.time() + 10
        while subprocess.run(['flock', '-n', str(sdks / 'preparation.lock'), 'true']).returncode == 0:
            assert time.time() < deadline, 'fixture holder never took the lock'
            time.sleep(0.05)
        (sdks / 'preparation.owner').write_text(
            f'pid={holder.pid}\nstarted=2026-01-01T00:00:00Z\ncaller=fixture holder\n'
            f'fingerprint={"b" * 64}\njob=\nprogress=/fixture/client-prepare.log\n')

        began = time.time()
        result = subprocess.run([str(wrapper), '--selection'], env=dict(env, BL_SDK_LOCK_WAIT='2'),
                                text=True, capture_output=True, timeout=30)
        waited = time.time() - began
        assert result.returncode == 75, (result.returncode, result.stderr)
        assert 1.5 <= waited < 15, waited
        assert f'held by pid {holder.pid}' in result.stderr, result.stderr
        assert 'fixture holder' in result.stderr and 'b' * 64 in result.stderr, result.stderr
        assert 'tail -f /fixture/client-prepare.log' in result.stderr, result.stderr
        assert 'gave up after 2s' in result.stderr, result.stderr
        assert result.stdout == '', result.stdout

        result = subprocess.run([str(wrapper), '--selection'], env=dict(env, BL_SDK_LOCK_WAIT='abc'),
                                text=True, capture_output=True, timeout=30)
        assert result.returncode == 64, (result.returncode, result.stderr)

        result = subprocess.run([str(wrapper), '--selection'], env=dict(env, BL_SDK_REUSE_CURRENT='1'),
                                text=True, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == f'{sdk} {published}', result.stdout
        assert 'may predate engine edits' in result.stderr, result.stderr
        assert not jobs(), 'reuse started a preparation job'

        # A waiter whose holder finishes continues into normal selection: the
        # tree's own fingerprint has no retained SDK, so it would start a
        # preparation, which the fixture refuses at its first producer step.
        waiter = subprocess.Popen([str(wrapper), '--selection'], env=env, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)
        assert waiter.poll() is None, 'waiter did not wait for the held lock'
    finally:
        # flock(1) leaves the lock with its child; release the whole group.
        os.killpg(holder.pid, signal.SIGKILL)
        holder.wait()
    out, err = waiter.communicate(timeout=60)
    assert 'waiting for the SDK preparation' in err, err
    assert waiter.returncode == 69 and 'capturing the immutable engine source' in err, (waiter.returncode, err)
    owner = (sdks / 'preparation.owner').read_text()
    assert f'pid={waiter.pid}' in owner, owner
    fingerprint = subprocess.run([str(wrapper), '--fingerprint'], env=env, text=True,
                                 capture_output=True, check=True).stdout.strip()
    assert f'fingerprint={fingerprint}' in owner, owner

    # With the lock free, BL_SDK_REUSE_CURRENT changes nothing: selection
    # still prepares the tree's own inputs.
    result = subprocess.run([str(wrapper), '--selection'], env=dict(env, BL_SDK_REUSE_CURRENT='1'),
                            text=True, capture_output=True, timeout=60)
    assert result.returncode == 69 and 'capturing the immutable engine source' in result.stderr, result.stderr
print(json.dumps({'status': 'passed', 'sdk': str(sdk), 'bounded_wait': 'exit 75',
                  'reuse_current': 'own fingerprint', 'released_lock': 'continues', 'VMs_started': 0}))
