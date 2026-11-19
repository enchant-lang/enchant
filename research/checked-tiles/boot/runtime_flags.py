"""Change the C compilation of one qualified stage two without changing generated Scheme or C."""
import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

from field_pipeline import CLOCK, medians, rows
from run import IMAGE, QUAL, command, sexp, sha, write


def run(pipeline, out, host_report=None):
    out.mkdir()
    reference = json.loads((pipeline/'pipeline.json').read_text())
    q = json.loads(QUAL.read_text())
    expected = q['images']['stage2']
    sha(IMAGE/'stage2', expected)
    sha(IMAGE/'eval-prepared.scm', q['prepared_macro_bundle_sha256'])
    sha(pipeline/'reader.bl', reference['source_sha256'])
    build = json.loads((IMAGE/'full-native-build.json').read_text())
    stage = next(row for row in build['builds'] if row['stage']=='stage2')
    manifest = Path(stage['split_manifest'])
    sha(manifest, stage['split_manifest_sha256'])
    link = next(row['argv'] for row in build['runs'] if row['label']=='stage2-native-link')
    report = dict(image=expected, fixture=reference['source_sha256'], objects=[], runs=[], images={})
    def relink(name, replacements):
        args = [str(replacements.get(x, x)) for x in link]
        args[-1] = str(out/name)
        subprocess.run(args, check=True)
        report['images'][name] = sha(args[-1])
    relink('stock', {})
    sha(out/'stock', expected)
    source = (pipeline/'observer.scm').read_text().replace(sexp(str(pipeline)),sexp(str(out)))
    (out/'observer.scm').write_text(source.replace('(define (A-run)',CLOCK+'\n(define (A-run)'))
    def measure(arms):
        for name in [*arms,*reversed(arms)]:
            log = command([out/name,'--eval',out/'observer.scm',IMAGE/'eval-prepared.scm'],os.environ,
                          out/f'{len(report["runs"])}-{name}.log', timeout=180)
            if 'definitions 104 emit-failures 0' not in log or 'A3_DONE' not in log:
                raise ValueError('Incomplete job')
            report['runs'].append(dict(arm=name, output=sha(out/'native.scm',reference['runs'][0]['emitted_sha256']),
                                       wall_ms=rows(log,'WALL',1000),cpu_ms=rows(log,'CPU',1000)))
        report['cpu_medians_ms'] = {a:medians([t for r in report['runs'] if r['arm']==a for t in r['cpu_ms']])
                                    for a in report['images'] if any(r['arm']==a for r in report['runs'])}
        write(out/'runtime-flags.json',report)
        print(report['cpu_medians_ms'],flush=True)
    def compile_unit(unit, level):
        src = manifest.parent/unit['file']
        sha(src,unit['sha256'])
        sha(unit['c'],unit['c_sha256'])
        sha(unit['object'],unit['object_sha256'])
        flags = list(unit['c_flags'])
        if flags[0]!='-O0' or '-D___SINGLE_HOST' not in flags:
            raise ValueError('Unexpected baseline flags')
        flags[0] = level
        flags[flags.index('-D___SINGLE_HOST')] = '-D___MULTIPLE_HOSTS'
        obj = out/f'unit-{unit["ordinal"]}{level}.o'
        start = time.monotonic()
        command([link[0],*flags,'-c',unit['c'],'-o',obj],os.environ,obj.with_suffix('.log'),timeout=600)
        report['objects'].append(dict(unit=unit['ordinal'],scheme=unit['sha256'],c=unit['c_sha256'],
                      old=unit['object_sha256'],new=sha(obj),flags=flags,seconds=time.monotonic()-start))
        return obj
    host, = [u for u in stage['units'] if u['indivisible_ffi_host']]
    if host_report:
        saved = json.loads(host_report.read_text())
        if (saved['image'] != expected or saved['fixture'] != reference['source_sha256']
                or len(saved['objects']) != 2):
            raise ValueError('Wrong host experiment')
        for row in saved['objects']:
            if row['unit'] != host['ordinal'] or row['c'] != sha(host['c']) or row['old'] != sha(host['object']):
                raise ValueError('Wrong host object')
            level = row['flags'][0]
            flags = list(host['c_flags'])
            flags[0] = level
            flags[flags.index('-D___SINGLE_HOST')] = '-D___MULTIPLE_HOSTS'
            if level not in ('-O0','-O1') or row['flags'] != flags:
                raise ValueError('Wrong host C policy')
            obj = host_report.parent/f'unit-{host["ordinal"]}{level}.o'
            sha(obj,row['new'])
            relink('runtime'+level,{host['object']:obj})
            sha(out/('runtime'+level),saved['images']['runtime'+level])
            if level == '-O1': host_optimized = obj
        report.update(objects=saved['objects'],runs=saved['runs'],host_receipt=sha(host_report))
    else:
        for level in ['-O0','-O1']:
            obj = compile_unit(host,level)
            relink('runtime'+level,{host['object']:obj})
            if level=='-O1': host_optimized=obj
        measure(['stock','runtime-O0','runtime-O1'])
    # Change only procedures defined by the self-hosted compiler. Mixed
    # initializer/rt units and the emitter/reader keep their original flags.
    optimized = {}
    for unit in stage['units']:
        source = manifest.parent/unit['file']
        sha(source,unit['sha256'])
        targets = re.findall(r'^\(define (v_[0-9_]+)\$[0-9]+ \(lambda ',source.read_text(),re.M)
        owners = {''.join(chr(int(c)) for c in n[2:].split('_')).split('/')[0] for n in targets}
        if owners == {'compiler'}:
            optimized[unit['object']] = compile_unit(unit,'-O1')
    if not optimized: raise ValueError('No pure compiler units')
    relink('language-O1',optimized)
    relink('combined-O1',{**optimized,host['object']:host_optimized})
    measure(['stock','language-O1','combined-O1','runtime-O1'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--host-report',type=Path,help='Reuse both verified host experiments')
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve(),a.host_report.resolve() if a.host_report else None)
