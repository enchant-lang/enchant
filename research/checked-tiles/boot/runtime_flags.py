"""Change the C compilation of one qualified stage two without changing generated Scheme or C."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from field_pipeline import CLOCK, medians, rows
from run import IMAGE, QUAL, command, sexp, sha, write


def run(pipeline, out):
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
    optimized = {}
    for level in ['-O0','-O1']:
        replacements = {host['object']:compile_unit(host,level)}
        relink('runtime'+level,replacements)
        if level=='-O1': optimized.update(replacements)
    measure(['stock','runtime-O0','runtime-O1'])
    for unit in stage['units']:
        if unit is host: continue
        # Unit 1 is bundle metadata initialization alone, already finished at
        # the timing boundary. Retain each data-only object byte for byte.
        source = manifest.parent/unit['file']
        sha(source,unit['sha256'])
        if '(define v_' in source.read_text():
            optimized[unit['object']] = compile_unit(unit,'-O1')
    relink('compiler-O1',optimized)
    measure(['stock','runtime-O1','compiler-O1'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('pipeline',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    run(a.pipeline.resolve(),a.out.resolve())
