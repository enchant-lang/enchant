"""Build unchanged missing boot modules with the qualified native compiler and execute probes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from run import HERE, BASE, IMAGE, QUAL, ROOT, command, native_elf, native_module, sexp, sha, write

EXCEPTIONS={'host.reader-exception.syntax':'Elixir.BeamLisp.Reader.SyntaxError',
            'host.reader-exception.limit':'Elixir.BeamLisp.Reader.AtomLimitError'}
MODULES={'host.reader':'priv/host/reader.bl','syntax':'priv/boot/syntax.bl',
         **{ns:'priv/host/reader_exception.bl' for ns in EXCEPTIONS}}


def run(out):
    out.mkdir()
    qual=json.loads(QUAL.read_text())
    image=IMAGE/'stage2'
    sha(image,qual['images']['stage2'])
    bundle=IMAGE/'eval-prepared.scm'
    sha(bundle,qual['prepared_macro_bundle_sha256'])
    (out/'modules.scm').write_text(sexp([[name,path,*([EXCEPTIONS[name]] if name in EXCEPTIONS else [])] for name,path in MODULES.items()]))
    tools=json.loads((HERE.parent/'tools.json').read_text())
    sdk=Path(tools['sdk'])
    sha(sdk/'artifact.json',tools['descriptor_sha256'])
    env=dict(os.environ,BOOT_BUNDLE=str(bundle),BOOT_OUT=str(out),BOOT_WIRE=str(HERE/'wire.scm'),
             BOOT_LINKS=str(HERE/'links.scm'),ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    def native(payload,log):
        return command([image,'--eval',payload,'unused'],env,out/log)
    emissions=native(HERE/'extend.scm','emit.log').splitlines()
    report={'image':sha(image),'bundle':sha(bundle),'emitter':sha(HERE/'extend.scm'),'modules':{}}
    cfg=native_elf.configuration(BASE,True,sha)
    cfg['flags'][0]='-O2'
    cfg['tool_identity']['flags']=cfg['flags']
    objects=[]
    for ns,path in MODULES.items():
        source=(out/(ns+'.scm')).read_bytes()
        names=[line.split('\t')[2] for line in emissions if line.startswith('EMIT\t'+ns+'\t')]
        def compile_step(label,argv,cwd,build):
            subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=120)
        product=native_module.build_module(out/ns,source,hashlib.sha256(source).hexdigest(),cfg,
                cache=out/'objects',report={},bind=sha,run=compile_step,save=lambda:None)['artifacts']['module']
        objects.append(product['path'])
        report['modules'][ns]=dict(source=sha(ROOT/path),names=names,scheme=sha(out/(ns+'.scm')),object=product['sha256'])
    (out/'objects.scm').write_text(sexp(objects))
    print([(ns,len(v['names'])) for ns,v in report['modules'].items()],flush=True)
    args=[['reader-read','host.reader','read_string','source'],['reader-syntax','host.reader','read_syntax','source'],
          ['reader-bare','host.reader','read_all','bare'],['reader-one','host.reader','read_one','bare'],
          ['reader-first','host.reader','read_first','source'],['reader-invalid','host.reader','read_string','invalid'],
          ['identifier-false','syntax','identifier?','nil'],['context','syntax','context','context'],
          ['identifier','syntax','identifier','identifier'],['read-context','syntax','read','read-context']]
    (out/'probes.scm').write_text(sexp(args))
    beam_driver=out/'oracle.bl'
    beam_driver.write_text((HERE/'wire.bl').read_text()+'\n'+(HERE/'extension-oracle.bl').read_text())
    command([sdk/'bin/bl','--cold','run',beam_driver,'--',out],env,out/'beam.log')
    result=native(HERE/'extension-check.scm','execution.log')
    report['observations']=[]
    for line in result.splitlines():
        phase,name,status=line.split('\t',2)
        gold=sha(out/('beam-'+name+'.wire'))
        value=sha(out/(phase+'-'+name+'.wire'))
        report['observations'].append(dict(phase=phase,name=name,status=status,
                                           beam=gold,native=value,equal=gold==value))
    if len(report['observations'])!=2*len(args): raise ValueError('Missing native observations')
    report['sdk']=tools['descriptor_sha256']
    report['inputs']={name:sha(HERE/name) for name in ['extend.scm','extension-check.scm','links.scm','extension-oracle.bl','wire.bl','wire.scm']}
    write(out/'extension.json',report)
    print([(r['phase'],r['name'],r['equal']) for r in report['observations']])



if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path)
    run(p.parse_args().out.resolve())
