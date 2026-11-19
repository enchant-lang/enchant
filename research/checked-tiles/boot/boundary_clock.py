"""Measure inclusive time in matched BL functions in the original warm reader job."""
import argparse
import json
import os
import re
import statistics
import subprocess
from pathlib import Path

from run import BASE, HERE, IMAGE, QUAL, command, native_elf, native_module, sexp, sha, write

TARGETS = {
    'read': ('reader/read-atom',),
    'compile': ('compiler/declaration-source', 'compiler/expand-macro', 'compiler/datum-macro-result',
                'compiler/macro-lookup', 'compiler/compile-symbol'),
    'emit': ('native.scheme/ident', 'native.scheme/text', 'native.scheme/literal'),
}
MACRO = {'compile': ('compiler/expand-macro', 'compiler/datum', 'compiler/datum-macro-result',
                     'host.compiler-data/check_first_order!', 'compiler/data->form', 'compiler/renumber',
                     'compiler/gensym-base')}


def run(pipeline, out, targets=TARGETS):
    out.mkdir()
    original = json.loads((pipeline/'pipeline.json').read_text())
    image = IMAGE/'stage2'
    qualification = json.loads(QUAL.read_text())
    sha(image, qualification['images']['stage2'])
    sdk_info = json.loads((HERE.parent/'tools.json').read_text())
    sdk = Path(sdk_info['sdk'])
    sha(sdk/'artifact.json', sdk_info['descriptor_sha256'])
    source = pipeline/'reader.bl'
    sha(source, original['source_sha256'])
    clock = HERE/'boundary-clock.scm'
    def compile_step(label, argv, cwd, build):
        subprocess.run(argv, cwd=cwd, check=True, capture_output=True, timeout=120)
    module = native_module.build_module(out/'module', clock.read_bytes(), sha(clock),
        native_elf.configuration(BASE,True,sha), cache=out/'objects', report={}, bind=sha,
        run=compile_step, save=lambda:None)['artifacts']['module']
    native = (pipeline/'observer.scm').read_text().replace(sexp(str(pipeline)),sexp(str(out)))
    definitions = (IMAGE/'stage2.scm').read_text()
    observed = []
    clocks = []
    for phase, names in targets.items():
        action = {'read':'A-read','compile':'(lambda () (A-compile-forms forms))',
                  'emit':'(lambda () (A-emit-nodes nodes))'}[phase]
        reference = {'read':'forms','compile':'nodes','emit':'texts'}[phase]
        for name in names:
            owner, fn = name.split('/')
            stem = 'v'+''.join('_'+str(ord(c)) for c in name)+'$'
            arities = re.findall(r'^\(define '+re.escape(stem)+r'(\d+) ',definitions,re.M)
            module_name = '.'.join(part.capitalize() for part in owner.split('.'))
            physical_module = 'Elixir.BeamLisp.Ns.Body.'+module_name
            if owner=='host.compiler-data':
                arity = '2'
                if arity not in arities: raise ValueError(name)
                physical_module = 'Elixir.BeamLisp.CompilerData'
            else:
                arity, = arities
            observed.append(f'["{phase}" :{physical_module} :"{fn}" {arity}]')
            clocks.append(f'(A-repeat 3 (lambda () (boundary-clock "{phase}" "{fn}" "{stem}{arity}" {action} {reference})))')
    native = native.replace('(A-repeat A-reps A-timed-round)','(begin '+'\n'.join(clocks)+')')
    (out/'observer.scm').write_text('(load '+sexp(module['path'])+')\n'+native)
    driver = (BASE/'speed/attrib/beam-attrib.bl').read_text()
    beam = '(def observed ['+' '.join(observed)+'])\n'+(HERE/'beam-boundary.bl').read_text()
    (out/'driver.bl').write_text(driver[:driver.index('(defn report')]+beam+'\n'+driver[driver.index('(defn reductions'):])
    env = dict(os.environ, ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    samples = {}
    for engine, argv in [('native',[image,'--eval',out/'observer.scm','unused']),
                         ('beam',[sdk/'bin/bl','--cold','-p',pipeline/'pinned','run',out/'driver.bl',
                                  '--',source,out,'3','snapshot'])]:
        log = command(argv,env,out/(engine+'.log'),timeout=300)
        if 'definitions 104 emit-failures 0' not in log or 'A3_DONE' not in log:
            raise ValueError('Incomplete translation')
        sha(out/(engine+'.scm'), original['runs'][0]['emitted_sha256'])
        for line in log.splitlines():
            if line.startswith('BOUND '):
                _,phase,name,count,elapsed,duration = line.split()
                samples.setdefault(name,{}).setdefault(engine,[]).append(
                    dict(phase=phase,calls=int(count),elapsed_ms=float(elapsed),phase_ms=float(duration)))
    result = {}
    for names in targets.values():
        for full in names:
            name = full.split('/')[1]
            matched = samples[name]
            if (set(matched) != {'native','beam'} or any(len(v)!=3 for v in matched.values())
                    or len({r['calls'] for rs in matched.values() for r in rs})!=1
                    or matched['native'][0]['calls']==0):
                raise ValueError('Incomplete or unmatched measurements for '+full)
            result[full] = {k:statistics.median(x['elapsed_ms'] for x in v) for k,v in matched.items()}
    write(out/'boundaries.json',dict(image=sha(image),sdk=sdk_info['descriptor_sha256'],source=sha(source),
        output=original['runs'][0]['emitted_sha256'],module=module['sha256'],medians_ms=result,samples=samples))
    print(result)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pipeline',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--macro-detail',action='store_true')
    args=parser.parse_args()
    run(args.pipeline.resolve(),args.out.resolve(),MACRO if args.macro_detail else TARGETS)
