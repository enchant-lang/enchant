#!/usr/bin/env python3
"""One sequential, bounded qualification of the frozen Scheme seed inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
OUT = BASE / 'out'
EVIDENCE = BASE / 'evidence'
TOOLS = json.loads((BASE / 'toolchain-pin.json').read_text())
GAMBIT = Path(TOOLS['gambit'])
CLANG = Path(TOOLS['clang']) / 'bin/clang'
RUNS = []

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(label, argv, cwd=OUT, timeout=120):
    start = time.monotonic()
    result = subprocess.run([str(x) for x in argv], cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    (EVIDENCE / f'{label}.log').write_text(result.stdout)
    RUNS.append({'label': label, 'argv': [str(x) for x in argv],
                 'seconds': round(time.monotonic() - start, 3),
                 'exit': result.returncode})
    if result.returncode:
        raise RuntimeError(f'{label}: exit {result.returncode}\n{result.stdout[-4000:]}')
    print(label, 'PASS', flush=True)
    return result.stdout

def main():
    OUT.mkdir(exist_ok=True)
    EVIDENCE.mkdir(exist_ok=True)
    # An earlier green report must never survive a failed new qualification.
    (EVIDENCE / 'qualification.json').unlink(missing_ok=True)
    inputs = [BASE/'host.scm', BASE/'kernel.bl', BASE/'fixture.bl', BASE/'build.bl',
              BASE/'src/native/scheme.bl', ROOT/'priv/lib/js/actor/runtime.bl',
              BASE/'sdk-pin.json', BASE/'toolchain-pin.json', Path(__file__).resolve()]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    run('build', [BASE/'run', 'run', BASE/'build.bl'], cwd=ROOT, timeout=260)
    scheme = run('scheme', [GAMBIT/'bin/gsi', OUT/'actors.scm'])
    run('scheme-to-c', [GAMBIT/'bin/gsc', '-c', 'actors.scm'])
    run('c-link-unit', [GAMBIT/'bin/gsc', '-link', 'actors.c'])
    units = ['actors', 'actors_']
    flags = ['-O0', '-fwrapv', '-fno-strict-aliasing', '-fPIC',
             '-D___SINGLE_HOST', '-D___TRUST_C_TCO',
             '-D___CAN_IMPORT_CLIB_DYNAMICALLY', '-D___CAN_IMPORT_SETJMP_DYNAMICALLY',
             '-I'+str(GAMBIT/'gambit/include')]
    libs = [str(GAMBIT/'gambit/lib/libgambit.so'), '-lm',
            '-Wl,-rpath,'+str(GAMBIT/'gambit/lib')]
    for name in units:
        run('c-object-'+name, [CLANG, *flags, '-c', name+'.c', '-o', name+'.o'])
    run('c-link', [CLANG, 'actors.o', 'actors_.o', *libs, '-o', 'actors-native'])
    native = run('native', [OUT/'actors-native'])
    for name in units:
        run('llvm-emit-'+name, [CLANG, *flags, '-fno-discard-value-names', '-S', '-emit-llvm', name+'.c', '-o', name+'.ll'])
        run('llvm-object-'+name, [CLANG, '-c', name+'.ll', '-o', name+'-llvm.o'])
    run('llvm-link', [CLANG, 'actors-llvm.o', 'actors_-llvm.o', *libs, '-o', 'actors-llvm'])
    llvm = run('llvm-native', [OUT/'actors-llvm'])
    assert scheme == native == llvm, 'Scheme, C and LLVM programs disagree'
    expected = [line for line in native.splitlines() if line.startswith('PASS ')]
    assert len(expected) == 27 and len(set(expected)) == 27 and 'NATIVE_SEED_ACTORS_OK' in native, native
    assert 'FAIL' not in native
    assert all(digest(ROOT/p) == h for p,h in hashes.items()), 'inputs changed during qualification'
    artifacts = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                 for p in OUT.iterdir() if p.suffix in {'.scm', '.c', '.ll'} or p.name in {'actors-native','actors-llvm'}}
    report = {'status': 'pass', 'scope': 'seed actor subset; virtual time; prebuilt Gambit GC/runtime',
              'self_hosted': False, 'checks': expected, 'inputs': hashes, 'artifacts': artifacts,
              'sdk': json.loads((BASE/'sdk-pin.json').read_text()), 'tools': TOOLS, 'runs': RUNS}
    (EVIDENCE/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'{len(expected)} checks: Scheme → C and LLVM → native agree', flush=True)

if __name__ == '__main__':
    main()
