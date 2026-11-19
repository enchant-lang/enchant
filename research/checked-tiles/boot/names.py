"""Time removal of repeated compiler name work within one actual compilation."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
from run import BASE, HERE, IMAGE, QUAL, command, native_elf, native_module, sha, write


def run(pipeline, out):
    out.mkdir()
    baseline = json.loads((pipeline/'pipeline.json').read_text())
    image = IMAGE/'stage2'
    sha(image,json.loads(QUAL.read_text())['images']['stage2'])
    assert sha(image)==baseline['native_image']
    cfg = native_elf.configuration(BASE,True,sha)
    cfg['flags'][0] = '-O2'
    cfg['tool_identity']['flags'] = cfg['flags']
    source = HERE/'names.scm'
    def cc(label,argv,cwd,build):
        subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=120)
    obj = native_module.build_module(out/'module',source.read_bytes(),sha(source),cfg,cache=out/'objects',
            report={},bind=sha,run=cc,save=lambda:None)['artifacts']['module']
    template = (pipeline/'observer.scm').read_text().replace(json.dumps(str(pipeline)),json.dumps(str(out)))
    key = '(let* ((start (real-time)) (forms (A-read))'
    assert template.count(key)==1
    template = template.replace(key, '(let* ((start (real-time)) (cleared (memo-reset!)) (forms (A-read))')
    template = template.replace('(A-repeat A-reps A-timed-round)', '(begin (A-repeat A-reps A-timed-round) (memo-report))')
    runs = []
    modes = ['stock','compile','emit','both']
    orders = [['verify'],modes,modes[::-1],modes[2:]+modes[:2]]
    for block,order in enumerate(orders):
        for mode in order:
            observer = out/'observer.scm'
            observer.write_text('(load '+json.dumps(obj['path'])+')\n(memo-mode! "'+mode+'")\n'+template)
            log = command([image,'--eval',observer,'unused'],os.environ,out/f'{mode}-{block}.log')
            times = [[1000*float(v) for v in l.split()[1:]] for l in log.splitlines() if l.startswith('A3_TIMING ')]
            assert len(times)==4 and 'definitions 104 emit-failures 0' in log
            hits = re.findall(r'MEMO \("([^"]+)" (\d+) (\d+)\)',log)
            if mode=='verify' and (len(hits)!=3 or any(int(h)==0 for _,h,_ in hits)):
                raise ValueError('Selected helpers were not exercised')
            runs.append(dict(mode=mode,block=block,timings_ms=times,
                counters={name:[int(h),int(m)] for name,h,m in hits},
                hash=sha(out/'native.scm',baseline['runs'][0]['emitted_sha256'])))
    medians = {}
    for mode in modes:
        samples = [r for arm in runs if arm['mode']==mode for r in arm['timings_ms']]
        medians[mode] = [statistics.median(col) for col in zip(*samples)] + [statistics.median(map(sum,samples))]
    write(out/'names.json',dict(image=sha(image),pipeline=sha(pipeline/'pipeline.json'),module=obj['sha256'],
          inputs={p:sha(HERE/p) for p in ('names.py','names.scm')},runs=runs,medians_ms=medians))
    print(medians)


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve())
