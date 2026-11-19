"""Run matched, version-bound native and BEAM reader jobs from the checkout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT/'research/native-seed'
IMAGE = BASE/'out/native-prepared-eval-build'
QUAL = BASE/'speed/attrib/raw/native-prepared-eval-qualification.json'
HOST_VALUES = BASE/'host/host-values.scm'
sys.path.insert(0, str(BASE))
import native_elf
import native_module


def sha(path, expected=None):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if expected and expected != digest:
        raise ValueError(f'Pinned input differs: {path}')
    return digest


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def sexp(value):
    if isinstance(value, list):
        return '('+' '.join(map(sexp,value))+')'
    if isinstance(value, int):
        return str(value)
    if not value.isascii():
        raise ValueError('Experiment path must be ASCII')
    return json.dumps(value)


def command(args, env, log, timeout=420):
    with log.open('wb') as sink:
        p = subprocess.run(args, stdout=sink, stderr=subprocess.STDOUT, env=env, cwd=ROOT, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'{args[0]} exited {p.returncode}: {log.read_text(errors="replace")[-1800:]}')
    return log.read_text(errors='replace')


def reader_leaf(path, name):
    source = path.read_text()
    start = source.index('(define (native-read-file path)')
    stop = source.index('(define (native-write-file', start)
    return source[start:stop].replace('(native-read-file path)', f'({name} path)', 1)


def transport_source():
    return ((HERE/'transport.scm').read_text()
            + reader_leaf(HOST_VALUES, 'boot-block-read-file')).encode()


def transport_object(out):
    cfg = native_elf.configuration(BASE, True, sha)
    cfg['flags'][0] = '-O2'
    cfg['tool_identity']['flags'] = cfg['flags']
    source = transport_source()
    def compile_step(label, argv, cwd, build):
        subprocess.run(argv,cwd=cwd,check=True,stdout=subprocess.DEVNULL,timeout=90)
    r = native_module.build_module(out/'transport', source, hashlib.sha256(source).hexdigest(), cfg,
            cache=out/'objects',report={},bind=sha,run=compile_step,save=lambda:None)
    return Path(r['artifacts']['module']['path'])


def inputs(out, smoke):
    paths = sorted((ROOT/'priv/boot').glob('*.bl'))
    if smoke:
        paths = [ROOT/'priv/boot/reader-node.bl']
    else:
        paths += sorted((ROOT/'priv/host').glob('*.bl'))
    rows=[]
    def add(path,label,mode,reps):
        rows.append(dict(id=f'{len(rows):03d}',path=str(path),label=label,mode=mode,reps=reps))
    for path in paths:
        label=str(path.relative_to(ROOT))
        add(path,label,'read',5 if label.startswith('priv/boot/') else 1)
        if path.name in ('reader.bl','reader-node.bl','core.bl','syntax.bl') and label.startswith('priv/boot/'):
            add(path,label,'syntax',3)
    fixtures=out/'fixtures'
    fixtures.mkdir()
    examples={'empty':'','positions':';α\r\n(foo [é 😀 é] {:id nil})\r\n#_ignored (next)\n',
              'literals':'#(list %1 %2) ^:private (quote a) \\newline 0xff 2.5',
              'bad-close':'(ok)\r\n[α }','unterminated':'(a "abc','multi':'first ; tail\n(second)\nthird',
              'raw':'#|raw text|','dispatch':'#?(:beam [1] :default [2])'}
    for name,src in examples.items():
        path=fixtures/(name+'.bl')
        path.write_bytes(src.encode())
        for mode in ['read','raw','syntax','stream']:
            add(path,'fixtures/'+name+'.bl',mode,1)
    return rows


def run(out,smoke):
    qual=json.loads(QUAL.read_text())
    tools=json.loads((HERE.parent/'tools.json').read_text())
    sdk=Path(tools['sdk'])
    image=IMAGE/'stage2'
    sha(image,qual['images']['stage2'])
    sha(IMAGE/'eval-prepared.scm',qual['prepared_macro_bundle_sha256'])
    sha(sdk/'artifact.json',tools['descriptor_sha256'])
    out.mkdir(mode=0o700)
    rows=inputs(out,smoke)
    write(out/'jobs.json',rows)
    (out/'jobs.scm').write_text(sexp([[r[k] for k in ('id','mode','path','label','reps')] for r in rows]))
    obj=transport_object(out)
    env=dict(os.environ,ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1',
             BOOT_OUT=str(out), BOOT_TRANSPORT=str(obj), BOOT_WIRE=str(HERE/'wire.scm'),
             BOOT_OBSERVATIONS=str(HERE/'observations.scm'))
    exe=lambda observer:[image,'--eval',HERE/observer,'unused']
    control=out/'control'
    control.mkdir()
    names=[]
    for name,payload in {'empty':b'', 'CRLF':b'a\r\nb\rc','nul':b'a\0b',
                         'nonbmp':'é😀é'.encode(), 'bad':b'a\xffz','truncated':b'a\xf0\x9f',
                         'across-buffer':b'A'*16383+'😀'.encode()+b'\r\nZ'}.items():
        (control/name).write_bytes(payload)
        names.append(str(control/name))
    names.append(str(control/'missing'))
    (out/'control.scm').write_text(sexp(names))
    env['BOOT_CONTROLS']=str(out/'control.scm')
    controls=command(exe('transport-control.scm'),env,out/'control.log').splitlines()
    print(f'{len(controls)} transport controls',flush=True)
    beam_driver=out/'oracle.bl'
    beam_driver.write_text((HERE/'wire.bl').read_text()+'\n'+(HERE/'beam.bl').read_text())
    beam=command([sdk/'bin/bl','--cold','run',beam_driver,'--',out],env,out/'beam.log')
    print('BEAM observations complete',flush=True)
    logs=command(exe('native.scm'),env,out/'native.log')
    values={r['id']:dict(source=r['label'],mode=r['mode'],source_sha256=sha(r['path']),
                         bytes=Path(r['path']).stat().st_size, timings_us={}) for r in rows}
    for line in beam.splitlines():
        if line.startswith('BEAM '):
            _,i,status,times=line.split(' ',3)
            samples=re.findall(r'\((\d+) (\d+)\)', times)
            if not samples: raise ValueError('Missing BEAM times: '+line)
            values[i]['beam_status']=status
            values[i]['timings_us']['beam.parse']=[int(m[0]) for m in samples]
            values[i]['beam_reductions']=[int(m[1]) for m in samples]
    for line in logs.splitlines():
        parts=line.strip().split('\t')
        if parts[0]=='RESULT':
            values[parts[1]]['native_status']=parts[2]
        elif parts[0] in ('PARSE','IO','TOTAL'):
            kind=parts[0].lower()+('.'+parts[2] if len(parts)==4 else '')
            values[parts[1]]['timings_us'].setdefault('native.'+kind,[]).append(float(parts[-1]))
    for i,row in values.items():
        a,b=(out/(engine+'-'+i+'.wire') for engine in ('beam','native'))
        row['beam_wire']=sha(a)
        row['native_wire']=sha(b)
        row['same']=row['beam_wire']==row['native_wire']
        if not row['same']:
            x,y=a.read_bytes(),b.read_bytes()
            start=next((i for i,(v,w) in enumerate(zip(x,y)) if v!=w),min(len(x),len(y)))
            row['first_difference']=dict(offset=start,beam=x[max(0,start-12):start+90].decode(errors='replace'),
                                         native=y[max(0,start-12):start+90].decode(errors='replace'))
        if not {'beam.parse','native.parse'}<=set(row['timings_us']): raise ValueError(i)
    receipt=dict(qualified_image=sha(image),sdk=tools['descriptor_sha256'],qualification=sha(QUAL),
          transport_object=sha(obj), cpu=next(l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),
          source={p.name:sha(p) for p in [HOST_VALUES,HERE/'run.py',HERE/'beam.bl',HERE/'native.scm',HERE/'transport.scm',HERE/'transport-control.scm',HERE/'wire.scm',HERE/'wire.bl',HERE/'observations.scm']},
          smoke=smoke, transport_controls=[line.replace(str(control)+'/','') for line in controls],rows=list(values.values()))
    write(out/'reader.json',receipt)
    print('Complete witnesses agree:',sum(r['same'] for r in values.values()),'/',len(values))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    run(args.out.resolve(),args.smoke)
