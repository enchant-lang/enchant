#!/usr/bin/env python3
"""Qualify restored SDK hits and changed-source refusal without starting a VM."""
import argparse
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk', type=Path, required=True)
parser.add_argument('--engine', type=Path, required=True)
parser.add_argument('--platform', type=Path, default=os.environ.get('BL_CHECKOUT_PLATFORM'),
                    help='checkout platform whose drop-launcher the settled selection (K2) uses')
args = parser.parse_args()
engine = args.engine.resolve(strict=True)
sdk = args.sdk.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='bl-sdk-cache-hit-') as temporary:
    root = Path(temporary) / 'tree'
    shutil.copytree(engine, root)
    for path in [root, *root.rglob('*')]:
        path.chmod(path.stat().st_mode | 0o200)
    tools = Path(temporary) / 'tools'
    tools.mkdir()
    for name in ('nix-build', 'systemd-run'):
        tool = tools / name
        tool.write_text('#!/bin/sh\necho "unexpected producer: $0" >&2\nexit 99\n')
        tool.chmod(0o755)
    env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'])
    wrapper = root / 'scripts/prepare-checkout-sdk'
    wrapper.chmod(0o755)
    loader = importlib.machinery.SourceFileLoader('cache_hit_inputs', str(root / 'scripts/sdk-inputs'))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    policy = json.loads((root / 'nix/engine-inputs.json').read_text())

    def retain():
        fingerprint = module.fingerprint(root, policy)
        directory = root / '.bl/sdks' / fingerprint
        directory.mkdir(parents=True)
        (directory / 'result-sdk').symlink_to(sdk, target_is_directory=True)
        (directory / 'source-engine').symlink_to(engine, target_is_directory=True)
        return fingerprint, directory

    fingerprint, directory = retain()
    result = subprocess.run([str(wrapper), '--selection'], env=env, text=True,
                            capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(sdk) + ' ' + fingerprint, result.stdout
    assert (root / '.bl/sdks/current-sdk').resolve() == sdk
    assert not list(directory.glob('job-*')), 'cache hit created a producer job'
    settled = 'skipped (no --platform)'
    if args.platform:
        # K2: the verified hit is recorded, and the next selection of the same
        # tree is answered from the client's inventory with no Python at all.
        assert (directory / 'selection.v1').is_file(), 'verified hit left no record'
        (tools / 'python3').write_text('#!/bin/sh\necho "unexpected python3" >&2\nexit 98\n')
        (tools / 'python3').chmod(0o755)
        fast = dict(env, BL_CHECKOUT_PLATFORM=str(args.platform.resolve(strict=True)))
        def select(environment):
            return subprocess.run([str(wrapper), '--selection'], env=environment, text=True,
                                  capture_output=True, timeout=60)
        result = select(fast)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == str(sdk) + ' ' + fingerprint, result.stdout
        # Every condition the record vouches for is re-read: a current-sdk that
        # names another product, a moved source link, an edited record, or the
        # digest cache turned off sends selection back to the verified path
        # (here the refusing python3 proves it was taken).
        current = root / '.bl/sdks/current-sdk'
        current.unlink()
        current.symlink_to(root, target_is_directory=True)
        assert select(fast).returncode != 0, 'stale current-sdk took the settled path'
        current.unlink()
        current.symlink_to(sdk, target_is_directory=True)
        source_link = directory / 'source-engine'
        source_link.unlink()
        source_link.symlink_to(sdk, target_is_directory=True)
        assert select(fast).returncode != 0, 'moved source link took the settled path'
        source_link.unlink()
        source_link.symlink_to(engine, target_is_directory=True)
        record = directory / 'selection.v1'
        text = record.read_text()
        record.write_text(text.replace(fingerprint, '0' * 64, 1))
        assert select(fast).returncode != 0, 'edited record took the settled path'
        record.write_text(text)
        assert select(dict(fast, BL_CHECKOUT_DIGEST_CACHE='0')).returncode != 0, 'cache-off took the settled path'
        assert select(fast).returncode == 0
        (tools / 'python3').unlink()
        settled = 'python-free'
    # Only the private fixture changes; the actual immutable SDK stays intact.
    source = root / 'priv/std/errors.bl'
    source.write_text(source.read_text() + '\n; changed engine input\n')
    changed, directory = retain()
    assert changed != fingerprint
    if args.platform:
        # The edited tree's own fingerprint has no record, so even with the
        # client's inventory it takes the verifying path, which refuses.
        result = subprocess.run([str(wrapper), '--selection'], text=True, capture_output=True, timeout=60,
                                env=dict(env, BL_CHECKOUT_PLATFORM=str(args.platform.resolve(strict=True)),
                                         BL_CHECKOUT_DEV_OVERLAY='0'))
        assert result.returncode == 69 and 'engine bytes differ' in result.stderr, (result.returncode, result.stderr)
    result = subprocess.run([str(wrapper)], env=env, text=True,
                            capture_output=True, timeout=60)
    assert result.returncode == 69, (result.returncode, result.stderr)
    assert 'engine bytes differ' in result.stderr, result.stderr
    assert not list(directory.glob('job-*')), 'invalid selection started production'
print(json.dumps({'status': 'passed', 'sdk': str(sdk), 'cache_hit_jobs': 0,
                  'changed_source': 'refused', 'settled_selection': settled, 'VMs_started': 0}))
