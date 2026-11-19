"""Count current Source declarations actually bound in the retained native stage."""
import argparse
import collections
import json
import os
from pathlib import Path

from run import HERE, ROOT, IMAGE, QUAL, command, sexp, sha, write


def tree(buf, pos=0):
    tag = chr(buf[pos])
    split = buf.index(b':', pos+1)
    length = int(buf[pos+1:split])
    pos = split+1
    if tag in 'SAI':
        return (tag, buf[pos:pos+length].decode()), pos+length
    if tag not in 'TLVMF':
        raise ValueError(tag)
    sub = []
    for _ in range(length):
        child, pos = tree(buf, pos)
        sub.append(child)
    return (tag, sub), pos


def unwrap(node):
    while node[0]=='T' and node[1][0]==('A','meta'):
        node=node[1][1]
    return node


def symbol(node):
    tag, items = unwrap(node)
    if tag=='T' and items[0]==('A','symbol'):
        return items[1][1]


def declarations(path):
    buf=path.read_bytes()
    outcome,end=tree(buf)
    if end!=len(buf) or outcome[1][0]!=('A','ok'):
        raise ValueError(f'Failed to decode complete oracle {path}')
    forms=outcome[1][1][1]
    ns=None
    names={}
    for form in forms:
        tag, items=unwrap(form)
        if tag!='T' or items[0]!=('A','list'):
            continue
        parts=items[1][1]
        if len(parts)<2: continue
        head,name=symbol(parts[0]),symbol(parts[1])
        if head=='ns': ns=name
        if head in ('def','defn','defn-','defmacro','defmacro-') and name:
            names[name]=head
    return ns,names


def audit(session,out):
    out.mkdir()
    receipt=json.loads((session/'reader.json').read_text())
    if receipt['smoke']: raise ValueError('Use a complete reader run')
    image=IMAGE/'stage2'
    qual=json.loads(QUAL.read_text())
    sha(image,qual['images']['stage2'])
    bundle=IMAGE/'eval-prepared.scm'
    sha(bundle,qual['prepared_macro_bundle_sha256'])
    jobs=json.loads((session/'jobs.json').read_text())
    entries={}
    files={}
    providers={p['path']:p['sha256'] for p in json.loads((IMAGE/'identity.json').read_text())['providers']}
    for job,result in zip(jobs,receipt['rows'],strict=True):
        path=job['label']
        if job['mode']!='read' or not path.startswith('priv/'): continue
        wire=session/('beam-'+job['id']+'.wire')
        sha(wire,result['beam_wire'])
        ns,names=declarations(wire)
        files[path]=dict(namespace=ns,definitions=len(names),source=result['source_sha256'],
                         image_provider=providers.get(path))
        if ns:
            for name,kind in names.items():
                key=ns+'/'+name
                if key in entries: raise ValueError('Duplicate qualified declaration: '+key)
                entries[key]=dict(path=path,kind=kind)
    (out/'names.scm').write_text(sexp([k.split('/',1) for k in entries]))
    env=dict(os.environ,BOOT_OUT=str(out),BOOT_BUNDLE=str(bundle))
    result=command([image,'--eval',HERE/'coverage.scm','unused'], env,out/'coverage.log')
    for line in result.splitlines():
        phase,key,value=line.split('\t')
        entries[key][phase]=value
    counts=collections.defaultdict(collections.Counter)
    for key,row in entries.items():
        if row['prepared'] not in ('image','missing','environment'): raise ValueError(key)
        counts[row['path']][row['prepared']]+=1
    for path,row in files.items():
        row['after_preparation']=dict(counts[path])
    artifact=dict(image=sha(image),prepared_bundle=sha(bundle),files=files,bindings=entries,
                  leaf_inventory=sha(IMAGE/'leaves.json'),
                  registered_leaves=len(json.loads((IMAGE/'leaves.json').read_text())['registered_leaves']))
    write(out/'coverage.json',artifact)
    for prefix in ('priv/boot/','priv/host/'):
        print(prefix,collections.Counter(v['prepared'] for v in entries.values() if v['path'].startswith(prefix)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('session',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    audit(a.session.resolve(),a.out.resolve())
