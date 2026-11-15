#!/usr/bin/env python3
"""Archive the actual completed prototype; no execution or synthesized results."""
import argparse, gzip, hashlib, json, re
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('build',type=Path);ap.add_argument('runtime',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    files={}
    def copy(source,name,compress=False):
        data=source.read_bytes();dest=args.output/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(gzip.compress(data,mtime=0) if compress else data)
        files[name]={'source':str(source.resolve()),'sha256':sha(dest.read_bytes()),'source_sha256':sha(data),'gzip':compress}
    for name in ['preparation.json','native.log','reference.txt','candidate.txt']:
        copy(args.runtime/name,name)
    copy(args.build/'modules.json','modules.json')
    copy(args.build/'reader.bl','reader.bl')
    modules=json.loads((args.build/'modules.json').read_text())
    for row in modules['modules']:
        directory=Path(row['directory']);mode=row['mode']
        for name in ['native-module.json','exports.json']:
            copy(directory/name,mode+'/'+name)
        copy(directory/'unit.scm',mode+'/unit.scm.gz',True)
        request=Path(row['request'])
        copy(request,mode+'/identity-request.json')
        copy(request.with_name(request.name.replace('-request','-result')),mode+'/identity-result.json')
        build=next(request.parent.glob('build-*-result.json'))
        copy(build,mode+'/build.json')
    image=Path(__file__).resolve().parent.parent/'out/cutover-image'
    for name in ['exports.json','exports.log']:
        copy(image/name,'image/'+name)
    report=json.loads((args.runtime/'observation.json').read_text())
    assert report['passed'] and report['checks']==77
    log=(args.runtime/'native.log').read_text()
    allocations={}
    for label,block in re.findall(r'CUTOVER_ALLOCATION (reference|candidate)\n(.*?)(?=CUTOVER_|$)',log,re.S):
        found=re.search(r'(\d+) bytes allocated',block)
        if found:allocations[label]={'repetitions':5,'bytes':int(found.group(1)),'bytes_per_parse':int(found.group(1))/5}
    assert set(allocations)=={'reference','candidate'}
    report['allocations']=allocations
    report['reuse_build_jobs']={r['mode']:r['reuse-build-jobs'] for r in modules['modules']}
    report['conclusion']='Behavioral prototype passes; no demonstrated reader speed or allocation improvement; default remains reference.'
    report['interpretation']='The measured parse enters no generic pattern matcher; rebuilding only Reader removes 2493 of 108936 remote resolutions. Remaining traffic is outside this specialized module.'
    report['scope_limits']=['single serial private reader namespace; 27 reader corpora and explicit call/guard checks',
       'not native generation custody or concurrent publication','no proof of Gambit/native lowering',
       'does not qualify all supported pattern shapes or actor receive paths','one allocation batch per variant; shared host timings']
    (args.output/'observation.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.output/'files.json').write_text(json.dumps(files,indent=2)+'\n')
    print('CUTOVER_EVIDENCE',len(files),'files')
if __name__=='__main__':main()
