"""Compile the entire set of missing boot declarations and inspect emitted link requirements."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
from run import BASE, HERE, IMAGE, QUAL, ROOT, command, native_elf, native_module, sexp, sha, write


def run(coverage, out):
    out.mkdir()
    census = json.loads((coverage/'coverage.json').read_text())
    q = json.loads(QUAL.read_text())
    image = IMAGE/'stage2'
    sha(image, q['images']['stage2'])
    if census['image'] != sha(image):
        raise ValueError('Census and selected native image differ')
    bundle = IMAGE/'eval-prepared.scm'
    sha(bundle, q['prepared_macro_bundle_sha256'])
    env = dict(os.environ, BOOT_BUNDLE=str(bundle), BOOT_OUT=str(out))
    cfg = native_elf.configuration(BASE, True, sha)
    order = ['syntax', 'binding', 'expand-source', 'expand', 'lower-core', 'lower', 'optimize']
    expected = {v['namespace'] for k,v in census['files'].items()
                if k.startswith('priv/boot/') and v['after_preparation'].get('missing', 0)}
    if set(order) != expected:
        raise ValueError('Missing namespace set changed')
    report = {}
    generated, objects = [], []
    for ns in order:
        path = 'priv/boot/'+ns+'.bl'
        row = report[ns] = dict(source=sha(ROOT/path,census['files'][path]['source']),
                                 declarations=census['files'][path]['definitions'])
        (out/'modules.scm').write_text(sexp([[ns, path]]))
        log = out/(ns+'.log')
        p = subprocess.run([image,'--eval',HERE/'extend.scm','unused'],cwd=ROOT,env=env,
                           capture_output=True, timeout=120)
        log.write_bytes(p.stdout+p.stderr)
        row['emitted'] = [l.split('\t')[2] for l in log.read_text().splitlines() if l.startswith('EMIT\t')]
        scheme = out/(ns+'.scm')
        if p.returncode:
            row['emission_error'] = log.read_text()[-900:]
            continue
        generated.append([ns,str(scheme)])
        row['scheme'] = sha(scheme)
        if len(row['emitted']) != row['declarations']:
            raise ValueError('Declarations lost in '+ns)
        def cc(label,argv,cwd,build):
            subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=150)
        product = native_module.build_module(out/ns,scheme.read_bytes(),sha(scheme),cfg,cache=out/'objects',
                report={},bind=sha,run=cc,save=lambda:None)['artifacts']['module']
        objects.append([ns,product['path']])
        row['object'] = product['sha256']
        print(ns,len(row['emitted']),'native definitions',flush=True)
    (out/'emitted.scm').write_text(sexp(generated))
    (out/'objects.scm').write_text('()')
    (out/'remotes.scm').write_text('()')
    def inspect(name):
        return command([image,'--eval',HERE/'surface.scm','unused'],env,out/name).splitlines()
    calls, excluded = {}, set()
    for line in inspect('references.log'):
        k, *values = line.split('\t')
        if k == 'unit':
            ns = values[0]
            calls[ns] = Counter()
        if k == 'native-remote':
            calls[ns][values[0]] += 1
        if k == 'excluded':
            excluded.add(values[0])
    refs = sorted(set().union(*(set(v) for v in calls.values())))
    def remote(key):
        module, fn_arity = key.split('/',1)
        fn, arity = fn_arity.rsplit('/',1)
        return [key,module,fn,int(arity)]
    (out/'remotes.scm').write_text(sexp([remote(k) for k in refs]))
    (out/'emitted.scm').write_text('()')
    (out/'objects.scm').write_text(sexp(objects))
    links = {}
    for line in inspect('load.log'):
        k, *values = line.split('\t')
        if k == 'link': links[values[0]] = values[1]
        if k == 'load': report[values[0]]['activation'] = values[1:]
    assert len(links) == len(refs)
    for ns, counts in calls.items():
        report[ns]['literal_remotes'] = dict(counts)
        report[ns]['missing_remotes'] = [k for k in sorted(counts) if links[k]=='absent']
    inventory = set(json.loads((IMAGE/'leaves.json').read_text())['registered_leaves'])
    write(out/'surface.json', dict(image=sha(image),sdk_binding_census=sha(coverage/'coverage.json'),
          units=report, inputs={p:sha(HERE/p) for p in ('surface.py','surface.scm','extend.scm')},
          remote_status=links, excluded_registered=sorted(excluded & inventory),
          registered_leaves=len(inventory), compiler_flags=cfg['flags']))


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('coverage',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    run(a.coverage.resolve(),a.out.resolve())
