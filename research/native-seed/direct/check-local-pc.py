#!/usr/bin/env python3
"""Compile one tiny C boundary probe; no BL, Source or ANF execution.

Run inside the integrator's sequential native-build memory wrapper. Children
retain120s compilation/30s execution ceilings. Both O0 and O1 use C and LLVM.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, default=base / 'fixtures')
    parser.add_argument('--optimization', choices=('0', '1', 'both'), default='both')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    receipt = out / 'qualification.json'
    if receipt.exists():
        raise RuntimeError('retain prior PC observations; select a fresh output directory')
    report = {'schema': 'bl.native.c-local-pc-boundary-qualification', 'version': 1,
              'status': 'running', 'scope': 'fixed C action boundary ABI only',
              'source_interpreter': False, 'anf_interpreter': False, 'source_executed': False,
              'compiler_fixpoint': False, 'actor_corpus': False, 'independent_runtime': False,
              'action-abi': 2, 'runs': [], 'results': {}}
    inputs = {}

    def bind(path):
        path = Path(path).resolve()
        value = sha(path)
        if str(path) in inputs and value != inputs[str(path)]:
            raise RuntimeError('PC probe input changed: ' + str(path))
        inputs[str(path)] = value
        return value

    def save():
        report['inputs'] = inputs
        receipt.write_text(json.dumps(report, indent=2) + '\n')

    def unchanged():
        for path, value in inputs.items():
            if not Path(path).is_file() or sha(path) != value:
                raise RuntimeError('PC probe input changed: ' + path)

    def run(label, argv, timeout, directory):
        start = time.monotonic()
        process = subprocess.Popen([str(x) for x in argv], cwd=directory, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            text, _ = process.communicate(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            text, _ = process.communicate()
            (out / (label + '.log')).write_text(text)
            raise
        log = out / (label + '.log')
        log.write_text(text)
        report['runs'].append({'label': label, 'argv': [str(x) for x in argv], 'exit': process.returncode,
            'seconds': round(time.monotonic() - start, 3), 'log': {'path': str(log), 'sha256': sha(log)}})
        save()
        unchanged()
        if process.returncode:
            raise RuntimeError(label + ': ' + text[-3000:])
        return text

    try:
        tools_path = base / 'toolchain-pin.json'
        bind(here)
        bind(tools_path)
        tools = json.loads(tools_path.read_text())
        gambit = Path(tools['gambit'])
        gsc, gsi = gambit / 'bin/gsc', gambit / 'bin/gsi'
        clang = Path(tools['clang']) / 'bin/clang'
        public, build_script = gambit / 'gambit/include/gambit.h', gambit / 'gambit/bin/gambuild-C'
        header = base / 'direct/native-direct.h'
        scm_source = args.fixtures.resolve() / 'pc-boundary-check.scm'
        c_source = args.fixtures.resolve() / 'pc-boundary-probe.c'
        for path in (gsc, gsi, clang, public, build_script, header, scm_source, c_source):
            bind(path)
        if ('#define BL_NATIVE_DIRECT_ABI 2\n' not in header.read_text()
                or '#define BLC_YIELD(m,kind)' not in header.read_text()):
            raise RuntimeError('PC probe requires the actual local-PC ABI2 header')
        declarations = re.findall(r'^DEFS_DYN="([^"\n]*)"$', build_script.read_text(), re.MULTILINE)
        expected = ['-D___SINGLE_HOST', '-D___TRUST_C_TCO', '-D___CAN_IMPORT_CLIB_DYNAMICALLY',
                    '-D___CAN_IMPORT_SETJMP_DYNAMICALLY', '-D___DYNAMIC']
        if len(declarations) != 1 or '$' in declarations[0] or shlex.split(declarations[0]) != expected:
            raise RuntimeError('PC probe public Gambit dynamic ABI changed')
        scm, c = out / 'pcprobe.scm', out / 'pc-boundary-probe.c'
        shutil.copy2(scm_source, scm)
        shutil.copy2(c_source, c)
        bind(scm)
        bind(c)
        raw, adapted = out / 'pcprobe.c', out / 'pcprobe.dynamic.c'
        run('scheme-to-c', [gsc, '-c', '-o', raw, scm], 120, out)
        text = raw.read_text()
        matches = list(re.finditer(r'^#define ___LINKER_ID ___LNK_pcprobe$', text, re.MULTILINE))
        if len(matches) != 1:
            raise RuntimeError('PC probe unexpected GSC startup symbol')
        match = matches[0]
        adapted.write_text(text[:match.start()] + '#define ___LINKER_ID ___LNK_pcprobe_2e_o1' + text[match.end():])
        bind(raw)
        bind(adapted)
        report['startup_adapter'] = {'from': '___LNK_pcprobe', 'to': '___LNK_pcprobe_2e_o1', 'replacements': 1}
        optimizations = ('0', '1') if args.optimization == 'both' else (args.optimization,)
        for optimization in optimizations:
            flags = ['-O' + optimization, '-fwrapv', '-fno-strict-aliasing', '-fno-trapping-math',
                     '-fno-math-errno', '-fPIC', '-fno-common', *expected,
                     '-I' + str(public.parent), '-I' + str(header.parent), '-I' + str(out)]
            for route in ('c', 'llvm'):
                name = 'o' + optimization + '-' + route
                directory = out / name
                directory.mkdir()
                obj = directory / 'pcprobe.o1'
                if route == 'c':
                    run(name + '-compile', [clang, *flags, '-shared', '-rdynamic', adapted,
                                          '-ldl', '-lm', '-o', obj], 120, out)
                else:
                    ir, llvm_object = directory / 'pcprobe.ll', directory / 'pcprobe.llvm.o'
                    run(name + '-ir', [clang, *flags, '-S', '-emit-llvm', adapted, '-o', ir], 120, out)
                    run(name + '-object', [clang, '-O' + optimization, '-fPIC', '-c', ir, '-o', llvm_object], 120, out)
                    run(name + '-link', [clang, '-shared', '-rdynamic', llvm_object, '-ldl', '-lm', '-o', obj], 120, out)
                    bind(ir)
                    bind(llvm_object)
                bind(obj)
                entry = directory / 'run.scm'
                entry.write_text('(load ' + json.dumps(str(obj)) + ')\n')
                bind(entry)
                output = run(name + '-run', [gsi, entry], 30, out)
                if output.splitlines() != ['NATIVE_C_LOCAL_PC_BOUNDARIES_PASS 153']:
                    raise RuntimeError(name + ': PC probe transcript differs: ' + output[-2000:])
                report['results'][name] = {'checks': 153, 'c_flags': flags, 'object_sha256': sha(obj),
                                          'all_action_and_pc_snapshots_equal': True}
                save()
        unchanged()
        report['status'] = 'pass'
        print('NATIVE_C_LOCAL_PC_BOUNDARIES_QUALIFIED ' + str(len(report['results'])) + ' C/LLVM optimization routes')
    except BaseException as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['inputs_after'] = {path: sha(path) if Path(path).is_file() else None for path in inputs}
        save()


if __name__ == '__main__':
    main()
