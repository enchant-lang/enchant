"""Strict passive admission for bounded direct actor/compiler artifacts."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

ORIGINAL = '5f2ad8223fd9f053157b65266d3ee14e7fe8567b6196a78ed7ac955132b9a5c5'
HEX = re.compile(r'[0-9a-f]{64}')
BUDGETS = ('default', '17', '41')
ORIGINAL_COMPILER_NAMES = frozenset((
    'anf', 'clojure.core-ext', 'clojure.re', 'clojure.string', 'compiler', 'core', 'diag',
    'host.compiler-data', 'host.form-meta', 'host.meta', 'native.bootstrap', 'native.eval',
    'native.scheme', 'reader', 'reader-node', 'rt', 'server-clause', 'sugar'))
DIRECT_COMPILER_ADDITIONS = (
    'native.c', 'native.c-remote', 'native.c-eval', 'native.c-units', 'native.c-bootstrap')

ZERO = {'procs': 0, 'monitors': 0, 'tables': 0, 'names': 0, 'table_names': 0,
        'runnable': 0, 'input_sink': None, 'critical': 0, 'errors': 0}


CLOCK_MODEL = {"name": "virtual-turn-ms-v1", "tick-ms": 1,
               "event": "completed-host-turn", "idle-progress": "existing-host-wait", "real-time": False}


def validate_native_clock(witness):
    clock = witness.get("clock", {})
    if clock.get("model") != "virtual-turn-ms-v1" or clock.get("tick_ms") != 1:
        raise RuntimeError("native corpus lacks its declared deterministic runnable-progress clock")
    for name in ("completed_turns", "yield_turns", "turn_ms", "elapsed_ms"):
        if type(clock.get(name)) is not int or clock[name] <= 0:
            raise RuntimeError("native corpus clock lacks positive actual " + name)
    if (clock["yield_turns"] > clock["completed_turns"]
            or clock["turn_ms"] != clock["completed_turns"] * clock["tick_ms"]
            or clock["elapsed_ms"] < clock["turn_ms"]):
        raise RuntimeError("native corpus completed/yield turn time progress is inconsistent")
    return clock


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



def compiler_partition(witness, record):
    witness.record(record)
    path = witness.path(record['path'])
    manifest = json.loads(path.read_text())
    if (manifest.get('schema') != 'bl.native.partitioned-closure' or manifest.get('version') != 1
            or not isinstance(manifest.get('units'), list) or not 1 <= len(manifest['units']) <= 256):
        raise RuntimeError('invalid actor compiler partition manifest')
    def part_path(name):
        p = Path(name)
        return p if p.is_absolute() else path.parent / p
    artifact = part_path(manifest['artifact_path'])
    if artifact.stat().st_size > 33554432:
        raise RuntimeError('actor compiler closure exceeds the canonical byte bound')
    witness.bind(artifact, manifest['artifact_sha256'])
    identities = {}
    for row in [manifest['metadata'], *manifest['units']]:
        witness.bind(part_path(row['path']), row['sha256'])
    for row in manifest['units']:
        name = row.get('namespace')
        if (not isinstance(name, str) or name in identities
                or not HEX.fullmatch(row.get('sha256', ''))):
            raise RuntimeError('duplicate or invalid actor compiler namespace identity')
        identities[name] = row['sha256']
    return identities


def actor_plan(witness, directory):
    directory = Path(directory).resolve()
    witness.bind(directory / 'manifest.json')
    manifest = json.loads((directory / 'manifest.json').read_text())
    if (manifest.get('schema') != 'bl.native.direct-original-actor-plan' or manifest.get('version') != 1
            or manifest.get('runtime-definitions') != 202 or manifest.get('group-size') != 32
            or manifest.get('source-interpreter') is not False or manifest.get('anf-interpreter') is not False
            or manifest.get('authored-scheme-bodies') is not False
            or manifest.get('program-control') != 'emitted-c'
            or manifest.get('clock') != 'virtual-turn-ms-v1' or manifest.get('clock-model') != CLOCK_MODEL
            or manifest.get('backend') != 'c' or manifest.get('scheme-body-fallback') != 'forbidden'
            or manifest.get('resolver-schema') != 'bl.native.proc-resolvers'
            or manifest.get('application') != {'path': 'research/js-actors/test.bl', 'sha256': ORIGINAL}):
        raise RuntimeError('not the complete original direct actor plan')
    data = index(witness, directory, actor=True)
    for record in (manifest['application'], manifest['runtime'], manifest['original-manifest'],
                   manifest['original-body'], manifest['original-anf'], manifest['original-link-closure-manifest'],
                   manifest['closure-manifest'],
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
            or original.get('clock-model') != CLOCK_MODEL or original.get('clock') != 'virtual-turn-ms-v1'
            or link['sdk-pin'] != manifest['sdk-pin'] or link['runtime-definitions'] != 202
            or link['source-frames?'] is not True or original['anf'] != manifest['original-anf']
            or original['body'] != manifest['original-body']
            or link['closure-manifest'] != manifest['original-link-closure-manifest']
            or link['emitted-bindings'] != manifest['emitted-bindings']):
        raise RuntimeError('C actor plan changed original Source/capture/SDK identity')
    for record in original['inputs']:
        witness.record(record)
    for record in (link['links'], link['host-link'], *link['host-extensions']):
        witness.record(record)
    original_units = compiler_partition(witness, manifest['original-link-closure-manifest'])
    selected_units = compiler_partition(witness, manifest['closure-manifest'])
    if (len(original_units) != 18 or set(original_units) != ORIGINAL_COMPILER_NAMES):
        raise RuntimeError('actor original link is not its exact eighteen-namespace compiler seed')
    sdk_pin_path = witness.path('research/native-seed/sdk-pin.json')
    sdk_pin_sha256 = witness.bind(sdk_pin_path)
    if json.loads(sdk_pin_path.read_text()) != manifest['sdk-pin']:
        raise RuntimeError('actor compiler profile differs from the pinned SDK map')
    profile = manifest.get('compiler-profile', {})
    if profile.get('version') != 1:
        raise RuntimeError('actor compiler selection lacks its finite profile admission')
    if profile.get('name') == 'native-c-seed-v1':
        if (len(selected_units) != 23
                or set(selected_units) != ORIGINAL_COMPILER_NAMES | set(DIRECT_COMPILER_ADDITIONS)
                or any(selected_units.get(name) != value for name, value in original_units.items())
                or profile.get('added') != list(DIRECT_COMPILER_ADDITIONS)
                or profile.get('scheme-dependencies-preserved') is not True
                or profile.get('sdk-only-producers-excluded') is not True
                or profile.get('parent', {}).get('sdk-pin-sha256') !=
                    sdk_pin_sha256):
            raise RuntimeError('actor C profile changed original units or admitted nonfinite compiler dependencies')
    elif profile.get('name') == 'original-scheme-seed-v1':
        if selected_units != original_units or profile.get('added') != []:
            raise RuntimeError('actor original compiler selection changed its captured seed')
    else:
        raise RuntimeError('unknown actor compiler profile')
    source_order = [r['namespace'] for r in manifest['compiler-sources']]
    original_order = manifest.get('compiler-original-order')
    if (not isinstance(original_order, list) or len(original_order) != 18
            or set(original_order) != ORIGINAL_COMPILER_NAMES
            or len(source_order) != len(selected_units) or set(source_order) != set(selected_units)
            or source_order[:18] != original_order
            or source_order[18:] != profile['added']):
        raise RuntimeError('actor Source index does not cover its complete ordered selected compiler profile')
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
    validate_native_clock(witness)
    if witness.get('budget') != budget or witness.get('cleanup') != ZERO:
        raise RuntimeError('direct C original corpus budget/cleanup differs')
    for key in ('samples', 'deaths', 'max_procs', 'max_monitors', 'max_tables', 'max_links'):
        if not isinstance(witness.get(key), int) or witness[key] <= 0:
            raise RuntimeError('direct C original corpus lacks positive ' + key)
    if not isinstance(steps.get('steps'), int) or steps['steps'] <= 0 or steps.get('core_c') is not True:
        raise RuntimeError('original corpus did not execute actual C control and C core')
    return {'labels': labels, 'traces': traces, 'witness': witness, 'control': steps}
