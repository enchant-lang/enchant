#!/usr/bin/env python3
"""Retain observed scan evidence and exact emitter bytes; never rerun a compiler."""
import argparse, gzip, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('build',type=Path);p.add_argument('runtime',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
files={}
def copy(src,name,compress=False):
    data=Path(src).read_bytes();out=a.output/name;out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes(gzip.compress(data,mtime=0) if compress else data)
    files[name]={'source':str(Path(src).resolve()),'source_sha256':hashlib.sha256(data).hexdigest(),
                 'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'gzip':compress}
m=json.loads((a.build/'module.json').read_text())
r=json.loads((a.runtime/'observation.json').read_text())
assert r['passed'] and r['checks']>800
for name in ['module.json','preflight.json']:copy(a.build/name,name)
for name in ['observation.json','preparation.json','native.log','reference.txt','candidate.txt']:copy(a.runtime/name,name)
copy(a.runtime/'observer.scm','observer.scm.gz',True)
copy(m['source']['path'],'kernel.bl')
copy(m['original']['path'],'original-reader.bl')
copy('research/native-seed/src/native/scheme.bl','emitter.bl')
d=Path(m['directory'])
for name in ['native-module.json','exports.json']:copy(d/name,name)
copy(d/'unit.scm','unit.scm.gz',True)
request=Path(m['request'])
copy(request,'identity-request.json')
copy(request.with_name(request.name.replace('-request','-result')),'identity-result.json')
copy(next(request.parent.glob('build-*-result.json')),'build.json')
(a.output/'files.json').write_text(json.dumps(files,indent=2)+'\n')
print('SCAN_EVIDENCE_RETAINED')
