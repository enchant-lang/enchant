#!/usr/bin/env python3
"""One reproducible prototype: verified image exports, paired AOT artifacts, execution."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'research/native-seed'
HERE=BASE/'cutover'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def row(path):return {'path':str(path),'sha256':sha(path)}
def run(argv, **kwargs):return subprocess.run([str(x) for x in argv],cwd=ROOT,check=True,**kwargs)
def image_exports():
    directory=BASE/'out/cutover-image'
    ledger=directory/'exports.json'
    qualification=json.loads((BASE/'out/compiler-native-owner/full-native-build.json').read_text())
    stage=next(x for x in qualification['builds'] if x['stage']=='stage1')
    image=BASE/'out/compiler-native-owner/stage1'
    assert sha(image)==stage['executable_sha256']
    if ledger.exists():
        data=json.loads(ledger.read_text())
        assert data['schema']=='bl.native.observed-image-exports'
        assert data['image']==row(image)
        for field in ['image','observer','producer','log']:
            assert sha(data[field]['path'])==data[field]['sha256']
        return
    directory.mkdir(parents=True,exist_ok=True)
    bundle=BASE/'out/compiler-native-owner/bundle.scm'
    assert sha(bundle)==qualification['inputs'][str(bundle)]
    observer=directory/'observer.scm'
    observer.write_bytes((HERE/'export-image.scm').read_bytes()+b'\n'+bundle.read_bytes())
    log=directory/'exports.log'
    with log.open('w') as output:
        run(['systemd-run','--user','--quiet','--collect','--wait','--pipe','--working-directory='+str(ROOT),
             '--property=MemoryMax=1500M','--property=MemorySwapMax=0','--property=RuntimeMaxSec=60',
             image,'--eval',observer,bundle],stdout=output,stderr=subprocess.STDOUT,timeout=80)
    lines=log.read_text().splitlines()
    assert lines[-1]=='CUTOVER_EXPORTS_PASS'
    exports=sorted(set(s.split('\t',1)[1] for s in lines if s.startswith('CUTOVER_MFA\t')))
    ledger.write_text(json.dumps({'schema':'bl.native.observed-image-exports','image':row(image),
        'observer':row(observer),'producer':row(HERE/'export-image.scm'),'log':row(log),'exports':exports},indent=2)+'\n')
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('output',type=Path)
    args=ap.parse_args()
    output=args.output.resolve()
    image_exports()
    if not (output/'modules.json').exists():
        run([BASE/'run','--sdk-pin',BASE/'incremental-sdk-pin.json','run',HERE/'build.bl','--',output,
             *(['resume'] if output.exists() else [])],timeout=260)
    runtime=output/'runtime'
    if not (runtime/'preparation.json').exists():
        run([sys.executable,HERE/'prepare.py',output/'modules.json',runtime],timeout=180)
    run([sys.executable,HERE/'measure.py',runtime/'preparation.json'],timeout=130)
if __name__=='__main__':main()
