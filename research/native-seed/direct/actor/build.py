#!/usr/bin/env python3
"""Admit the captured original C actors; --build compiles only bounded actor units.

No BL, Source parser, actor execution or parent-core rebuild. Run --build in the
integrator's sequential 2 GiB cgroup; each compiler child retains 120 seconds.
"""
from __future__ import annotations
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
from artifacts import Witness, actor_plan, sha


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--cache', type=Path, default=base / 'out/direct-actor-cache')
    parser.add_argument('--compile-timeout', type=int, default=120)
    args = parser.parse_args()
    directory = args.plan.resolve()
    report_path = directory / ('build-evidence.json' if args.build else 'admission.json')
    report_path.unlink(missing_ok=True)
    report = {'schema': 'bl.native.direct-original-actor-build', 'version': 1, 'action-abi': 2,
              'status': 'running', 'builds_requested': args.build, 'builds_launched': False, 'source_parser': False,
              'actor_run': False, 'parent_core_rebuilt': False, 'objects': [], 'runs': []}
    witness = Witness(root)

    def save():
        report['inputs'] = witness.inputs
        report_path.write_text(json.dumps(report, indent=2) + '\n')

    def run(label, argv, work):
        report['builds_launched'] = True
        started = time.monotonic()
        process = subprocess.Popen(argv, cwd=directory, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            output, _ = process.communicate(timeout=args.compile_timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            (work / (label + '.log')).write_text(output)
            raise
        (work / (label + '.log')).write_text(output)
        report['runs'].append({'label': label, 'argv': argv, 'exit': process.returncode,
                              'seconds': round(time.monotonic() - started, 3)})
        save()
        witness.unchanged()
        if process.returncode:
            raise RuntimeError(label + ' failed: ' + output[-3000:])

    try:
        if not 1 <= args.compile_timeout <= 120:
            raise RuntimeError('original C actors retain 120-second compiler child deadlines')
        witness.bind(here)
        witness.bind(here.with_name('artifacts.py'))
        actor = actor_plan(witness, directory)
        report['definitions'] = len(actor['manifest']['emitted-bindings'])
        report['runtime_definitions'] = 202
        if not args.build:
            report['status'] = 'admitted-not-built'
            print('DIRECT_ORIGINAL_ACTORS_ADMITTED; no compiler launched')
            return
        tools_path = base / 'toolchain-pin.json'
        witness.bind(tools_path)
        tools = json.loads(tools_path.read_text())
        gambit, clang = Path(tools['gambit']), Path(tools['clang']) / 'bin/clang'
        gsc, public = gambit / 'bin/gsc', gambit / 'gambit/include/gambit.h'
        build_script, header = gambit / 'gambit/bin/gambuild-C', base / 'direct/native-direct.h'
        for path in (gsc, clang, public, build_script, header):
            witness.bind(path)
        if re.findall(r'^#define BL_NATIVE_DIRECT_ABI ([0-9]+)$', header.read_text(), re.MULTILINE) != ['2']:
            raise RuntimeError('actor builder requires action ABI2 header')
        report.update({'header-action-abi': 2, 'header_sha256': sha(header)})
        defines = re.findall(r'^DEFS_DYN="([^"\n]*)"$', build_script.read_text(), re.MULTILINE)
        expected = ['-D___SINGLE_HOST', '-D___TRUST_C_TCO', '-D___CAN_IMPORT_CLIB_DYNAMICALLY',
                    '-D___CAN_IMPORT_SETJMP_DYNAMICALLY', '-D___DYNAMIC']
        if len(defines) != 1 or '$' in defines[0] or shlex.split(defines[0]) != expected:
            raise RuntimeError('pinned public Gambit dynamic ABI differs')
        flags = ['-O0', '-fwrapv', '-fno-strict-aliasing', '-fno-trapping-math', '-fno-math-errno',
                 '-fPIC', '-fno-common', *expected, '-I' + str(public.parent), '-I' + str(header.parent)]
        environment = hashlib.sha256(json.dumps({k: v for k, v in os.environ.items()
            if k.startswith(('NIX_', 'GAMBIT')) or k in ('PATH', 'CPATH', 'C_INCLUDE_PATH',
                'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'SDKROOT')}, sort_keys=True).encode()).hexdigest()
        report['compiler_environment_sha256'] = environment
        args.cache.mkdir(parents=True, exist_ok=True)
        for unit in [{'name': 'actorhost', 'scmsha': sha(directory / 'actorhost.scm'), 'csha': None}, *actor['units']]:
            name = unit['name']
            source = directory / (name + '.scm')
            key = hashlib.sha256(json.dumps({'action-abi': 2, 'header-action-abi': 2, 'name': name, 'source': unit['scmsha'], 'control': unit['csha'],
                'tools': {str(p): sha(p) for p in (gsc, clang, public, build_script, header)},
                'flags': flags, 'builder': sha(here), 'admission': sha(here.with_name('artifacts.py')),
                'compiler_environment': environment}, sort_keys=True).encode()).hexdigest()
            cache = args.cache.resolve() / key
            cache.mkdir(exist_ok=True)
            raw, adapted = cache / (name + '.c'), cache / (name + '.dynamic.c')
            obj, receipt = cache / (name + '.o1'), cache / 'object.json'
            reused = obj.is_file() and receipt.is_file() and json.loads(receipt.read_text()).get('sha256') == sha(obj)
            if not reused:
                run(name + '-scheme-to-c', [str(gsc), '-c', '-o', str(raw), str(source)], cache)
                text = raw.read_text()
                startup = list(re.finditer(r'^#define ___LINKER_ID ___LNK_' + name + r'$', text, re.MULTILINE))
                if len(startup) != 1:
                    raise RuntimeError('unexpected pinned Gambit startup symbol: ' + name)
                match = startup[0]
                adapted.write_text(text[:match.start()] + '#define ___LINKER_ID ___LNK_' + name + '_2e_o1' + text[match.end():])
                run(name + '-clang', [str(clang), *flags, '-shared', '-rdynamic', str(adapted),
                                     '-ldl', '-lm', '-o', str(obj)], cache)
                receipt.write_text(json.dumps({'action-abi': 2, 'header-action-abi': 2, 'sha256': sha(obj), 'raw_c_sha256': sha(raw),
                    'adapted_c_sha256': sha(adapted), 'startup_from': '___LNK_' + name,
                    'startup_to': '___LNK_' + name + '_2e_o1', 'replacements': 1}, indent=2) + '\n')
            shutil.copy2(obj, directory / (name + '.o1'))
            report['objects'].append({'name': name, 'sha256': sha(obj), 'cache_key': key, 'reused': reused,
                                      'receipt': {'path': str(receipt), 'sha256': sha(receipt)}})
            save()
        witness.unchanged()
        report['status'] = 'built-not-executed'
        print('DIRECT_ORIGINAL_ACTORS_BUILT ' + str(len(actor['units'])) + '; parent core reused; no actor execution')
    except BaseException as error:
        report.update(status='fail', error=str(error))
        raise
    finally:
        report['inputs_after'] = {p: sha(p) if Path(p).is_file() else None for p in witness.inputs}
        save()


if __name__ == '__main__':
    main()
