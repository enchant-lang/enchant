"""Finite production-JS artifact admission, independent of native producer paths."""
import json
from pathlib import Path

ORIGINAL = '5f2ad8223fd9f053157b65266d3ee14e7fe8567b6196a78ed7ac955132b9a5c5'
OLD = '838f57ced45ce56776c24729e7703d36f6991c16e9f86270f407161a6328a65c'
FIXED = '5a53fbcb6a88ef939a9c62792c1898ac8b774d0d7b11301a3553ffeacd721bf4'
BUDGETS = ['default', '17', '41']
ZERO = dict(procs=0, monitors=0, tables=0, names=0, table_names=0,
            runnable=0, input_sink=None, critical=0, errors=0)
CLOCK_MODEL = {'name': 'virtual-turn-ms-v1', 'tick-ms': 1, 'event': 'completed-host-turn',
               'idle-progress': 'existing-host-wait', 'real-time': False}


def admit(path, bind, path_for, *, application):
    bind(Path(__file__))
    bind(path)
    manifest = json.loads(path.read_text())
    def identity(row):
        return bind(path_for(row['path']), row['sha256'])
    if (manifest.get('schema') != 'bl.native.original-actor-corpus' or manifest.get('version') != 1
            or manifest.get('target') != 'javascript' or manifest.get('application') != application
            or manifest.get('assertion-adaptation') != 'none' or manifest.get('source-path-adaptation') != 'none'
            or manifest.get('runtime', {}).get('path') != 'priv/lib/js/actor/runtime.bl'):
        raise RuntimeError('not an unadapted original production-JS Source capture')
    for row in [manifest['application'], manifest['runtime'], manifest['artifact'], manifest['host'],
                manifest['graph-parent'], manifest['graph-qualification'], *manifest['inputs'],
                *manifest['assets'], *manifest['graph-assets']]:
        identity(row)
    pin = manifest['sdk-pin']
    bind(Path(pin['sdk']) / 'artifact.json', pin['descriptor_sha256'])
    producer = manifest['producer']
    if (producer.get('schema') != 'bl.native.production-js-capsule' or producer.get('version') != 1
            or producer.get('sdk-pin') != pin or producer.get('members') != ['write-bundle!/4', 'build-one/5']
            or producer.get('logical-namespace') != 'js.actor' or producer.get('evaluation') != 'canonical-anonymous-eval'
            or producer.get('namespace-publication') is not False or producer.get('generated-output-adaptation') != 'none'
            or producer.get('sole-source-delta') != 'named-ENV-import'
            or producer.get('source') != {'path': 'priv/lib/js/actor.bl', 'sha256': FIXED}
            or producer.get('sdk-source') != {'path': str(Path(pin['source']) / 'priv/lib/js/actor.bl'), 'sha256': OLD}):
        raise RuntimeError('JS producer was not the exact Source-owned private canonical capsule')
    aliases = [['pserver', 'proc.server'], ['server-clause', 'server-clause'], ['psuper', 'proc.super'],
               ['native', 'system.js'], ['ir', 'system.ir'], ['sync', 'js.emit'], ['rn', 'reader-node'],
               ['jsbuild', 'js.build'], ['facade', 'bl.js'], ['json', 'bl.json'],
               ['regex', 'clojure.re'], ['string', 'clojure.string']]
    if (producer.get('alias-authority') != 'canonical-original-namespace-header'
            or producer.get('alias-scope') != 'private-fork' or producer.get('aliases') != aliases
            or producer.get('outer-aliases-preserved') is not True or producer.get('provider-loading') != 'normal-retained-sdk'
            or [row.get('namespace') for row in producer.get('providers', [])] != [row[1] for row in aliases]):
        raise RuntimeError('private producer did not restore every exact original namespace alias')
    for row in producer['providers']:
        identity(row['source'])
        identity(row['sdk-source'])
        if (not path_for(row['sdk-source']['path']).is_relative_to(Path(pin['source']))
                or row['source']['sha256'] != row['sdk-source']['sha256']):
            raise RuntimeError('capsule alias provider differs from its immutable qualified SDK Source')
    identity(producer['source'])
    identity(producer['sdk-source'])
    identity(producer['sdk-provider'])
    if producer['sdk-provider']['sha256'] != OLD:
        raise RuntimeError('patched workspace namespace was loaded instead of the unchanged SDK provider')
    old = path_for(producer['sdk-source']['path']).read_text()
    current = path_for(producer['source']['path']).read_text()
    if (old.count('"import * as E_ from "') != 1
            or current != old.replace('"import * as E_ from "', '"import { ENV as E_ } from "')):
        raise RuntimeError('producer differs from immutable SDK Source beyond the reviewed import')
    parent_path = path_for(manifest['graph-parent']['path'])
    parent = json.loads(parent_path.read_text())
    proof = json.loads(path_for(manifest['graph-qualification']['path']).read_text())
    if (parent.get('sdk-pin') != pin or parent.get('target') != 'javascript'
            or proof.get('schema') != 'bl.native.original-actor-qualification' or proof.get('status') != 'pass'
            or proof.get('sdk') != pin or proof.get('original_actor_corpus_qualified') is not True
            or proof['inputs'].get(str(parent_path)) != manifest['graph-parent']['sha256']):
        raise RuntimeError('reused canonical JS graph lacks its historical exact qualification')
    graph = parent_path.parent / 'canonical'
    selected = [row for row in parent['assets'] if path_for(row['path']).is_relative_to(graph)]
    if len(selected) != 21 or manifest['graph-assets'] != selected:
        raise RuntimeError('canonical graph asset selection differs from the admitted graph')
    for row in selected:
        if proof['inputs'].get(str(path_for(row['path']))) != row['sha256']:
            raise RuntimeError('canonical graph asset was not in its qualified parent')
    dependencies_path = graph / 'dependencies.json'
    bind(dependencies_path)
    dependencies = json.loads(dependencies_path.read_text())
    if (dependencies.get('schema') != 'bl.js.dependencies' or dependencies.get('version') != 1
            or dependencies.get('entry') != 'core' or len(dependencies.get('namespaces', {})) != 6):
        raise RuntimeError('canonical production core graph contract differs')
    for spec in dependencies['namespaces'].values():
        bind(path_for(spec['path']), spec['source-sha256'])
    if not any(row['path'] == 'research/native-seed/src/native/js-producer.bl' for row in manifest['inputs']):
        raise RuntimeError('private producer capture Source is not bound')
    # Ordinary namespace modules and the actor writer must share this ABI.
    artifact = path_for(manifest['artifact']['path']).read_text()
    if 'import { ENV as E_ } from ' not in artifact or 'import * as E_ from ' in artifact:
        raise RuntimeError('production actor output still imports the wrong Env ABI')
    return manifest


def observe(text, budget):
    lines = text.splitlines()
    if 'js-actors: ALL PASS' not in lines or any(line.startswith(('FAIL ', 'SKIP ')) for line in lines):
        raise RuntimeError('original JS acceptance driver failed or skipped')
    labels = [line[5:] for line in lines if line.startswith('PASS ')]
    if len(labels) != 461 or len(set(labels)) != 461:
        raise RuntimeError('original JS corpus omitted/duplicated an assertion')
    traces = [line for line in lines if line.startswith(('EXIT-PARITY ', 'SUP-PARITY ', 'SUP-TRACE '))]
    if [sum(line.startswith(prefix + ' ') for line in traces) for prefix in
            ('EXIT-PARITY', 'SUP-PARITY', 'SUP-TRACE')] != [11, 10, 2]:
        raise RuntimeError('original JS lifecycle/supervision trace is incomplete')
    prefix = 'JS_CORPUS_WITNESS '
    witnesses = [json.loads(line[len(prefix):]) for line in lines if line.startswith(prefix)]
    if len(witnesses) != 1 or not lines[-1].startswith(prefix):
        raise RuntimeError('original JS corpus lacks its unique final witness')
    witness = witnesses[0]
    if witness.get('budget') != budget or witness.get('cleanup') != ZERO:
        raise RuntimeError('original JS corpus budget/cleanup differs')
    if any(type(witness.get(key)) is not int or witness[key] <= 0 for key in
           ('samples', 'deaths', 'max_procs', 'max_monitors', 'max_tables', 'max_links')):
        raise RuntimeError('original JS corpus lacks positive lifecycle observations')
    return {'labels': labels, 'traces': traces, 'witness': witness}
