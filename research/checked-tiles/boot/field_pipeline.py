"""Compare freshly built native compilers with the warm SDK on complete translations."""
import argparse
import json
import os
import statistics
from pathlib import Path

from run import BASE, HERE, ROOT, command, sexp, sha, write

CLOCK = """(define (A-timed-round)
 (let* ((w (real-time)) (c (cpu-time)) (forms (A-read))
        (r (real-time)) (rc (cpu-time)) (nodes (A-compile-forms forms))
        (k (real-time)) (kc (cpu-time)) (texts (A-emit-nodes nodes))
        (e (real-time)) (ec (cpu-time)))
  (A-log "WALL " (- r w) " " (- k r) " " (- e k))
  (A-log "CPU " (- rc c) " " (- kc rc) " " (- ec kc))
  (if (not (string=? (A-join texts) (native-read-file (string-append A-out "/native.scm"))))
      (error "timed translation differs from warmup"))))
"""

CENSUS = """(define (field-census nodes)
 (let ((children (A-select "anf" "executable-children")))
  (let visit ((todo nodes) (compact 0) (total 0))
   (if (null? todo) (A-log "LAYOUT " compact " " total)
    (let* ((node (car todo)) (storage (vector-ref node 1))
           (shared (and (vector? storage) (vector? (vector-ref storage 0)))))
     (visit (append (A-call children node) (cdr todo))
            (if shared (+ compact 1) compact) (+ total 1)))))))
"""


def rows(log, mark, factor):
    result = [[float(s)*factor for s in line.split()[1:]]
              for line in log.splitlines() if line.startswith(mark+' ')]
    if len(result) != 4 or any(len(r) != 3 for r in result):
        raise ValueError('Missing phase observations: ' + mark)
    return result


def medians(samples):
    return [statistics.median(col) for col in zip(*samples)] + [statistics.median(map(sum, samples))]


def run(pipeline, control, candidate, out, before_symbols=None):
    out.mkdir()
    sdk_info = json.loads((HERE.parent/'tools.json').read_text())
    sdk = Path(sdk_info['sdk'])
    sha(sdk/'artifact.json', sdk_info['descriptor_sha256'])
    sdk_source = Path(json.loads((sdk/'artifact.json').read_text())['source'])
    core = {}
    for build in [control, candidate]:
        providers = {r['path']:r['sha256'] for r in json.loads((build/'identity.json').read_text())['providers']}
        for p in ('priv/boot/reader.bl','priv/boot/compiler.bl','priv/boot/anf.bl','priv/boot/rt.bl',
                  'priv/boot/core.bl','priv/boot/sugar.bl','priv/host/compiler_data.bl','priv/host/optimize.bl'):
            core[p] = sha(sdk_source/p,providers[p])
    bundle = control/'eval-prepared.scm'
    template = (pipeline/'observer.scm').read_text()
    reference = json.loads((pipeline/'pipeline.json').read_text())
    sha(pipeline/'reader.bl', reference['source_sha256'])
    env = dict(os.environ, ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    report = dict(sdk=sdk_info['descriptor_sha256'], core_sources=core, prepared_macros=sha(bundle),
                  images={k:sha(v/'stage1') for k,v in [('control',control),('candidate',candidate)]},
                  boot_sources={k:sha(v/'stage1.scm') for k,v in [('control',control),('candidate',candidate)]},
                  jobs={})
    if before_symbols:
        report['images']['fields'] = sha(before_symbols/'stage1')
        report['boot_sources']['fields'] = sha(before_symbols/'stage1.scm')
    arms = ['control','flat','candidate','beam']
    if before_symbols: arms.insert(2,'fields')
    for ns, path in [('reader',pipeline/'reader.bl'),('anf',ROOT/'priv/boot/anf.bl'),('diag',ROOT/'priv/boot/diag.bl')]:
        job = out/ns
        job.mkdir()
        attr = 'priv/boot/'+ns+'.bl'
        observer = (template.replace(sexp(str(pipeline/'reader.bl')),sexp(str(path)))
                    .replace(sexp(str(pipeline)),sexp(str(job)))
                    .replace('(define A-ns "reader")','(define A-ns '+sexp(ns)+')')
                    .replace('"priv/boot/reader.bl"', sexp(attr)))
        old_bundle = next(s for s in observer.splitlines() if s.startswith('(define A-bundle-path '))
        observer = observer.replace(old_bundle, '(define A-bundle-path '+sexp(str(bundle))+')')
        observer = observer.replace('(define (A-run)', CLOCK+CENSUS+'\n(define (A-run)')
        observer = observer.replace('(A-log "A3_FIXTURE', '(field-census nodes) (A-log "A3_FIXTURE')
        beam = job/'driver.bl'
        beam.write_text((BASE/'speed/attrib/beam-attrib.bl').read_text()
                        .replace('(def ns-name "reader")','(def ns-name '+sexp(ns)+')')
                        .replace('priv/boot/reader.bl',attr))
        runs = []
        for order in [arms, list(reversed(arms))]:
            for arm in order:
                payload = job/'observer.scm'
                if arm == 'beam':
                    argv = [sdk/'bin/bl','--cold','-p',BASE/'src','run',beam,'--',path,job,'4','snapshot','timing']
                else:
                    # Switch only construction. Any pre-existing compact map must
                    # remain readable through every ordinary map operation.
                    switch = '(set! native-field-map (lambda (pairs size) #f))\n' if arm=='flat' else ''
                    payload.write_text(switch+observer)
                    image = control if arm=='control' else before_symbols if arm=='fields' else candidate
                    argv = [image/'stage1','--eval',payload,bundle]
                log = command(argv,env,job/(str(len(runs))+'-'+arm+'.log'),timeout=360)
                if 'emit-failures 0' not in log or 'A3_DONE' not in log:
                    raise ValueError('Incomplete translation')
                wall = rows(log,'A3_TIMING_US',0.001) if arm=='beam' else rows(log,'WALL',1000)
                digest = sha(job/('beam.scm' if arm=='beam' else 'native.scm'))
                layout = None if arm=='beam' else next([int(v) for v in l.split()[1:]]
                    for l in log.splitlines() if l.startswith('LAYOUT '))
                if layout and ((layout[0]>0)!=(arm in ('candidate','fields')) or layout[1]<1):
                    raise ValueError(f'Construction switch was ineffective: {arm} {layout}')
                runs.append(dict(arm=arm,output=digest,wall_ms=wall,layout=layout,
                                 cpu_ms=None if arm=='beam' else rows(log,'CPU',1000)))
        if len({r['output'] for r in runs}) != 1:
            raise ValueError('Compiler output mismatch for '+ns+': '+str([(r['arm'],r['output']) for r in runs]))
        stats = {a:medians([t for r in runs if r['arm']==a for t in r['wall_ms']])
                 for a in order}
        report['jobs'][ns] = dict(source=sha(path), output=runs[0]['output'],runs=runs,medians_ms=stats)
        write(out/'field-pipeline.json',report)
        print(ns,stats,flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('pipeline','control','candidate'):
        parser.add_argument(arg,type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--before-symbols',type=Path)
    a=parser.parse_args()
    run(a.pipeline.resolve(),a.control.resolve(),a.candidate.resolve(),a.out.resolve(),a.before_symbols.resolve() if a.before_symbols else None)
