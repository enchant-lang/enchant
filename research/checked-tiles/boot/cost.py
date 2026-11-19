"""Attribute the existing warm 104-definition native job using separate allocation and sampling runs."""
import argparse
import json
import os
from pathlib import Path
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

    def replace_round(source):
        start=baseline.index('(define (A-timed-round)')
        stop=baseline.index('(define (A-run)',start)
        return baseline[:start]+(HERE/source).read_text()+baseline[stop:]

    def observe(name, source):
        payload=out/(name+'.scm')
        payload.write_text(source)
        log=command([image,'--eval',payload,'unused'],os.environ,out/(name+'.log'))
        assert 'definitions 104 emit-failures 0' in log and 'A3_DONE' in log
        sha(out/'native.scm',gold)
        return log

    allocation=observe('allocation',replace_round('cost-phases.scm'))
    fields=('wall_ms','user_ms','sys_ms','gc_ms','collections','raw_allocator_bytes')
    phases={p:[] for p in ('read','compile','emit')}
    for line in allocation.splitlines():
        if line.startswith('COST '):
            _,phase,*values=line.split()
            assert len(values)==len(fields)
            phases[phase].append(dict(zip(fields,[1000*float(n) for n in values[:4]]+
                                                [int(n) for n in values[4:]])))
    assert all(len(v)==4 for v in phases.values())
    median={p:{k:statistics.median(r[k] for r in rows) for k in fields} for p,rows in phases.items()}

    counted=observe('operations',replace_round('cost-operations.scm').replace('(define A-reps 4)','(define A-reps 1)'))
    calls={}
    for line in counted.splitlines():
        if line.startswith('CALLS '):
            _,phase,*items=line.split()
            calls[phase]={k:int(v) for k,v in (item.split('=') for item in items)}
    assert calls.keys()==phases.keys()
    nodes,=[int(line.split()[1]) for line in counted.splitlines() if line.startswith('ANF_OCCURRENCES ')]
    sdk_pin=json.loads((HERE.parent/'tools.json').read_text())
    sdk=Path(sdk_pin['sdk'])
    sha(sdk/'artifact.json',prior['sdk'])
    flavor=command([sdk/'bin/bl','--cold','eval','(erlang/system_info :emu_flavor)'],
                   dict(os.environ,BL_DAEMON='off',ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'),out/'beam-flavor.log').strip()
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
    inputs={p.name:sha(p) for p in (HERE/'cost.py',HERE/'cost-phases.scm',HERE/'cost-operations.scm',ATTR/'prepare.py',ATTR/'analyze.py',
                                    pipeline/'observer.scm',pipeline/'reader.bl')}
    write(out/'cost.json',dict(image=sha(image),sdk=prior['sdk'],input_bytes=(pipeline/'reader.bl').stat().st_size,
        emitted_sha256=gold,emitted_bytes=(out/'native.scm').stat().st_size,inputs=inputs,
        confirmed_calls=calls,anf_node_occurrences=nodes,beam_emulator=flavor,
        allocator_caveat='Compile-phase byte counter has implausible discontinuities. Do not use the byte field to infer allocation volume or ratios.',
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
