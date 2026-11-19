"""Compare the same emitted BL recurrence with per-operation and per-entry guards."""
import argparse
import json
import os
from pathlib import Path
import statistics

from run import HERE, SEED, TOOLS, case, checked, digest, job, native_elf, native_module, run_block, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session',type=Path)
    p.add_argument('--out',required=True,type=Path)
    style=p.add_mutually_exclusive_group()
    style.add_argument('--direct', action='store_true',
                   help='keep the machine primitive in operator position inside a lexical lambda')
    style.add_argument('--machine', action='store_true',
                       help='lower the four proved operations to unchecked primitives inside their own lambdas')
    args=p.parse_args()
    mode='machine' if args.machine else 'direct' if args.direct else 'value'
    old=args.session.resolve()
    out=args.out.resolve()
    out.mkdir()
    receipt=json.loads((old/'receipt.json').read_text())
    expected=receipt['build']
    image=SEED/'out/compiler-native-owner/stage2'
    checked(image,expected['stage2'])
    checked(old/'bend',expected['bend_elf_sha256'])
    sdk=Path(TOOLS['sdk'])
    checked(sdk/'artifact.json',TOOLS['descriptor_sha256'])
    env=dict(os.environ,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    env['LD_LIBRARY_PATH']='/run/opengl-driver/lib:'+env.get('LD_LIBRARY_PATH','')
    proof=job([TOOLS['lean'],'-j2',HERE/'Bound.lean'])
    if 'sorryAx' in proof or 'SerialRegion.invariant' not in proof:
        raise ValueError('Unclosed invariant')
    raw=out/'serial.scm'
    job([sdk/'bin/bl','--cold','-p',SEED/'src','run',HERE/'bounded.bl','--',HERE/'kernels.bl',raw,
         mode],env=env)
    ordinary=(HERE/'arithmetic.scm').read_bytes()+(old/'shapes.scm').read_bytes()
    if digest(ordinary)!=expected['modules']['shapes-O2']['source_sha256']:
        raise ValueError('Prepared control changed')
    code=ordinary+raw.read_bytes()+(HERE/'select.scm').read_bytes()
    cfg=native_elf.configuration(SEED,True,checked)
    cfg['flags'][0]='-O2'
    cfg['tool_identity']['flags']=cfg['flags']
    def compile_step(label,argv,cwd,build):
        return job(argv,cwd=cwd)
    obj=native_module.build_module(out,code,digest(code),cfg,cache=out/'objects',report={},bind=checked,
                                   run=compile_step,save=lambda:None)['artifacts']['module']
    base=next((old/'shapes-O2').glob('*.o1'))
    checked(base,expected['modules']['shapes-O2']['elf_sha256'])
    boundary=job([image,'--eval',HERE/'boundary.scm',obj['path']]).strip()
    if boundary != '12 boundary and fallback controls passed':
        raise ValueError(boundary)
    text=raw.read_text()
    if '(h-tick)' not in text or not all(op in text for op in ['##fx+','##fx-','##fx*','##fx<']):
        raise ValueError('Expected arithmetic or scheduling checkpoint missing')
    commands={'shapes':[image,'--eval',HERE/'serve.scm',base],
              'bounded':[image,'--eval',HERE/'serve.scm',obj['path']],
              'bend-cpu1':[old/'bend','+RTS','--threads','1','--gpu','off']}
    generated=next(out.glob('*.dynamic.c')).read_text()
    external=[op for op in ['##fx+', '##fx-', '##fx*', '##fx<'] if ('"'+op+'"') in generated]
    if args.machine and (external or '___FIXADD(' not in generated or '___FIXMUL(' not in generated):
        raise ValueError('Proved operations still require dynamic calls')
    r=dict(intrinsic_call=mode, external_primitives=external,proof=proof,boundary=boundary,source_sha256=checked(HERE/'kernels.bl'),raw_sha256=checked(raw),
           proof_sha256=checked(HERE/'Bound.lean'),elf_sha256=obj['sha256'],runs={},order=[])
    for block in range(3):
        trials=[[case(1,n,17+trial*23+block) for n in (64,4096,32768,65535)] for trial in range(5)]
        order=list(commands)[block:]+list(commands)[:block]
        r['order'].append(order)
        for name in order:
            row=run_block(commands[name],env,out,name,block,trials)
            r['runs'].setdefault(name,[]).append(row)
    r['medians_ms']={name:{key:statistics.median(x for row in rows for x in row['samples_ms'][key])
                          for key in rows[0]['samples_ms']} for name,rows in r['runs'].items()}
    save(out/'receipt.json',r)
    print(json.dumps(r['medians_ms']))


if __name__=='__main__':
    main()
