"""Try the same compiler name reuse on two boot namespaces outside the tuning fixture."""
import argparse
import json
import os
from pathlib import Path
import statistics
from run import BASE, HERE, IMAGE, QUAL, ROOT, command, sexp, sha, write


def run(pipeline, names, out, include_emit=False):
    out.mkdir()
    tools = json.loads((HERE.parent/'tools.json').read_text())
    sdk = Path(tools['sdk'])
    sha(sdk/'artifact.json',tools['descriptor_sha256'])
    image = IMAGE/'stage2'
    sha(image,json.loads(QUAL.read_text())['images']['stage2'])
    receipt = json.loads((names/'names.json').read_text())
    obj, = (names/'module').glob('*.o1')
    sha(obj,receipt['module'])
    sha(pipeline/'pipeline.json',receipt['pipeline'])
    template = (pipeline/'observer.scm').read_text()
    beamt = (BASE/'speed/attrib/beam-attrib.bl').read_text()
    env = dict(os.environ,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    modes = ['stock','emit','both','beam'] if include_emit else ['stock','both','beam']
    report = {}
    for ns, size in [('anf',100),('diag',22)]:
        folder = out/ns
        folder.mkdir()
        source = ROOT/f'priv/boot/{ns}.bl'
        attribution = str(source.relative_to(ROOT))
        beam = folder/'driver.bl'
        beam.write_text(beamt.replace('(def ns-name "reader")','(def ns-name '+sexp(ns)+')')
                             .replace('priv/boot/reader.bl',attribution))
        nativet = (template.replace(sexp(str(pipeline/'reader.bl')),sexp(str(source)))
                   .replace(sexp(str(pipeline)),sexp(str(folder)))
                   .replace('(define A-ns "reader")','(define A-ns '+sexp(ns)+')')
                   .replace('"priv/boot/reader.bl"',sexp(attribution))
                   .replace('(start (real-time)) (forms (A-read))','(start (real-time)) (reset (memo-reset!)) (forms (A-read))'))
        runs = []
        for block,order in enumerate([modes,list(reversed(modes))]):
            for mode in order:
                if mode=='beam':
                    argv=[sdk/'bin/bl','--cold','-p',pipeline/'pinned','run',beam,'--',source,folder,'4','snapshot','timing']
                else:
                    payload=folder/'observer.scm'
                    payload.write_text('(load '+sexp(str(obj))+')\n(memo-mode! '+sexp(mode)+')\n'+nativet)
                    argv=[image,'--eval',payload,'unused']
                log=command(argv,env,folder/f'{block}-{mode}.log')
                prefix,scale=('A3_TIMING_US ',0.001) if mode=='beam' else ('A3_TIMING ',1000)
                rows=[[float(x)*scale for x in l.split()[1:]] for l in log.splitlines() if l.startswith(prefix)]
                if len(rows)!=4 or f'definitions {size} emit-failures 0' not in log:
                    raise ValueError('Unexpected measurement '+log[-600:])
                artifact=folder/('beam.scm' if mode=='beam' else 'native.scm')
                runs.append(dict(block=block,mode=mode,timings_ms=rows,sha256=sha(artifact),bytes=artifact.stat().st_size))
        if len({r['sha256'] for r in runs if r['mode']!='beam'})!=1:
            raise ValueError('Native optimization changed emitted code')
        medians={}
        for mode in modes:
            samples=[t for r in runs if r['mode']==mode for t in r['timings_ms']]
            medians[mode]=[statistics.median(c) for c in zip(*samples)]+[statistics.median(map(sum,samples))]
        report[ns]=dict(source=sha(source),definitions=size,runs=runs,medians_ms=medians,
                        all_outputs_equal=len({r['sha256'] for r in runs})==1)
        print(ns,medians,flush=True)
    write(out/'heldout.json',dict(sdk=tools['descriptor_sha256'],image=sha(image),names=sha(names/'names.json'),jobs=report))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('names',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--include-emit',action='store_true',
                   help='include emitter-only name reuse in both held-out workloads')
    a=p.parse_args()
    run(a.pipeline.resolve(),a.names.resolve(),a.out.resolve(),a.include_emit)
