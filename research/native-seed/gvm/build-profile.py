#!/usr/bin/env python3
"""Build one hash-admitted GVM compiler plan; reuse exact immutable objects.

No Source is parsed here. Only bootstrap/data metadata is decoded, and every
authored body reaches the pinned GVM backend as inert DATA. Jobs are serial.
"""
import argparse
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parents[1]
HEX = re.compile(r'[0-9a-f]{64}')
FLAGS = runpy.run_path(str(BASE / 'gvm/build-module.py'))['FLAGS']
DECODE = runpy.run_path(str(BASE / 'gvm/read-metadata.py'))['decode']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def record(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha(path)}


def admit(directory):
    manifest = directory / 'plan.manifest.scm'
    plan = DECODE(manifest.read_text())
    if (plan.get('schema') != 'bl.native.gvm-compiler-units' or plan.get('version') != 1
            or plan.get('runtime-abi') != 1 or plan.get('group-size') != 32):
        raise ValueError('not the bounded GVM compiler plan')
    if (directory / 'plan.json').exists() and json.loads((directory / 'plan.json').read_text()) != plan:
        raise ValueError('SDK JSON and owned metadata projections differ')
    lines = (directory / 'index.tsv').read_text(encoding='ascii').splitlines()
    if lines[:2] != ['BL_NATIVE_GVM_UNITS\t1\t32', 'B\t1']:
        raise ValueError('unsupported compiler index')
    files, single, unit_rows, source_rows = {}, {}, [], []

    def bind(name, expected):
        if not HEX.fullmatch(expected) or sha(directory / name) != expected:
            raise ValueError('compiler artifact hash differs: ' + name)
        files[name] = expected

    phase = 'functions'
    for line in lines[2:]:
        row = line.split('\t')
        kind = row[0]
        if kind in ('H', 'M', 'E', 'A', 'P'):
            name = {'H': 'host.scm', 'M': 'metadata.scm', 'E': 'entry.scm',
                    'A': 'assembly.scm', 'P': 'plan.manifest.scm'}[kind]
            if kind in single or len(row) != (4 if kind == 'H' else 3) or row[1] != name:
                raise ValueError('invalid fixed compiler artifact')
            bind(name, row[2])
            single[kind] = row
        elif kind == 'S':
            if len(row) != 4 or row[1] != str(len(source_rows)) or not all(HEX.fullmatch(s) for s in row[2:]):
                raise ValueError('invalid Source identity row')
            source_rows.append(row)
        elif kind == 'U':
            if len(row) != 10:
                raise ValueError('invalid GVM unit row')
            _, new_phase, name, module, data, data_sha, metadata, metadata_sha, count, names_sha = row
            if (new_phase not in ('functions', 'initializers')
                    or (phase == 'initializers' and new_phase != phase)
                    or name != 'u' + str(len(unit_rows)).zfill(4)
                    or module != 'native_gvm_' + name or data != name + '.gvm-data'
                    or metadata != name + '.manifest.scm' or not count.isdigit()
                    or not 1 <= int(count) <= 32 or not HEX.fullmatch(names_sha)):
                raise ValueError('invalid bounded GVM identity/order')
            bind(data, data_sha)
            bind(metadata, metadata_sha)
            phase = new_phase
            unit_rows.append(row)
        else:
            raise ValueError('unknown GVM compiler index record')
    if set(single) != {'H', 'M', 'E', 'A', 'P'} or not unit_rows or not source_rows or lines[-1].split('\t')[0] != 'P':
        raise ValueError('incomplete GVM compiler plan')
    if len(unit_rows) != len(plan['units']) or len(source_rows) != len(plan['sources']):
        raise ValueError('manifest/index unit or Source count differs')
    for row, unit in zip(unit_rows, plan['units']):
        expected = ['U', unit['phase'], unit['name'], unit['module'], unit['data']['path'],
                    unit['data']['sha256'], unit['manifest']['path'], unit['manifest']['sha256'],
                    str(unit['definition-count'])]
        if row[:9] != expected or unit['definition-count'] != len(unit['definitions']):
            raise ValueError('manifest/index definition group differs')
        emission = DECODE((directory / unit['manifest']['path']).read_text())
        if emission != unit['emission'] or emission.get('module') != unit['module'] or emission.get('runtime-abi') != 1:
            raise ValueError('GVM emission identity differs')
        if any(emission.get(flag) is not False for flag in
               ('authored-scheme', 'source-interpreter', 'anf-interpreter', 'gvm-interpreter', 'c-lambda-stepper')):
            raise ValueError('GVM unit has an unadmitted executable representation')
    if (directory / 'entry.scm').read_text() != '(native-main (native-command-line))\n':
        raise ValueError('native command entry differs')
    files['index.tsv'] = sha(directory / 'index.tsv')
    return plan, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--cache', type=Path, default=ROOT / '.local/native-gvm-build-cache')
    args = parser.parse_args()
    source, out, cache = (p.resolve() for p in (args.plan, args.out, args.cache))
    if out.exists():
        parser.error('choose a fresh runtime output directory')
    plan, files = admit(source)
    out.mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)
    for route in ('c', 'llvm'):
        (out / route).mkdir()
    tools = json.loads((BASE / 'toolchain-pin.json').read_text())
    gambit, clang = Path(tools['gambit']), str(Path(tools['clang']) / 'bin/clang')
    gsc, runtime = str(gambit / 'bin/gsc'), gambit / 'gambit/lib/libgambit.so'
    environment = key({k: v for k, v in os.environ.items()
                       if k in ('PATH', 'LD_LIBRARY_PATH') or k.startswith('NIX_')})
    report = {'schema': 'bl.native.gvm-profile-build', 'version': 1, 'status': 'building',
              'qualification': False, 'plan': str(source), 'semantic_files': files,
              'inputs': {str(BASE / 'gvm/build-profile.py'): sha(__file__),
                         str(BASE / 'gvm/build-module.py'): sha(BASE / 'gvm/build-module.py'),
                         str(BASE / 'gvm/read-metadata.py'): sha(BASE / 'gvm/read-metadata.py')},
              'tools': tools, 'compiler_environment_sha256': environment,
              'child_deadline_seconds': 120, 'jobs': [], 'modules': []}

    def save():
        (out / 'build.json').write_text(json.dumps(report, indent=2) + '\n')

    def run(name, argv, cwd, timeout=120):
        log = out / (name + '.log')
        row = {'name': name, 'argv': list(map(str, argv)), 'deadline_seconds': timeout}
        report['jobs'].append(row)
        start = time.monotonic()
        save()
        try:
            with log.open('w') as stream:
                result = subprocess.run(argv, cwd=cwd, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=timeout)
            row.update(returncode=result.returncode, seconds=time.monotonic() - start)
            if result.returncode:
                raise RuntimeError(name + ' failed: ' + str(log))
        except subprocess.TimeoutExpired:
            row.update(status='timeout', seconds=time.monotonic() - start)
            raise
        finally:
            save()

    # Remaining build phases share this exact pinned recipe and serial runner.
    build_profile(source, out, cache, plan, report, tools, gambit, clang, gsc,
                  runtime, environment, run, save)


def build_profile(source, out, cache, plan, report, tools, gambit, clang, gsc,
                  runtime, environment, run, save):
    def cached(directory, request):
        receipt = directory / 'receipt.json'
        if not receipt.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return None
        value = json.loads(receipt.read_text())
        if value['request'] != request or any(sha(p) != h for p, h in value['artifacts'].items()):
            raise RuntimeError('immutable native object cache differs: ' + str(directory))
        return value

    def seal(directory, request, paths):
        value = {'request': request, 'artifacts': {str(p): sha(p) for p in paths}}
        (directory / 'receipt.json').write_text(json.dumps(value, indent=2) + '\n')
        return value

    lock = (cache / 'writer.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        host_request = {'source': sha(source / 'host.scm'), 'tools': tools, 'flags': FLAGS,
                        'environment': environment, 'runtime': sha(runtime),
                        'recipe': hashlib.sha256(inspect.getsource(compile_host).encode()).hexdigest()}
        host_dir = cache / 'hosts' / key(host_request)
        host_value = cached(host_dir, host_request)
        host_reused = host_value is not None
        if host_value is None:
            paths = compile_host(source / 'host.scm', host_dir, gambit, clang, gsc, run)
            host_value = seal(host_dir, host_request, paths)
        for route, src in [('c', host_dir / 'host.o1'), ('llvm', host_dir / 'llvm/host.o1')]:
            shutil.copy2(src, out / route / 'host.o1')
        report['host'] = {'source': record(source / 'host.scm'),
                          'c': record(out / 'c/host.o1'), 'llvm': record(out / 'llvm/host.o1'),
                          'receipt': record(host_dir / 'receipt.json'), 'reused': host_reused}
        save()
        for index, unit in enumerate(plan['units']):
            data = source / unit['data']['path']
            request = {'data': sha(data), 'name': unit['module'], 'tools': tools,
                       'environment': environment, 'builder': sha(BASE / 'gvm/build-module.py'),
                       'importer': sha(BASE / 'gvm/import.scm'), 'route': 'both', 'flags': FLAGS}
            directory = cache / 'units' / key(request)
            value = cached(directory, request)
            reused = value is not None
            if value is None:
                run('unit-' + unit['name'], [sys.executable, str(BASE / 'gvm/build-module.py'),
                    str(data), str(directory), '--name', unit['module']], ROOT, timeout=480)
                built = json.loads((directory / 'build.json').read_text())
                if built['status'] != 'compiled-not-qualified' or len(built['jobs']) != 4:
                    raise RuntimeError('GVM module build did not finish every native compiler phase')
                paths = [Path(p) for p in built['artifacts']] + [directory / 'build.json']
                value = seal(directory, request, paths)
            for route, src in [('c', directory / unit['object']),
                               ('llvm', directory / 'llvm' / unit['object'])]:
                shutil.copy2(src, out / route / unit['object'])
            report['modules'].append({'name': unit['name'], 'module': unit['module'],
                'data': record(data), 'emission': record(source / unit['manifest']['path']),
                'build': record(directory / 'build.json'), 'receipt': record(directory / 'receipt.json'),
                'c': record(directory / (unit['module'] + '.c')),
                'native': record(out / 'c' / unit['object']),
                'llvm': record(out / 'llvm' / unit['object']), 'reused': reused})
            save()
            print('GVM_BUILD_UNIT', index + 1, '/', len(plan['units']), unit['module'],
                  'reused' if reused else 'compiled', flush=True)
        entry_request = {'assembly': sha(source / 'assembly.scm'), 'tools': tools,
                         'environment': environment, 'flags': FLAGS, 'runtime': sha(runtime),
                         'recipe': hashlib.sha256(inspect.getsource(compile_entry).encode()).hexdigest()}
        entry_dir = cache / 'entries' / key(entry_request)
        entry_value = cached(entry_dir, entry_request)
        entry_reused = entry_value is not None
        if entry_value is None:
            paths = compile_entry(source / 'assembly.scm', entry_dir, gambit, clang, gsc, runtime, run)
            entry_value = seal(entry_dir, entry_request, paths)
        report['executables'] = {}
        for route in ('c', 'llvm'):
            shutil.copy2(entry_dir / route / 'compiler', out / route / 'compiler')
            report['executables'][route] = record(out / route / 'compiler')
        report['entry'] = {'receipt': record(entry_dir / 'receipt.json'), 'reused': entry_reused}
        report['status'] = 'compiled-not-qualified'
        print('NATIVE_GVM_PROFILE_C_AND_LLVM_COMPILED', len(plan['units']), flush=True)
    except BaseException as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        save()
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def compile_host(source, directory, gambit, clang, gsc, run):
    raw, adapted = directory / 'host.c', directory / 'host.dynamic.c'
    run('host-gsc', [gsc, '-c', '-prelude', '(declare (standard-bindings) (extended-bindings))',
                     '-o', str(raw), str(source)], directory)
    text = raw.read_text()
    matches = list(re.finditer(r'^#define ___LINKER_ID ([^\s]+)[ \t]*$', text, re.MULTILINE))
    if len(matches) != 1:
        raise RuntimeError('host C lacks a unique dynamic linker identity')
    match = matches[0]
    adapted.write_text(text[:match.start()] + '#define ___LINKER_ID ___LNK_host_2e_o1' + text[match.end():])
    (directory / 'llvm').mkdir(exist_ok=True)
    common = [clang, *FLAGS, '-I' + str(gambit / 'gambit/include')]
    obj, ir, llvm_obj = directory / 'host.o1', directory / 'llvm/host.ll', directory / 'llvm/host.o1'
    run('host-c', [*common, '-shared', '-rdynamic', str(adapted), '-ldl', '-lm', '-o', str(obj)], directory)
    run('host-llvm-ir', [*common, '-S', '-emit-llvm', str(adapted), '-o', str(ir)], directory)
    run('host-llvm-link', [clang, '-O1', '-fPIC', '-shared', '-rdynamic', str(ir),
                          '-ldl', '-lm', '-o', str(llvm_obj)], directory)
    return [raw, adapted, obj, ir, llvm_obj]


def compile_entry(source, directory, gambit, clang, gsc, runtime, run):
    entry_c, link_c = directory / 'assembly.c', directory / 'program_.c'
    run('entry-gsc', [gsc, '-c', '-prelude', '(declare (standard-bindings) (extended-bindings))',
                      '-o', str(entry_c), str(source)], directory)
    run('entry-link-gsc', [gsc, '-link', '-o', str(link_c), str(entry_c)], directory)
    flags = [f for f in FLAGS if f != '-D___DYNAMIC']
    flags += ['-pthread', '-I' + str(gambit / 'gambit/include')]
    artifacts = [entry_c, link_c]
    for route in ('c', 'llvm'):
        selected = directory / route
        selected.mkdir(exist_ok=True)
        objects = []
        for name, cfile in [('assembly', entry_c), ('program_', link_c)]:
            obj = selected / (name + '.o')
            if route == 'llvm':
                ir = selected / (name + '.ll')
                run('entry-' + route + '-' + name + '-ir',
                    [clang, *flags, '-S', '-emit-llvm', str(cfile), '-o', str(ir)], directory)
                run('entry-' + route + '-' + name + '-object',
                    [clang, '-O1', '-fPIC', '-c', str(ir), '-o', str(obj)], directory)
                artifacts.append(ir)
            else:
                run('entry-' + route + '-' + name + '-object',
                    [clang, *flags, '-c', str(cfile), '-o', str(obj)], directory)
            artifacts.append(obj)
            objects.append(str(obj))
        executable = selected / 'compiler'
        run('entry-' + route + '-elf', [clang, *objects, str(runtime), '-pthread', '-ldl', '-lm',
             '-Wl,-rpath,' + str(runtime.parent), '-o', str(executable)], directory)
        artifacts.append(executable)
    return artifacts


if __name__ == '__main__':
    main()
