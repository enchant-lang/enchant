#!/usr/bin/env python3
"""A warm command whose client is ended by SIGTERM or SIGKILL is cancelled.

F2 item 4 runs the command in the VM's connection process instead of a child
of it, and the connection's watcher ends that process when the client leaves.
This drives the checkout's real client and VM in an isolated project:

  * for SIGTERM and SIGKILL, a 3 s command whose client dies at 1 s never
    writes its marker, and the VM serves the next command;
  * a command whose own process dies is reported (exit 1, a reason on stderr);
  * afterwards `realm stop` succeeds at once: no request custody leaked.

Run under a memory cap; every VM it started is stopped.
"""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--root', default=Path(__file__).resolve().parents[2], type=Path)
args = parser.parse_args()
launcher = str(args.root.resolve() / 'bin/bl')

with tempfile.TemporaryDirectory(prefix='bl-warm-cancel-') as scratch:
    project = Path(scratch)
    runtime = project / '.runtime'
    runtime.mkdir(mode=0o700)
    (project / 'env.bl').write_text('{:name "warm-cancel-test"}')
    env = {**os.environ, 'XDG_RUNTIME_DIR': str(runtime), 'XDG_STATE_HOME': str(project / '.state')}
    env.pop('BL_CHECKOUT_COLD', None)
    failures = []

    def check(ok, what):
        print(('PASS ' if ok else 'FAIL ') + what, flush=True)
        if not ok:
            failures.append(what)

    def run(*argv, timeout=420):
        return subprocess.run([launcher, *argv], cwd=project, env=env, text=True,
                              capture_output=True, timeout=timeout)

    def owned_vms():
        found = []
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():
                continue
            try:
                if f'XDG_RUNTIME_DIR={runtime}'.encode() + b'\0' in (proc / 'environ').read_bytes():
                    argv = (proc / 'cmdline').read_bytes().split(b'\0')
                    if Path(os.fsdecode(argv[0])).name in {'beam.smp', 'beam'} or b'--generation-service' in argv:
                        found.append(int(proc.name))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
        return found

    try:
        first = run('eval', '(println :warm)')
        check(first.returncode == 0 and ':warm' in first.stdout, 'the VM starts and answers')
        for sig in (signal.SIGTERM, signal.SIGKILL):
            marker = project / f'marker-{sig.name}'
            (project / 'slow.bl').write_text(
                f'(Process/sleep 3000) (File/write! "{marker}" "ran")')
            client = subprocess.Popen([launcher, 'run', 'slow.bl'], cwd=project, env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            client.send_signal(sig)
            client.wait(timeout=30)
            time.sleep(3.5)
            check(not marker.exists(), f'{sig.name}: the command was ended before its side effect')
            after = run('eval', '(println (+ 40 2))')
            check(after.returncode == 0 and '42' in after.stdout, f'{sig.name}: the next command is served')
        died = run('eval', '(erlang/exit (erlang/self) :boom)')
        check(died.returncode == 1 and 'ended abnormally' in died.stderr and 'boom' in died.stderr,
              f'a command whose process dies is exit 1 with its reason: {died.returncode} {died.stderr[-200:]!r}')
        check(run('eval', '(println :still)').returncode == 0, 'and the VM serves the next command')
        stop = run('realm', 'stop', timeout=60)
        check(stop.returncode == 0 and 'pending' not in stop.stdout + stop.stderr,
              f'realm stop finds no request in flight: {stop.returncode} {(stop.stdout + stop.stderr)[-200:]!r}')
    finally:
        for pid in owned_vms():
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 3
        while owned_vms() and time.monotonic() < deadline:
            time.sleep(0.05)
        for pid in owned_vms():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    print('warm_cancel: ' + ('ok' if not failures else f'{len(failures)} failed'), flush=True)
    sys.exit(1 if failures else 0)
