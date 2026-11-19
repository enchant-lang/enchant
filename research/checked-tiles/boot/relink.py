"""Relink the exact native compiler, changing Clang policy only on units containing reader functions."""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

from run import HERE,BASE,IMAGE,QUAL,command,sha,write


def run(pipeline,out):
    out.mkdir()
    qual=json.loads(QUAL.read_text())
    sha(IMAGE/'full-fixpoint.json',qual['receipt']['sha256'])
    build=json.loads((IMAGE/'full-native-build.json').read_text())
    stage=next(x for x in build['builds'] if x['stage']=='stage2')
    sha(IMAGE/'stage2',qual['images']['stage2'])
    assert stage['executable_sha256']==qual['images']['stage2']
    link=next(x for x in build['runs'] if x['label']=='stage2-native-link')['argv']
    manifest=Path(stage['split_manifest'])
    sha(manifest,stage['split_manifest_sha256'])
    control=out/'stock'
    subprocess.run(link[:-1]+[control],check=True,timeout=120)
    sha(control,qual['images']['stage2'])
    report=dict(control=sha(control),units=[],runs=[])
    candidate=out/'reader-O1'
    args=link[:-1]+[candidate]
    for u in stage['units']:
        path=manifest.parent/u['file']
        sha(path,u['sha256'])
        sha(u['c'],u['c_sha256'])
        sha(u['object'],u['object_sha256'])
        names=[''.join(chr(int(n)) for n in match[2:].split('_'))
               for match in re.findall(r'^\(define (v_[0-9_]+)(?:\$| )',path.read_text(),re.M)]
        owners=collections.Counter(s.split('/')[0] for s in names)
        if not owners['reader']: continue
        flags=list(u['c_flags'])
        if flags[0]!='-O0': raise ValueError('Different base C flags')
        flags[0]='-O1'
        obj=out/f'reader-{u["ordinal"]}.o'
        start=time.monotonic()
        command([link[0],*flags,'-c',u['c'],'-o',obj],os.environ,out/f'unit-{u["ordinal"]}.log',timeout=120)
        args[args.index(u['object'])]=obj
        report['units'].append(dict(ordinal=u['ordinal'],namespaces=owners,source=sha(path),
                                 c=sha(u['c']),old=u['object_sha256'],new=sha(obj),seconds=time.monotonic()-start))
    if not report['units']: raise ValueError('No reader units selected')
    subprocess.run(args,check=True,timeout=120)
    report['candidate']=sha(candidate)
    reference=json.loads((pipeline/'pipeline.json').read_text())
    source=pipeline/'reader.bl'
    sha(source,reference['source_sha256'])
    obs=(pipeline/'observer.scm').read_text().replace(json.dumps(str(pipeline)),json.dumps(str(out)))
    (out/'observer.scm').write_text(obs)
    for block,order in enumerate([['stock','reader-O1'],['reader-O1','stock']]):
        for name in order:
            log=command([out/name,'--eval',out/'observer.scm',IMAGE/'eval-prepared.scm'],
                        os.environ,out/f'{name}-{block}.log',timeout=120)
            if 'definitions 104 emit-failures 0' not in log: raise ValueError('Incomplete pipeline')
            timings=[[float(s)*1000 for s in line.split()[1:]] for line in log.splitlines() if line.startswith('A3_TIMING ')]
            assert len(timings)==4
            report['runs'].append(dict(name=name,block=block,timings_ms=timings,output=sha(out/'native.scm',reference['runs'][0]['emitted_sha256'])))
    report['medians_ms']={}
    for name in ('stock','reader-O1'):
        ts=[t for row in report['runs'] if row['name']==name for t in row['timings_ms']]
        report['medians_ms'][name]=[statistics.median(k) for k in zip(*ts)]+[statistics.median(map(sum,ts))]
    write(out/'relink.json',report)
    print(report['medians_ms'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve())
