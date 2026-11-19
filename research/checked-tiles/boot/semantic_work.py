"""Count the same named compiler operations on both runtimes on the historical reader fixture."""
import argparse
import json
import os
import re
from pathlib import Path

from run import HERE, BASE, IMAGE, QUAL, command, sexp, sha, write

# Single-arity BL algorithms. Exclude public multi-arity dispatchers, helper
# lambdas, and kernel operations whose inlining intentionally differs by target.
NAMES = {'reader/read-form-core':1,'reader/read-atom':1,'compiler/declaration-source':2,
         'compiler/compile-node':2,'compiler/compile-call':2,'compiler/macro-lookup':2,
         'compiler/canonical-gensyms':1,'compiler/renumber':2,'compiler/data->form':1,
         'native.scheme/emit':2,'native.scheme/ident':1,'native.scheme/text':1}


def run(pipeline,out):
    out.mkdir()
    baseline = json.loads((pipeline/'pipeline.json').read_text())
    source = pipeline/'reader.bl'
    sha(source,baseline['source_sha256'])
    qual = json.loads(QUAL.read_text())
    sha(IMAGE/'stage2',qual['images']['stage2'])
    sdk_info=json.loads((HERE.parent/'tools.json').read_text())
    sdk=Path(sdk_info['sdk'])
    sha(sdk/'artifact.json',sdk_info['descriptor_sha256'])
    actual = (IMAGE/'stage2.scm').read_text()
    cells = {}
    for name,arity in NAMES.items():
        stem='v'+''.join('_'+str(ord(c)) for c in name)+'$'
        # Older reader providers have distinct fixed arities.
        fixed=re.findall(r'^\(define '+re.escape(stem)+r'(\d+) ',actual,re.M)
        if not fixed: raise ValueError(name)
        if str(arity) not in fixed:
            if len(fixed)!=1: raise ValueError((name,fixed))
            arity=int(fixed[0])
        cells[name]=stem+str(arity)
    obs=(pipeline/'observer.scm').read_text().replace(sexp(str(pipeline)),sexp(str(out)))
    obs=obs.replace('(define A-reps 4)','(define A-reps 1)')
    marked = '''(define census (make-vector %d 0))
(define (count! i cell)
 (let* ((v (##make-global-var (string->symbol cell))) (f (##global-var-ref v)))
  (##global-var-set! v (lambda args (vector-set! census i (+ 1 (vector-ref census i))) (apply f args)))))
(define (phase p action)
 (vector-fill! census 0)
 (let ((v (action))) (display "WORK ") (display p)
  (for-each (lambda (n) (display " ") (display n)) (vector->list census)) (newline) v))
(define (A-timed-round)
 %s
 (let* ((forms (phase "read" A-read)) (nodes (phase "compile" (lambda () (A-compile-forms forms))))
        (texts (phase "emit" (lambda () (A-emit-nodes nodes)))))
  (if (not (string=? (A-join texts) (native-read-file (string-append A-out "/native.scm"))))
   (error "counted translation differs"))))
''' % (len(cells),'\n '.join('(count! %d %s)'%(i,sexp(v)) for i,v in enumerate(cells.values())))
    (out/'observer.scm').write_text(obs.replace('(define (A-run)',marked+'\n(define (A-run)'))
    env=dict(os.environ,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    native=command([IMAGE/'stage2','--eval',out/'observer.scm','unused'],env,out/'native.log')
    driver=(BASE/'speed/attrib/beam-attrib.bl').read_text()
    names=' '.join(sexp(n.split('/')[1]) for n in cells)
    source_report='(def observed-fns #{'+names+'})\n'+(HERE/'beam-work.bl').read_text()
    (out/'beam-work.bl').write_text(driver[:driver.index('(defn report')]+source_report+'\n'+driver[driver.index('(defn reductions'):])
    beam=command([sdk/'bin/bl','--cold','-p',pipeline/'pinned','run',out/'beam-work.bl',
                  '--',source,out,'1','snapshot'],env,out/'beam.log',timeout=480)
    expected=baseline['runs'][0]['emitted_sha256']
    for platform in ['native','beam']: sha(out/(platform+'.scm'),expected)
    if any('definitions 104 emit-failures 0' not in log for log in (native,beam)):
        raise ValueError('Incomplete pipeline')
    counts={r.split()[1]:dict(zip(cells,map(int,r.split()[2:]),strict=True)) for r in native.splitlines() if r.startswith('WORK ')}
    if set(counts) != {'read','compile','emit'} or any(not any(row[n] for row in counts.values()) for n in cells):
        raise ValueError('Missing native compiler entries')
    entries={phase:[] for phase in counts}
    for line in beam.splitlines():
        if line.startswith('ENTRY\t'):
            _,phase,module,fun,arity,n=line.split('\t')
            entries[phase].append(dict(module=module,function=fun,arity=int(arity),calls=int(n)))
    matched={phase:{} for phase in counts}
    for phase, candidates in entries.items():
        for name,cell in cells.items():
            if not counts[phase][name]: continue
            owner,fun=name.split('/')
            module='.'.join(part.capitalize() for part in owner.split('.'))
            possible=[r for r in candidates if r['module'] in ['Elixir.BeamLisp.Ns.Body.'+module,'Elixir.BeamLisp.Ns.'+module]
                      and r['function']==fun and r['arity']==int(cell.split('$')[-1])]
            actual=next((r for r in possible if '.Ns.Body.' in r['module']),None)
            if not actual and len(possible)==1: actual=possible[0]
            if actual: matched[phase][name]=actual['calls']
    for phase,native_counts in counts.items():
        expected={name:n for name,n in native_counts.items() if n}
        if matched[phase]!=expected:
            raise ValueError(f'Compiler entries differ in {phase}: {matched[phase]} vs {expected}')
    write(out/'work.json',dict(image=qual['images']['stage2'],sdk=sdk_info['descriptor_sha256'],
        fixture=sha(source),output=expected,cells=cells,native=counts,beam=matched,beam_mfas=entries))
    for phase in matched:
        print(phase,[(n,counts[phase][n],b) for n,b in matched[phase].items()])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve())
