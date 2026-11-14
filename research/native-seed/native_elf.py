"""Shared bounded Scheme-to-native ELF transport; no BL execution or policy.

Callers separately admit canonical Source/SDK manifests and validate their own
runtime witnesses. Only GSI READ/WRITE transport splits the generated program.
"""
import hashlib
import json
import os
from pathlib import Path

TARGET, HARD, DEADLINE = 256 * 1024, 1024 * 1024, 120


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def configuration(base, standard_bindings, bind):
    bind(Path(__file__))
    bind(base / 'toolchain-pin.json')
    tools = json.loads((base / 'toolchain-pin.json').read_text())
    gambit = Path(tools['gambit'])
    gsc, gsi, clang = gambit / 'bin/gsc', gambit / 'bin/gsi', Path(tools['clang']) / 'bin/clang'
    public, library = gambit / 'gambit/include/gambit.h', gambit / 'gambit/lib/libgambit.so'
    splitter = base / 'split-top-level.scm'
    for p in (gsc, gsi, clang, public, library, splitter):
        bind(p)
    flags = ['-O0', '-fwrapv', '-fno-strict-aliasing', '-fPIC', '-pthread', '-D___SINGLE_HOST',
             '-D___TRUST_C_TCO', '-D___CAN_IMPORT_CLIB_DYNAMICALLY',
             '-D___CAN_IMPORT_SETJMP_DYNAMICALLY', '-I' + str(public.parent)]
    link_flags = [str(library), '-pthread', '-ldl', '-lm', '-Wl,-rpath,' + str(library.parent)]
    scheme_flags = (['-prelude', '(declare (standard-bindings) (extended-bindings))']
                    if standard_bindings else [])
    environment = key({k: v for k, v in os.environ.items() if k.startswith(('NIX_', 'GAMBIT'))
                      or k in ('PATH', 'CPATH', 'C_INCLUDE_PATH', 'CPLUS_INCLUDE_PATH', 'LIBRARY_PATH', 'SDKROOT')})
    tool_identity = {'builder_sha256': digest(Path(__file__)), 'tools': {str(p): digest(p) for p in (gsc, gsi, clang, public, library)},
                     'flags': flags, 'link_flags': link_flags, 'scheme_compiler_flags': scheme_flags,
                     'compiler_environment_sha256': environment}
    return {name: value for name, value in locals().items() if name in ('gsc', 'gsi', 'clang', 'public', 'library', 'splitter', 'flags', 'link_flags', 'scheme_flags', 'environment', 'tool_identity')}


def build_native(folder, program, prefix, config, *, cache, reuse_build, standard_bindings,
                 report, bind, path_for, run, save, image_name):
    gsc = config['gsc']
    gsi = config['gsi']
    clang = config['clang']
    public = config['public']
    library = config['library']
    splitter = config['splitter']
    flags = config['flags']
    link_flags = config['link_flags']
    scheme_flags = config['scheme_flags']
    environment = config['environment']
    tool_identity = config['tool_identity']
    if not program.startswith(prefix) or not 0 < len(prefix) <= HARD:
        raise RuntimeError('native program does not retain its bounded frozen host prefix')
    image = folder / image_name
    report['tool_identity'] = tool_identity
    cache_root = cache.resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    tail = folder / 'tail.scm'
    tail.write_bytes(program[len(prefix):])
    host_path = folder / 'ffi-host.scm'
    host_path.write_bytes(prefix)
    split = folder / 'split'
    split.mkdir(exist_ok=True)
    for p in split.glob('forms-*.scm'):
        p.unlink()
    job = folder / 'split.scm'
    job.write_text('(define split-input ' + json.dumps(str(tail)) + ')\n'
        + '(define split-output ' + json.dumps(str(split)) + ')\n'
        + f'(define split-target {TARGET})\n(define split-hard {HARD})\n' + splitter.read_text())
    rows = [{'path': host_path, 'sha256': digest(host_path), 'bytes': len(prefix), 'ordinal': 0}]
    for ordinal, line in enumerate(run('split', [gsi, job]).splitlines(), 1):
        fields = line.split('\t')
        if len(fields) != 5 or fields[0] != 'CHUNK' or fields[1] != f'forms-{ordinal - 1}.scm':
            raise RuntimeError('unexpected bounded splitter output')
        _, name, count, size, oversized = fields
        p = split / name
        if (not count.isdigit() or int(count) < 1 or p.stat().st_size != int(size)
                or not 0 < int(size) <= HARD or oversized not in ('0', '1')
                or (int(size) > TARGET and (int(count) != 1 or oversized != '1'))):
            raise RuntimeError('invalid bounded Scheme unit')
        rows.append({'path': p, 'sha256': digest(p), 'bytes': int(size), 'ordinal': ordinal})
    if len(rows) < 2:
        raise RuntimeError('canonical actor/compiler bodies were not split')
    candidates = {}
    if reuse_build:
        bind(reuse_build)
        parent = json.loads(reuse_build.read_text())
        if (parent.get('schema') != 'bl.native.bounded-build' or parent.get('version') != 1
                or parent.get('status') not in ('stage1-compiled-not-qualified', 'stage1-actors-compiled-not-qualified', 'qualified')
                or parent.get('compile_deadline_seconds') != DEADLINE
                or parent.get('standard_bindings') != standard_bindings
                or parent.get('scheme_compiler_flags') != scheme_flags):
            raise RuntimeError('parent is not a completed compatible bounded native build')
        for p, expected in parent['inputs'].items():
            bind(p, expected)
        for p in (gsc, gsi, clang, public, library):
            if parent['inputs'].get(str(p.resolve())) != digest(p):
                raise RuntimeError('parent tool identity differs')
        for build in parent['builds']:
            for row in build['units']:
                if row.get('c_flags') == flags and row.get('scheme_compiler_flags') == scheme_flags:
                    proof_path = path_for(row['c']).parent / 'scheme-c.json'
                    bind(proof_path)
                    proof = json.loads(proof_path.read_text())
                    if proof.get('request', {}).get('tools', {}).get('compiler_environment_sha256') != environment:
                        raise RuntimeError('parent compiler environment differs')
                    candidates[(row['ordinal'], row['sha256'])] = row
    c_units, objects = [], []
    for row in rows:
        ordinal, source = row['ordinal'], row['path']
        old = candidates.get((ordinal, row['sha256']))
        if old:
            cfile, obj = path_for(old['c']), path_for(old['object'])
            bind(cfile, old['c_sha256'])
            bind(obj, old['object_sha256'])
            reused = True
        else:
            request = {'source_sha256': row['sha256'], 'ordinal': ordinal, 'tools': tool_identity}
            cache = cache_root / key(request)
            cache.mkdir(exist_ok=True)
            stem = f'unit_{ordinal:04d}_{key(request)[:16]}'
            scm, cfile, obj = (cache / (stem + suffix) for suffix in ('.scm', '.c', '.o'))
            proof = cache / 'object.json'
            previous = json.loads(proof.read_text()) if proof.is_file() else {}
            reused = (previous.get('request') == request and cfile.is_file() and obj.is_file()
                      and digest(cfile) == previous.get('c_sha256') and digest(obj) == previous.get('object_sha256'))
            if not reused:
                scm.write_bytes(source.read_bytes())
                run(f'unit-{ordinal:04d}-scheme-to-c', [gsc, '-c', *scheme_flags, '-o', cfile, scm], cwd=cache, build=True)
                run(f'unit-{ordinal:04d}-object', [clang, *flags, '-c', cfile, '-o', obj], cwd=cache, build=True)
                proof.write_text(json.dumps({'request': request, 'c_sha256': digest(cfile), 'object_sha256': digest(obj)}, indent=2) + '\n')
        bind(source, row['sha256'])
        bind(cfile)
        bind(obj)
        c_units.append(cfile)
        objects.append(obj)
        report['units'].append({'ordinal': ordinal, 'source_sha256': row['sha256'],
            'c': {'path': str(cfile), 'sha256': digest(cfile)},
            'object': {'path': str(obj), 'sha256': digest(obj)}, 'reused': reused})
        save()
    link_c, link_o = folder / 'program_.c', folder / 'program_.o'
    run('link-metadata', [gsc, '-link', '-o', link_c, *c_units], build=True)
    run('link-object', [clang, *flags, '-c', link_c, '-o', link_o], build=True)
    run('native-link', [clang, *objects, link_o, *link_flags, '-o', image], build=True)
    report['link_artifacts'] = [{'path': str(p), 'sha256': bind(p)} for p in (link_c, link_o)]
    with image.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            raise RuntimeError('actor image is not a native ELF')
    return image
