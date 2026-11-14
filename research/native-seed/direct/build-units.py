#!/usr/bin/env python3
"""Admit bounded C units by fixed TSV, optionally build them one at a time.

Never launches BL, parses Scheme/Source, or runs the emitted compiler. Run
--build only under the integrator's existing 2 GiB sequential cgroup.
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
    value = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--cache', type=Path, default=base / 'out/direct-unit-cache')
    parser.add_argument('--compile-timeout', type=int, default=120)
    parser.add_argument('--route', choices=('c', 'llvm'), default='c')
    parser.add_argument('--standard-bindings', action='store_true')
    args = parser.parse_args()
    out = args.plan.resolve()
    report_path = out / 'build-evidence.json'
    report_path.unlink(missing_ok=True)
    report = {'schema': 'bl.native.direct-unit-build', 'version': 1, 'status': 'running',
              'source_parser': False, 'compiler_run': False, 'runs': [], 'objects': [],
              'route': args.route, 'standard_bindings': args.standard_bindings}
    inputs = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        value = sha(path)
        if expected is not None and value != expected:
            raise RuntimeError('unit input hash mismatch: ' + str(path))
        if str(path) in inputs and inputs[str(path)] != value:
            raise RuntimeError('unit input changed during admission: ' + str(path))
        inputs[str(path)] = value
        return value

    def save():
        report['inputs'] = inputs
        report_path.write_text(json.dumps(report, indent=2) + '\n')

    def unchanged():
        for path, value in inputs.items():
            if not Path(path).is_file() or sha(path) != value:
                raise RuntimeError('bounded unit input changed: ' + path)

    def run(label, argv, directory):
        started = time.monotonic()
        process = subprocess.Popen(argv, cwd=out, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
        try:
            output, _ = process.communicate(timeout=args.compile_timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            output, _ = process.communicate()
            (directory / (label + '.log')).write_text(output)
            raise
        (directory / (label + '.log')).write_text(output)
        report['runs'].append({'label': label, 'argv': argv, 'exit': process.returncode,
                              'seconds': round(time.monotonic() - started, 3)})
        save()
        unchanged()
        if process.returncode:
            raise RuntimeError(label + ' failed: ' + output[-3000:])

    try:
        bind(here)
        if not 1 <= args.compile_timeout <= 120:
            raise RuntimeError('bounded units retain the existing 120-second compiler deadline')
        index = out / 'index.tsv'
        bind(index)
        rows = index.read_text(encoding='ascii').splitlines()
        if not rows or rows[0] != 'BL_NATIVE_DIRECT_UNITS\t1\t32':
            raise RuntimeError('unsupported direct compiler index schema')
        units, singleton, definitions = [], {}, {}
        phase = 'functions'
        digest_pattern = re.compile(r'[0-9a-f]{64}')
        for line in rows[1:]:
            fields = line.split('\t')
            kind = fields[0]
            if kind in ('H', 'M', 'E', 'A', 'P'):
                expected_length = 4 if kind == 'H' else 3
                if len(fields) != expected_length or kind in singleton:
                    raise RuntimeError('duplicate/malformed singleton index row')
                expected_file = {'H': 'host.scm', 'M': 'metadata.scm', 'E': 'entry.scm',
                                 'A': 'assembly.scm', 'P': 'plan.manifest.scm'}[kind]
                if fields[1] != expected_file or not digest_pattern.fullmatch(fields[2]):
                    raise RuntimeError('invalid fixed index file/hash')
                bind(out / fields[1], fields[2])
                singleton[kind] = fields
            elif kind == 'S':
                if len(fields) != 4 or not fields[1].isdigit() or not all(digest_pattern.fullmatch(v) for v in fields[2:]):
                    raise RuntimeError('invalid source identity index row')
            elif kind == 'U':
                if len(fields) != 9:
                    raise RuntimeError('malformed unit index row')
                _, next_phase, name, cfile, csha, scmfile, scmsha, count, namesha = fields
                if (next_phase not in ('functions', 'initializers') or (phase == 'initializers' and next_phase != phase)
                        or not re.fullmatch(r'u[0-9]{4}', name) or name in definitions
                        or cfile != name + '.c' or scmfile != name + '.scm'
                        or not count.isdigit() or not 1 <= int(count) <= 32
                        or not all(digest_pattern.fullmatch(v) for v in (csha, scmsha, namesha))):
                    raise RuntimeError('invalid unit phase/name/size/hash')
                phase = next_phase
                bind(out / cfile, csha)
                bind(out / scmfile, scmsha)
                control = (out / cfile).read_text()
                declaration = '(c-declare ' + json.dumps(control, ensure_ascii=False) + ')'
                if (out / scmfile).read_text().count(declaration) != 1:
                    raise RuntimeError('unit FFI does not contain its exact C declaration once')
                units.append({'name': name, 'phase': phase, 'source': out / scmfile,
                              'control': out / cfile, 'count': int(count)})
                definitions[name] = []
            elif kind == 'D':
                if (len(fields) != 5 or not units or fields[1] != units[-1]['name']
                        or fields[2] != str(len(definitions[fields[1]]))
                        or not all(digest_pattern.fullmatch(v) for v in fields[3:])):
                    raise RuntimeError('invalid definition order/body/binding digest row')
                definitions[fields[1]].append(fields[3:])
            else:
                raise RuntimeError('unknown compiler index row: ' + kind)
        if set(singleton) != {'H', 'M', 'E', 'A', 'P'} or not units or units[0]['phase'] != 'functions':
            raise RuntimeError('incomplete compiler assembly index')
        if rows[-1].split('\t')[0] != 'P':
            raise RuntimeError('portable manifest digest must close the index')
        for unit in units:
            if len(definitions[unit['name']]) != unit['count']:
                raise RuntimeError('definition count differs from unit index')
        expected_entry = '(native-main (native-command-line))\n'
        if (out / 'entry.scm').read_text() != expected_entry:
            raise RuntimeError('closed compiler command-line entry changed')
        expected_assembly = (';; Direct C compiler: relative link entries; unit root is explicit.\n'
            '(define native-direct-unit-root (getenv "BL_NATIVE_C_UNIT_ROOT" #f))\n'
            '(if (not native-direct-unit-root) (error "BL_NATIVE_C_UNIT_ROOT is required"))\n'
            '(load (string-append native-direct-unit-root "/host.o1"))\n'
            '(native-install-bundle! ' + (out / 'metadata.scm').read_text() + ')\n'
            '(set! native-c-backend (bl-key "c"))\n' + ''.join(
                '(load (string-append native-direct-unit-root "/' + u['name'] + '.o1"))\n' for u in units) + expected_entry)
        if (out / 'assembly.scm').read_text() != expected_assembly:
            raise RuntimeError('assembly differs from exact host/metadata/functions/initializer/entry order')
        report['units'] = [{'name': u['name'], 'phase': u['phase'], 'count': u['count']} for u in units]
        if not args.build:
            report['status'] = 'admitted-not-built'
            print('DIRECT_UNITS_ADMITTED ' + str(len(units)) + '; no compiler launched')
            return
        tools_path = base / 'toolchain-pin.json'
        bind(tools_path)
        tools = json.loads(tools_path.read_text())
        gambit, clang = Path(tools['gambit']), Path(tools['clang']) / 'bin/clang'
        public = gambit / 'gambit/include/gambit.h'
        header = base / 'direct/native-direct.h'
        build_script = gambit / 'gambit/bin/gambuild-C'
        compiler_tools = (gambit / 'bin/gsc', clang, public, header, build_script)
        for path in compiler_tools:
            bind(path)
        tool_hashes = {str(path.resolve()): sha(path) for path in compiler_tools}
        matches = re.findall(r'^DEFS_DYN="([^"\n]*)"$', build_script.read_text(), re.MULTILINE)
        if len(matches) != 1 or '$' in matches[0]:
            raise RuntimeError('nonliteral public Gambit dynamic ABI')
        defines = shlex.split(matches[0])
        if defines != ['-D___SINGLE_HOST', '-D___TRUST_C_TCO', '-D___CAN_IMPORT_CLIB_DYNAMICALLY',
                       '-D___CAN_IMPORT_SETJMP_DYNAMICALLY', '-D___DYNAMIC']:
            raise RuntimeError('public Gambit dynamic ABI changed')
        flags = ['-O0', '-fwrapv', '-fno-strict-aliasing', '-fno-trapping-math', '-fno-math-errno',
                 '-fPIC', '-fno-common', *defines, '-I' + str(public.parent), '-I' + str(header.parent)]
        gsc_flags = ['-prelude', '(declare (standard-bindings) (extended-bindings))'] if args.standard_bindings else []
        llvm_object_flags = ['-O0', '-fPIC']
        report.update(c_flags=flags, scheme_compiler_flags=gsc_flags, llvm_object_flags=llvm_object_flags)
        compiler_environment = hashlib.sha256(json.dumps({name: value for name, value in os.environ.items()
            if name.startswith(('NIX_', 'GAMBIT')) or name in
            ('PATH', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'SDKROOT')}, sort_keys=True).encode()).hexdigest()
        report['compiler_environment_sha256'] = compiler_environment
        args.cache.mkdir(parents=True, exist_ok=True)
        for unit in [{'name': 'host', 'source': out / 'host.scm', 'control': None}, *units]:
            name = unit['name']
            request = {'name': name, 'source': sha(unit['source']),
                'control': sha(unit['control']) if unit['control'] else None,
                'host': inputs[str((out / 'host.scm').resolve())], 'flags': flags,
                'route': args.route, 'gsc_flags': gsc_flags, 'llvm_object_flags': llvm_object_flags,
                'builder': sha(here), 'public_build_script': sha(build_script),
                'compiler_environment': compiler_environment,
                'gambit': str(gambit), 'clang': str(clang), 'public': sha(public), 'header': sha(header),
                'tool_hashes': tool_hashes}
            key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
            cache = args.cache.resolve() / key
            cache.mkdir(exist_ok=True)
            obj = cache / (name + '.o1')
            raw, adapted = cache / (name + '.c'), cache / (name + '.dynamic.c')
            receipt = cache / 'object.json'
            previous = json.loads(receipt.read_text()) if receipt.is_file() else {}
            reused = (previous.get('request') == request and obj.is_file()
                      and previous.get('sha256') == sha(obj) and previous.get('route') == args.route
                      and raw.is_file() and previous.get('raw_c_sha256') == sha(raw)
                      and adapted.is_file() and previous.get('adapted_c_sha256') == sha(adapted))
            if reused and args.route == 'llvm':
                reused = all(Path(r['path']).is_file() and sha(r['path']) == r['sha256']
                             for r in previous.get('llvm_artifacts', [])) and len(previous.get('llvm_artifacts', [])) == 2
            if not reused:
                run(name + '-scheme-to-c', [str(gambit / 'bin/gsc'), '-c', *gsc_flags, '-o', str(raw), str(unit['source'])], cache)
                text = raw.read_text()
                startup = list(re.finditer(r'^#define ___LINKER_ID ([^\s]+)[ \t]*$', text, re.MULTILINE))
                if len(startup) != 1 or startup[0].group(1) != '___LNK_' + name:
                    raise RuntimeError('unexpected unique raw startup symbol: ' + name)
                if unit['control'] and text.count(unit['control'].read_text()) != 1:
                    raise RuntimeError('GSC altered/duplicated direct C control')
                match = startup[0]
                adapted.write_text(text[:match.start()] + '#define ___LINKER_ID ___LNK_' + name + '_2e_o1' + text[match.end():])
                llvm_artifacts = []
                if args.route == 'llvm':
                    ir, llvm_object = cache / (name + '.ll'), cache / (name + '.llvm.o')
                    run(name + '-emit-llvm', [str(clang), *flags, '-S', '-emit-llvm', str(adapted), '-o', str(ir)], cache)
                    run(name + '-llvm-object', [str(clang), *llvm_object_flags, '-c', str(ir), '-o', str(llvm_object)], cache)
                    run(name + '-llvm-shared', [str(clang), '-shared', '-rdynamic', str(llvm_object), '-ldl', '-lm', '-o', str(obj)], cache)
                    llvm_artifacts = [{'path': str(p), 'sha256': sha(p)} for p in (ir, llvm_object)]
                else:
                    run(name + '-clang', [str(clang), *flags, '-shared', '-rdynamic', str(adapted), '-ldl', '-lm', '-o', str(obj)], cache)
                receipt.write_text(json.dumps({'request': request, 'sha256': sha(obj), 'raw_c_sha256': sha(raw),
                    'adapted_c_sha256': sha(adapted), 'startup_from': '___LNK_' + name,
                    'startup_to': '___LNK_' + name + '_2e_o1', 'replacements': 1,
                    'route': args.route, 'llvm_artifacts': llvm_artifacts}, indent=2) + '\n')
            shutil.copy2(obj, out / (name + '.o1'))
            details = json.loads(receipt.read_text())
            c_artifacts = [{'path': str(p), 'sha256': bind(p)} for p in (raw, adapted)]
            bind(obj, details['sha256'])
            bind(receipt)
            for artifact in details.get('llvm_artifacts', []):
                bind(artifact['path'], artifact['sha256'])
            report['objects'].append({'name': name, 'sha256': sha(obj), 'cache_key': key, 'reused': reused,
                'route': args.route, 'receipt': {'path': str(receipt), 'sha256': sha(receipt)},
                'c_artifacts': c_artifacts, 'llvm_artifacts': details.get('llvm_artifacts', [])})
            save()
        # Only this tiny load/link entry is an executable TU. Every authored
        # compiler function is already an actual C-control dynamic unit above.
        executable_flags = [value for value in flags if value != '-D___DYNAMIC'] + ['-pthread']
        runtime = gambit / 'gambit/lib/libgambit.so'
        bind(runtime)
        executable_request = {'assembly': sha(out / 'assembly.scm'),
            'objects': [{'name': row['name'], 'sha256': row['sha256']} for row in report['objects']],
            'builder': sha(here), 'flags': executable_flags,
            'route': args.route, 'gsc_flags': gsc_flags, 'llvm_object_flags': llvm_object_flags,
            'compiler_environment': compiler_environment,
            'runtime': sha(runtime), 'gambit': str(gambit), 'clang': str(clang), 'tool_hashes': tool_hashes}
        executable_key = hashlib.sha256(json.dumps(executable_request, sort_keys=True).encode()).hexdigest()
        directory = args.cache.resolve() / executable_key
        directory.mkdir(exist_ok=True)
        entry_c, entry_o = directory / 'assembly.c', directory / 'assembly.o'
        link_c, link_o = directory / 'program_.c', directory / 'program_.o'
        executable, receipt = directory / 'compiler', directory / 'executable.json'
        previous = json.loads(receipt.read_text()) if receipt.is_file() else {}
        reused = (previous.get('request') == executable_request and executable.is_file()
                  and previous.get('sha256') == sha(executable) and previous.get('route') == args.route
                  and len(previous.get('c_artifacts', [])) == 4
                  and all(Path(r['path']).is_file() and sha(r['path']) == r['sha256']
                          for r in previous.get('c_artifacts', [])))
        if reused and args.route == 'llvm':
            reused = all(Path(r['path']).is_file() and sha(r['path']) == r['sha256']
                         for r in previous.get('llvm_artifacts', [])) and len(previous.get('llvm_artifacts', [])) == 4
        if not reused:
            run('entry-scheme-to-c', [str(gambit / 'bin/gsc'), '-c', *gsc_flags, '-o', str(entry_c), str(out / 'assembly.scm')], directory)
            llvm_artifacts = []
            if args.route == 'llvm':
                entry_ir = directory / 'assembly.ll'
                run('entry-emit-llvm', [str(clang), *executable_flags, '-S', '-emit-llvm', str(entry_c), '-o', str(entry_ir)], directory)
                run('entry-llvm-object', [str(clang), *llvm_object_flags, '-c', str(entry_ir), '-o', str(entry_o)], directory)
                llvm_artifacts.extend({'path': str(p), 'sha256': sha(p)} for p in (entry_ir, entry_o))
            else:
                run('entry-object', [str(clang), *executable_flags, '-c', str(entry_c), '-o', str(entry_o)], directory)
            run('entry-link-unit', [str(gambit / 'bin/gsc'), '-link', '-o', str(link_c), str(entry_c)], directory)
            if args.route == 'llvm':
                link_ir = directory / 'program_.ll'
                run('link-emit-llvm', [str(clang), *executable_flags, '-S', '-emit-llvm', str(link_c), '-o', str(link_ir)], directory)
                run('link-llvm-object', [str(clang), *llvm_object_flags, '-c', str(link_ir), '-o', str(link_o)], directory)
                llvm_artifacts.extend({'path': str(p), 'sha256': sha(p)} for p in (link_ir, link_o))
            else:
                run('entry-link-object', [str(clang), *executable_flags, '-c', str(link_c), '-o', str(link_o)], directory)
            run('entry-executable', [str(clang), str(entry_o), str(link_o), str(runtime), '-pthread', '-ldl', '-lm',
                '-Wl,-rpath,' + str(runtime.parent), '-o', str(executable)], directory)
            receipt.write_text(json.dumps({'request': executable_request, 'sha256': sha(executable), 'route': args.route,
                'c_artifacts': [{'path': str(p), 'sha256': sha(p)} for p in (entry_c, entry_o, link_c, link_o)],
                'llvm_artifacts': llvm_artifacts}, indent=2) + '\n')
        details = json.loads(receipt.read_text())
        bind(executable, details['sha256'])
        bind(receipt)
        for artifact in details['c_artifacts'] + details.get('llvm_artifacts', []):
            bind(artifact['path'], artifact['sha256'])
        shutil.copy2(executable, out / 'compiler')
        report['executable'] = {'sha256': sha(executable), 'cache_key': executable_key, 'reused': reused,
                                'unit_root_environment': 'BL_NATIVE_C_UNIT_ROOT', 'route': args.route,
                                'receipt': {'path': str(receipt), 'sha256': sha(receipt)},
                                'c_artifacts': details['c_artifacts'],
                                'llvm_artifacts': details.get('llvm_artifacts', [])}
        unchanged()
        report['status'] = 'built-not-executed'
        print('DIRECT_UNITS_BUILT ' + str(len(units)) + '; host compiled once; no compiler program run')
    except BaseException as error:
        report.update({'status': 'fail', 'error': str(error)})
        raise
    finally:
        report['inputs_after'] = {path: sha(path) if Path(path).is_file() else None for path in inputs}
        save()


if __name__ == '__main__':
    main()
