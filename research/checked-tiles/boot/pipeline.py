"""Counterbalanced, complete read/compile/emit comparison on the frozen 104 definitions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

from run import ROOT, HERE, BASE, IMAGE, QUAL, command, sha, write

ATTR=BASE/'speed/attrib'
FIXTURE='93a224b6b74fb52209e9f13b913a459f8b5cfef10f73f9173d3f2143653102ef'
REV='507346397e954cff891fca4382a6f32ee47e9d78'


def source_at(path,expected):
    local=ROOT/path
    if sha(local)==expected:
        return local.read_bytes(),'checkout'
    history=subprocess.check_output(['git','log','-80','--format=%H','--',path],cwd=ROOT,text=True)
    for rev in history.splitlines():
        data=subprocess.check_output(['git','show',rev+':'+path],cwd=ROOT)
        if hashlib.sha256(data).hexdigest()==expected:
            return data,rev
    raise ValueError('Missing qualified source '+path)


def run(out):
    out.mkdir()
    qual=json.loads(QUAL.read_text())
    image=IMAGE/'stage2'
    sha(image,qual['images']['stage2'])
    bundle=IMAGE/'eval-prepared.scm'
    sha(bundle,qual['prepared_macro_bundle_sha256'])
    sdk_info=json.loads((HERE.parent/'tools.json').read_text())
    sdk=Path(sdk_info['sdk'])
    sha(sdk/'artifact.json',sdk_info['descriptor_sha256'])
    source=out/'reader.bl'
    source.write_bytes(subprocess.check_output(['git','show',REV+':priv/boot/reader.bl'],cwd=ROOT))
    sha(source,FIXTURE)
    ns=out/'pinned/native'
    ns.mkdir(parents=True)
    providers=json.loads((IMAGE/'identity.json').read_text())['providers']
    sources={}
    for p in providers:
        if p['path'].startswith('research/native-seed/src/native/'):
            data,rev=source_at(p['path'],p['sha256'])
            (ns/Path(p['path']).name).write_bytes(data)
            sources[p['path']]=[p['sha256'],rev]
    observer=out/'observer.scm'
    text=(ATTR/'native-attrib.scm.in').read_text()
    substitutions={'SOURCE':str(source),'BUNDLE':str(bundle),'TARGETS':'unused','OUT':str(out)}
    for key,value in substitutions.items(): text=text.replace('@'+key+'@',json.dumps(value))
    for key,value in {'REPS':'4','INTERVAL':'0.001','COUNTS':'#f','TIMINGS':'#t'}.items():
        text=text.replace('@'+key+'@',value)
    observer.write_text(text)
    env=dict(os.environ,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    result={'native_image':sha(image),'prepared_macros':sha(bundle),'source_sha256':sha(source),
            'sdk':sdk_info['descriptor_sha256'],'pinned_emitter_sources':sources,'runs':[]}
    arms={'native':[image,'--eval',observer,bundle],
          'beam':[sdk/'bin/bl','--cold','-p',ns.parent,'run',ATTR/'beam-attrib.bl','--',source,out,'4','snapshot','timing']}
    for block,order in enumerate([['native','beam'],['beam','native']]):
        for name in order:
            started=time.perf_counter()
            log=command(arms[name],env,out/f'{name}-{block}.log',timeout=240)
            if name=='native':
                timings=[[float(v)*1000 for v in line.split()[1:]] for line in log.splitlines() if line.startswith('A3_TIMING ')]
            else:
                timings=[[float(v)/1000 for v in line.split()[1:]] for line in log.splitlines() if line.startswith('A3_TIMING_US ')]
            if len(timings)!=4 or not re.search(r'definitions 104 emit-failures 0',log):
                raise ValueError('Incomplete compiler observations: '+log[-500:])
            artifact=out/(name+'.scm')
            result['runs'].append(dict(arm=name,block=block,timings_ms=timings,emitted_sha256=sha(artifact),
                                      emitted_bytes=artifact.stat().st_size,session_s=time.perf_counter()-started))
            print('pipeline',name,block,sha(artifact)[:12],flush=True)
    result['medians_ms']={}
    for name in arms:
        times=[row for r in result['runs'] if r['arm']==name for row in r['timings_ms']]
        result['medians_ms'][name]=[statistics.median(x) for x in zip(*times)] + [statistics.median(map(sum,times))]
    result['same_emitted_bytes']=len({b['emitted_sha256'] for b in result['runs']})==1
    write(out/'pipeline.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True,type=Path)
    run(p.parse_args().out.resolve())
