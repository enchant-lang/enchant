"""Change four hot scalar/byte operations in the original machine image, at fixed C flags."""
import argparse
import json
import os
import subprocess
from pathlib import Path

from field_pipeline import CLOCK, medians, rows
from run import BASE, HERE, IMAGE, QUAL, command, native_elf, native_module, sexp, sha, write


def run(pipeline, out, hygiene=False):
    out.mkdir()
    baseline = json.loads((pipeline/'pipeline.json').read_text())
    qual = json.loads(QUAL.read_text())
    image = IMAGE/'stage2'
    sha(image,qual['images']['stage2'])
    sha(IMAGE/'eval-prepared.scm',qual['prepared_macro_bundle_sha256'])
    sha(pipeline/'reader.bl',baseline['source_sha256'])
    cfg = native_elf.configuration(BASE,True,sha)
    source = HERE/('hygiene-cost.scm' if hygiene else 'primitive-cost.scm')
    def compile_step(label,argv,cwd,build):
        subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=120)
    obj = native_module.build_module(out/'module',source.read_bytes(),sha(source),cfg,cache=out/'objects',
              report={},bind=sha,run=compile_step,save=lambda:None)['artifacts']['module']
    observer = (pipeline/'observer.scm').read_text().replace(sexp(str(pipeline)),sexp(str(out)))
    observer = observer.replace('(define (A-run)',CLOCK+'\n(define (A-run)')
    observer = observer.replace('(A-log "A3_DONE")','(primitive-report!) (A-log "A3_DONE")')
    modes = ['stock','guarded'] if hygiene else ['stock','scalars','bytes','both']
    report = dict(image=sha(image),module=obj['sha256'],module_source=sha(source),
                  source=baseline['source_sha256'], flags=cfg['flags'],runs=[])
    for arm in ['verify',*modes,*reversed(modes)]:
        payload = out/'observer.scm'
        payload.write_text('(load '+sexp(obj['path'])+')\n(primitive-install! '+sexp(arm)+')\n'+observer)
        log = command([image,'--eval',payload,'unused'],os.environ,out/f'{len(report["runs"])}-{arm}.log')
        if 'definitions 104 emit-failures 0' not in log or 'A3_DONE' not in log:
            raise ValueError('Incomplete translation')
        counts = {x.split()[1]:int(x.split()[2]) for x in log.splitlines() if x.startswith('FAST ')}
        if arm=='verify' and (len(counts)!=(2 if hygiene else 4) or min(counts.values())<=0):
            raise ValueError('Unobserved mechanism '+str(counts))
        report['runs'].append(dict(arm=arm,cpu_ms=rows(log,'CPU',1000),wall_ms=rows(log,'WALL',1000),
                     output=sha(out/'native.scm',baseline['runs'][0]['emitted_sha256']),verified=counts))
    report['cpu_medians_ms'] = {a:medians([t for r in report['runs'] if r['arm']==a for t in r['cpu_ms']]) for a in modes}
    write(out/'primitive-cost.json',report)
    print(report['cpu_medians_ms'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--hygiene',action='store_true',help='Test reusing unchanged macro result trees')
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve(),a.hygiene)
