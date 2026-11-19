"""Attribute the existing warm 104-definition native job using separate allocation and sampling runs."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

from run import BASE, HERE, IMAGE, QUAL, command, sexp, sha, write

ATTR = BASE/'speed/attrib'
sys.path.insert(0, str(ATTR))
from prepare import targets


def run(pipeline, out):
    out.mkdir()
    prior = json.loads((pipeline/'pipeline.json').read_text())
    image = IMAGE/'stage2'
    qual = json.loads(QUAL.read_text())
    sha(image,qual['images']['stage2'])
    sha(IMAGE/'eval-prepared.scm',qual['prepared_macro_bundle_sha256'])
    sha(IMAGE/'stage2.scm',qual['stage2_and_stage3_scheme_sha256'])
    assert sha(image)==prior['native_image']
    sha(pipeline/'reader.bl', prior['source_sha256'])
    gold = prior['runs'][0]['emitted_sha256']
    baseline = (pipeline/'observer.scm').read_text().replace(sexp(str(pipeline)),sexp(str(out)))

    def observe(name, source):
        payload=out/(name+'.scm')
        payload.write_text(source)
        log=command([image,'--eval',payload,'unused'],os.environ,out/(name+'.log'))
        assert 'definitions 104 emit-failures 0' in log and 'A3_DONE' in log
        sha(out/'native.scm',gold)
        return log

    start=baseline.index('(define (A-timed-round)')
    stop=baseline.index('(define (A-run)',start)
    allocation=observe('allocation',baseline[:start]+(HERE/'cost-phases.scm').read_text()+baseline[stop:])
    fields=('wall_ms','user_ms','sys_ms','gc_ms','collections','allocated_bytes')
    phases={p:[] for p in ('read','compile','emit')}
    for line in allocation.splitlines():
        if line.startswith('COST '):
            _,phase,*values=line.split()
            assert len(values)==len(fields)
            phases[phase].append(dict(zip(fields,[1000*float(n) for n in values[:4]]+
                                                [int(n) for n in values[4:]])))
    assert all(len(v)==4 for v in phases.values())
    median={p:{k:statistics.median(r[k] for r in rows) for k in fields} for p,rows in phases.items()}

    listing,_=targets(IMAGE/'stage2.scm')
    target_file=out/'targets.scm'
    target_file.write_text(listing)
    sampling=baseline.replace('(define A-timings? #t)','(define A-timings? #f)').replace(
        '(define A-targets-path "unused")','(define A-targets-path '+sexp(str(target_file))+')')
    assert '(define A-counts? #f)' in sampling
    observe('native',sampling)
    subprocess.run([sys.executable,'-B',ATTR/'analyze.py','native',out],check=True,stdout=subprocess.DEVNULL)
    profile=json.loads((out/'native-summary.json').read_text())
    assert all(profile['phases'][p]['samples']>0 for p in phases)
    inputs={p.name:sha(p) for p in (HERE/'cost.py',HERE/'cost-phases.scm',ATTR/'prepare.py',ATTR/'analyze.py',
                                    pipeline/'observer.scm',pipeline/'reader.bl')}
    write(out/'cost.json',dict(image=sha(image),sdk=prior['sdk'],input_bytes=(pipeline/'reader.bl').stat().st_size,
        emitted_sha256=gold,emitted_bytes=(out/'native.scm').stat().st_size,inputs=inputs,
        timings=phases,medians=median,samples={p:{k:v[k] for k in ('samples','host_entry_op','entry_category')}
        for p,v in profile['phases'].items()},allocation_source='Gambit v4.9.5 lib/_repl.scm ##exec-stats',
        scope='Four warm full rounds with per-phase allocator statistics, then a separate four-round stack sample without call wrappers.'))
    for p in phases: print(p,median[p],profile['phases'][p]['host_entry_op'][:5])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    run(args.pipeline.resolve(),args.out.resolve())
