"""Exercise source-derived reader fast paths inside the real native image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess

from run import HERE,BASE,IMAGE,ROOT,QUAL,command,native_elf,native_module,sexp,sha,write


def run(session,pipeline,out):
    out.mkdir()
    receipt=json.loads((session/'reader.json').read_text())
    baseline=json.loads((pipeline/'pipeline.json').read_text())
    q=json.loads(QUAL.read_text())
    image=IMAGE/'stage2'
    sha(image,q['images']['stage2'])
    src=ROOT/'priv/boot/reader.bl'
    pinned='0a62a19fbdc7e02d2fb79a0b92eedd2123a97d4890c78d5513e694353bba4f6e'
    sha(src,pinned)
    providers=json.loads((IMAGE/'identity.json').read_text())['providers']
    assert any(r['path']=='priv/boot/reader.bl' and r['sha256']==pinned for r in providers)
    assert not receipt['smoke'] and receipt['qualified_image']==sha(image)==baseline['native_image']
    cfg=native_elf.configuration(BASE,True,sha)
    cfg['flags'][0]='-O2'
    cfg['tool_identity']['flags']=cfg['flags']
    source=HERE/'region.scm'
    def cc(label,argv,cwd,build):
        subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=120)
    product=native_module.build_module(out/'module',source.read_bytes(),sha(source),cfg,cache=out/'objects',
           report={},bind=sha,run=cc,save=lambda:None)['artifacts']['module']
    env=dict(os.environ,BOOT_REGION=product['path'],BOOT_BASE=str(session),BOOT_OUT=str(out),
             BOOT_WIRE=str(HERE/'wire.scm'),BOOT_OBSERVATIONS=str(HERE/'observations.scm'))
    def native(observer,log):
        return command([image,'--eval',observer,'unused'],env,out/log,timeout=300)
    checks=native(HERE/'region-control.scm','controls.log')
    jobs=json.loads((session/'jobs.json').read_text())
    for job,old in zip(jobs,receipt['rows'],strict=True):
        sha(job['path'],old['source_sha256'])
    files=[[r['path'],r['label']] for r in jobs if r['mode']=='read' and r['label'].startswith('priv/boot/')]
    assert len(files)==17
    (out/'boot.scm').write_text(sexp(files))
    read=native(HERE/'region-read.scm','boot.log')
    witnesses={j['id']:sha(out/(j['id']+'.wire'),row['native_wire']) for j,row in zip(jobs,receipt['rows'],strict=True)}
    times={}
    for line in read.splitlines():
        parts=line.split()
        if parts[0]=='BOOT': times.setdefault(parts[2],[]).append(float(parts[3])/1000)
        if parts[0]=='COUNTS': counts=list(map(int,parts[1:]))
    if not all(n>0 for n in counts): raise ValueError('Compiled calls did not reach the measured arity cells')
    report=dict(inputs={p.name:sha(p) for p in [source,src,HERE/'region-read.scm',HERE/'region-control.scm']},
                module=product['sha256'],image=sha(image),checks=checks,typed_witnesses=witnesses,
                token_calls=counts[0],skip_calls=counts[1],identity_skip_calls=counts[2],boot_ms=times,pipeline=[])
    for block,order in enumerate([['stock','both'],['both','stock']]):
        for mode in order:
            observer=out/'observer.scm'
            template=(pipeline/'observer.scm').read_text().replace(json.dumps(str(pipeline)),json.dumps(str(out)))
            observer.write_text('(load (getenv "BOOT_REGION"))\n(region-mode! "'+mode+'")\n'+template)
            log=native(observer,f'{mode}-{block}.log')
            ts=[[float(v)*1000 for v in line.split()[1:]] for line in log.splitlines() if line.startswith('A3_TIMING ')]
            assert len(ts)==4 and 'definitions 104 emit-failures 0' in log
            report['pipeline'].append(dict(mode=mode,timings_ms=ts,
                    sha256=sha(out/'native.scm',baseline['runs'][0]['emitted_sha256'])))
    write(out/'regions.json',report)
    print({k:statistics.median(ts) for k,ts in times.items()},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('reader_session',type=Path)
    p.add_argument('pipeline_session',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    run(a.reader_session.resolve(),a.pipeline_session.resolve(),a.out.resolve())
