"""Strict passive admission for bounded direct actor/compiler artifacts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

ORIGINAL = '5f2ad8223fd9f053157b65266d3ee14e7fe8567b6196a78ed7ac955132b9a5c5'
HEX = re.compile(r'[0-9a-f]{64}')
BUDGETS = ('default', '17', '41')
ZERO = {'procs': 0, 'monitors': 0, 'tables': 0, 'names': 0, 'table_names': 0,
        'runnable': 0, 'input_sink': None, 'critical': 0, 'errors': 0}


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


class Witness:
    def __init__(self, root):
        self.root, self.inputs = Path(root).resolve(), {}

    def path(self, path):
        p = Path(path)
        return p.resolve() if p.is_absolute() else (self.root / p).resolve()

    def bind(self, path, expected=None):
        path = self.path(path)
        actual = sha(path)
        if expected is not None and actual != expected:
            raise RuntimeError('artifact identity differs: ' + str(path))
        if str(path) in self.inputs and self.inputs[str(path)] != actual:
            raise RuntimeError('input changed during admission: ' + str(path))
        self.inputs[str(path)] = actual
        return actual

    def record(self, record):
        return self.bind(record['path'], record['sha256'])

    def unchanged(self):
        for name, expected in self.inputs.items():
            if not Path(name).is_file() or sha(name) != expected:
                raise RuntimeError('qualification input changed: ' + name)


def index(witness, directory, actor=False):
    directory = Path(directory).resolve()
    witness.bind(directory / 'index.tsv')
    lines = (directory / 'index.tsv').read_text(encoding='ascii').splitlines()
    expected = 'BL_NATIVE_DIRECT_ACTORS\t1\t32' if actor else 'BL_NATIVE_DIRECT_UNITS\t1\t32'
    if not lines or lines[0] != expected:
        raise RuntimeError('unsupported bounded index: ' + str(directory))
    singles, units, sources, phase = {}, [], [], 'functions'
    for line in lines[1:]:
        row = line.split('\t')
        kind = row[0]
        if kind in ('H', 'M', 'E', 'A', 'P'):
            names = {'H': 'actorhost.scm' if actor else 'host.scm', 'M': 'metadata.scm',
                     'E': 'entry.scm', 'A': 'assembly.scm', 'P': 'plan.manifest.scm'}
            length = 4 if kind == 'H' and not actor else 3
            if len(row) != length or kind in singles or row[1] != names[kind] or not HEX.fullmatch(row[2]):
                raise RuntimeError('invalid bounded singleton row')
            witness.bind(directory / row[1], row[2])
            singles[kind] = row
        elif kind == 'S' and not actor:
            if (len(row) != 4 or row[1] != str(len(sources))
                    or not all(HEX.fullmatch(x) for x in row[2:])):
                raise RuntimeError('invalid original compiler source row')
            sources.append(row)
        elif kind == 'U':
            if len(row) != 9:
                raise RuntimeError('malformed bounded unit row')
            _, newphase, name, cfile, csha, scmfile, scmsha, count, recordsha = row
            pattern = r'a[0-9]{4}' if actor else r'u[0-9]{4}'
            if (newphase not in ('functions', 'initializers')
                    or (phase == 'initializers' and newphase != phase)
                    or not re.fullmatch(pattern, name) or any(x['name'] == name for x in units)
                    or cfile != name + '.c' or scmfile != name + '.scm'
                    or not count.isdigit() or not 1 <= int(count) <= 32
                    or not all(HEX.fullmatch(x) for x in (csha, scmsha, recordsha))):
                raise RuntimeError('invalid bounded unit identity/phase/size')
            phase = newphase
            witness.bind(directory / cfile, csha)
            witness.bind(directory / scmfile, scmsha)
            ctext = (directory / cfile).read_text()
            exact = '(c-declare ' + json.dumps(ctext, ensure_ascii=False) + ')'
            if (directory / scmfile).read_text().count(exact) != 1:
                raise RuntimeError('FFI wrapper does not contain exact C control once')
            units.append({'name': name, 'phase': phase, 'count': int(count), 'csha': csha,
                          'scmsha': scmsha, 'recordsha': recordsha, 'definitions': []})
        elif kind == 'D':
            if (len(row) != 5 or not units or row[1] != units[-1]['name']
                    or row[2] != str(len(units[-1]['definitions']))
                    or not all(HEX.fullmatch(x) for x in row[3:])):
                raise RuntimeError('invalid bounded original definition row')
            units[-1]['definitions'].append(row[3:])
        else:
            raise RuntimeError('unknown bounded index row: ' + kind)
    required = {'H', 'E', 'P'} if actor else {'H', 'M', 'E', 'A', 'P'}
    if (set(singles) != required or not units or units[0]['phase'] != 'functions'
            or lines[-1].split('\t')[0] != 'P'):
        raise RuntimeError('incomplete bounded artifact set')
    if any(len(x['definitions']) != x['count'] for x in units):
        raise RuntimeError('bounded original definition counts differ')
    return {'directory': directory, 'singletons': singles, 'units': units, 'sources': sources}


def actor_plan(witness, directory):
    directory = Path(directory).resolve()
    witness.bind(directory / 'manifest.json')
    manifest = json.loads((directory / 'manifest.json').read_text())
    if (manifest.get('schema') != 'bl.native.direct-original-actor-plan' or manifest.get('version') != 1
            or manifest.get('runtime-definitions') != 202 or manifest.get('group-size') != 32
            or manifest.get('source-interpreter') is not False or manifest.get('anf-interpreter') is not False
            or manifest.get('authored-scheme-bodies') is not False
            or manifest.get('program-control') != 'emitted-c'
            or manifest.get('backend') != 'c' or manifest.get('scheme-body-fallback') != 'forbidden'
            or manifest.get('resolver-schema') != 'bl.native.proc-resolvers'
            or manifest.get('application') != {'path': 'research/js-actors/test.bl', 'sha256': ORIGINAL}):
        raise RuntimeError('not the complete original direct actor plan')
    data = index(witness, directory, actor=True)
    for record in (manifest['application'], manifest['runtime'], manifest['original-manifest'],
                   manifest['original-body'], manifest['original-anf'], manifest['closure-manifest'],
                   *manifest['host-inputs']):
        witness.record(record)
    if any(r['path'].endswith('/direct-control-frames.scm') for r in manifest['host-inputs']):
        raise RuntimeError('source control frames belong to the compiled host exactly once')
    guards = [r for r in manifest['host-inputs'] if r['path'].endswith('/direct/actor/direct-actor-no-fallback.scm')]
    if len(guards) != 1:
        raise RuntimeError('direct actor host lacks its explicit no-Scheme-fallback guard')
    host_prefix = b'\n'.join(witness.path(r['path']).read_bytes() for r in manifest['host-inputs']) + b'\n'
    if not (directory / 'actorhost.scm').read_bytes().startswith(host_prefix):
        raise RuntimeError('compiled actor host does not preserve its exact component/guard order')
    original = json.loads(witness.path(manifest['original-manifest']['path']).read_text())
    link = original['link']
    if (original.get('schema') != 'bl.native.original-actor-corpus' or original.get('target') != 'scheme'
            or original.get('assertion-adaptation') != 'none' or original.get('source-path-adaptation') != 'none'
            or original['application'] != manifest['application'] or original['runtime'] != manifest['runtime']
            or link['sdk-pin'] != manifest['sdk-pin'] or link['runtime-definitions'] != 202
            or link['source-frames?'] is not True or original['anf'] != manifest['original-anf']
            or original['body'] != manifest['original-body']
            or link['emitted-bindings'] != manifest['emitted-bindings']):
        raise RuntimeError('C actor plan changed original Source/capture/SDK identity')
    for record in original['inputs']:
        witness.record(record)
    for record in (link['links'], link['host-link'], *link['host-extensions']):
        witness.record(record)
    partition = json.loads(witness.path(manifest['closure-manifest']['path']).read_text())
    for record in [partition['metadata'], *partition['units']]:
        p = Path(record['path'])
        if not p.is_absolute():
            p = witness.path(manifest['closure-manifest']['path']).parent / p
        witness.bind(p, record['sha256'])
    if len(data['units']) != len(manifest['units']):
        raise RuntimeError('actor plan/index unit counts differ')
    bindings = []
    for actual, declared in zip(data['units'], manifest['units']):
        if (actual['name'] != declared['name'] or actual['phase'] != declared['phase']
                or actual['count'] != declared['definition-count']
                or actual['csha'] != declared['c']['sha256'] or actual['scmsha'] != declared['ffi']['sha256']
                or actual['recordsha'] != declared['definitions-sha256']
                or declared['emission']['program-control'] != 'emitted-c'):
            raise RuntimeError('actor C unit differs from captured plan')
        for expected, definition in zip(actual['definitions'], declared['definitions']):
            if expected != [definition['body-sha256'], definition['binding-sha256']]:
                raise RuntimeError('actor original ANF/body order differs')
            bindings.append(definition['namespace'] + '/' + definition['name'])
    if bindings != manifest['emitted-bindings']:
        raise RuntimeError('original C actor bindings were omitted or reordered')
    data['manifest'] = manifest
    return data


def compiler_stage(witness, directory, actor):
    data = index(witness, directory)
    expected = [['S', str(i), r['sha256'], r['binding-sha256']]
                for i, r in enumerate(actor['manifest']['compiler-sources'])]
    if (data['sources'] != expected
            or data['singletons']['M'][2] != actor['manifest']['compiler-metadata-sha256']):
        raise RuntimeError('actor capture and compiler stage do not share exact original Source/core/metadata')
    witness.bind(Path(directory) / 'build-evidence.json')
    build = json.loads((Path(directory) / 'build-evidence.json').read_text())
    if build.get('status') != 'built-not-executed' or build.get('compiler_run') is not False:
        raise RuntimeError('compiler stage was not admitted/built by the bounded C builder')
    expected_names = ['host', *[u['name'] for u in data['units']]]
    if [x['name'] for x in build['objects']] != expected_names:
        raise RuntimeError('compiled parent object order differs')
    for row in build['objects']:
        witness.bind(Path(directory) / (row['name'] + '.o1'), row['sha256'])
    for name, expected_sha in build['inputs'].items():
        witness.bind(name, expected_sha)
    route = build.get('route', 'c')
    if route not in ('c', 'llvm'):
        raise RuntimeError('unknown compiled parent route')
    data['route'] = route
    if (Path(directory) / 'entry.scm').read_text() != '(native-main (native-command-line))\n':
        raise RuntimeError('parent compiler exact command-line entry changed')
    return data


def observe(text, budget):
    lines = text.splitlines()
    labels = [line[5:] for line in lines if line.startswith('PASS ')]
    traces = [line for line in lines if line.startswith(('EXIT-PARITY ', 'SUP-PARITY ', 'SUP-TRACE '))]
    final = [line for line in lines if line.startswith('NATIVE_CORPUS_WITNESS ')]
    control = [line for line in lines if line.startswith('DIRECT_C_CORPUS_CONTROL ')]
    if ('js-actors: ALL PASS' not in lines or any(line.startswith('FAIL ') for line in lines)
            or len(labels) < 461 or len(set(labels)) != len(labels)
            or [sum(x.startswith(prefix) for x in traces) for prefix in
                ('EXIT-PARITY ', 'SUP-PARITY ', 'SUP-TRACE ')] != [11, 10, 2]
            or len(final) != 1 or lines[-1] != final[0] or len(control) != 1):
        raise RuntimeError('direct C original corpus output is incomplete')
    witness = json.loads(final[0].split(' ', 1)[1])
    steps = json.loads(control[0].split(' ', 1)[1])
    if witness.get('budget') != budget or witness.get('cleanup') != ZERO:
        raise RuntimeError('direct C original corpus budget/cleanup differs')
    for key in ('samples', 'deaths', 'max_procs', 'max_monitors', 'max_tables', 'max_links'):
        if not isinstance(witness.get(key), int) or witness[key] <= 0:
            raise RuntimeError('direct C original corpus lacks positive ' + key)
    if not isinstance(steps.get('steps'), int) or steps['steps'] <= 0 or steps.get('core_c') is not True:
        raise RuntimeError('original corpus did not execute actual C control and C core')
    return {'labels': labels, 'traces': traces, 'witness': witness, 'control': steps}
