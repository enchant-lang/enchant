"""Isolate compiled versus evaluated boot macro bodies on the recorded reader compile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess

from run import BASE, IMAGE, QUAL, command, native_elf, native_module, sexp, sha, write

# Count the kind of procedures the original generated bundle registers, only
# while it is loading. Restore the original registrar before compiling Source.
REGISTER = '''
(define (observed-install thunk)
 (let ((saved bl-register-callable!) (compiled 0) (interpreted 0))
  (set! bl-register-callable!
    (lambda (f arity)
     (if (##interp-procedure? f) (set! interpreted (+ interpreted 1)) (set! compiled (+ compiled 1)))
     (saved f arity)))
  (let ((bundle (thunk)))
    (set! bl-register-callable! saved)
    (A-log "BUNDLE_PROCEDURES " compiled " " interpreted)
    bundle)))
'''


def run(pipeline,out):
    out.mkdir()
    prior=json.loads((pipeline/'pipeline.json').read_text())
    image=IMAGE/'stage2'
    qual=json.loads(QUAL.read_text())
    sha(image,qual['images']['stage2'])
    assert sha(image)==prior['native_image']
    bundle=IMAGE/'eval-prepared.scm'
    sha(bundle,qual['prepared_macro_bundle_sha256'])
    sha(pipeline/'reader.bl',prior['source_sha256'])
    # Preserve the return value as well as the ordered module initialization.
    source=b'(define cost-bundle-result\n'+bundle.read_bytes()+b'\n)\n'
    cfg=native_elf.configuration(BASE,True,sha)
    def cc(label,argv,cwd,build):
        subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=180)
    obj=native_module.build_module(out/'module',source,hashlib.sha256(source).hexdigest(),cfg,
                       cache=out/'objects',report={},bind=sha,run=cc,save=lambda:None)['artifacts']['module']
    template=(pipeline/'observer.scm').read_text().replace(sexp(str(pipeline)),sexp(str(out)))
    key='(native-eval-string (native-read-file A-bundle-path))'
    assert template.count(key)==1
    loads={'evaluated':key,'aot':'(begin (load '+sexp(str(obj['path']))+') cost-bundle-result)'}
    runs=[]
    for block,order in enumerate([['evaluated','aot'],['aot','evaluated']]):
        for mode in order:
            file=out/(mode+'.scm')
            file.write_text(REGISTER+template.replace(key,'(observed-install (lambda () '+loads[mode]+'))'))
            log=command([image,'--eval',file,'unused'],os.environ,out/f'{mode}-{block}.log')
            compiled,interpreted=next([int(v) for v in line.split()[1:]] for line in log.splitlines() if line.startswith('BUNDLE_PROCEDURES '))
            assert (compiled>0 and interpreted==0) if mode=='aot' else (interpreted>0 and compiled==0)
            trials=[[float(v)*1000 for v in line.split()[1:]] for line in log.splitlines() if line.startswith('A3_TIMING ')]
            assert len(trials)==4 and 'definitions 104 emit-failures 0' in log
            runs.append(dict(mode=mode,block=block,compiled=compiled,interpreted=interpreted,trials_ms=trials,
                        output=sha(out/'native.scm',prior['runs'][0]['emitted_sha256'])))
    medians={}
    for mode in loads:
        samples=[t for r in runs if r['mode']==mode for t in r['trials_ms']]
        medians[mode]=[statistics.median(values) for values in zip(*samples)]+[statistics.median(map(sum,samples))]
    write(out/'macro-cost.json',dict(image=sha(image),bundle=sha(bundle),object=obj['sha256'],flags=cfg['flags'],
          driver=sha(Path(__file__)),source=prior['source_sha256'],medians_ms=medians,runs=runs,
          scope='Counterbalanced warm Source read, compile and emit. Only the preparation of boot macro bodies differs.'))
    print(medians)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve())
