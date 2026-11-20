"""Compare independently qualified native generations on identical complete jobs."""
import argparse
import json
import os
from pathlib import Path

from field_pipeline import CLOCK, medians, rows
from run import BASE, HERE, ROOT, command, sexp, sha, write


def inputs(build):
    path = build / 'full-fixpoint.json'
    receipt = json.loads(path.read_text())
    if (receipt['status'] != 'qualified' or not receipt['stage2-stage3-byte-equal']
            or not receipt['stage3-built-and-executed']):
        raise ValueError(f'{build} lacks a completed native fixed point')
    s2 = receipt['source_results']['stage2']
    bundle = build / 'eval-prepared.scm'
    image = build / 'stage2'
    compiler = next(row['sha256'] for row in json.loads((build/'identity.json').read_text())['providers']
                    if row['path'] == 'priv/boot/compiler.bl')
    return dict(image=sha(image, s2['image_sha256']),
                bundle=sha(bundle, s2['prepared_eval_bundle_sha256']),
                qualification=sha(path), compiler_source=compiler)


def run(baseline, candidate, out):
    out.mkdir()
    pipeline = BASE / 'out/checked-boot-replay/pipeline'
    template = (pipeline / 'observer.scm').read_text()
    selected = {'baseline': baseline, 'candidate': candidate}
    generations = {arm: inputs(build) for arm, build in selected.items()}
    if generations['baseline']['compiler_source'] == generations['candidate']['compiler_source']:
        raise ValueError('The two generations contain identical compiler Source')
    qualification = json.loads((HERE.parent/'evidence/boot-self-hosted-fields.json').read_text())
    report = dict(generations=generations, jobs={})
    for namespace in ('reader', 'anf', 'diag'):
        label = f'priv/boot/{namespace}.bl'
        source = pipeline/'reader.bl' if namespace == 'reader' else ROOT/label
        reference = qualification['jobs'][namespace]
        sha(source, reference['source'])
        job = out/namespace
        job.mkdir()
        rounds = []
        for arm in ('baseline', 'candidate', 'candidate', 'baseline'):
            observer = (template.replace(sexp(str(pipeline/'reader.bl')), sexp(str(source)))
                        .replace(sexp(str(pipeline)), sexp(str(job)))
                        .replace('(define A-ns "reader")', '(define A-ns '+sexp(namespace)+')')
                        .replace('"priv/boot/reader.bl"', sexp(label)))
            # Use one macro bundle across arms so this intervention isolates
            # the compiler generation during the measured job.
            bundle = baseline/'eval-prepared.scm'
            declaration = next(line for line in observer.splitlines() if line.startswith('(define A-bundle-path '))
            observer = observer.replace(declaration, f'(define A-bundle-path {sexp(str(bundle))})')
            path = job/'observer.scm'
            path.write_text(observer.replace('(define (A-run)', CLOCK+'\n(define (A-run)'))
            log = command([selected[arm]/'stage2','--eval',path,'unused'], os.environ,
                          job/f'{len(rounds)}-{arm}.log')
            if 'A3_DONE' not in log or 'emit-failures 0' not in log:
                raise ValueError(f'Incomplete translation of {label}')
            rounds.append(dict(arm=arm, output=sha(job/'native.scm', reference['output']),
                               wall_ms=rows(log,'WALL',1000), cpu_ms=rows(log,'CPU',1000)))
        report['jobs'][namespace] = dict(source=reference['source'], runs=rounds,
            cpu_medians_ms={arm:medians([sample for row in rounds if row['arm']==arm for sample in row['cpu_ms']])
                            for arm in selected})
        write(out/'timing.json', report)
        print(namespace, report['jobs'][namespace]['cpu_medians_ms'], flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--baseline', type=Path, default=BASE/'out/checked-fields-build')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.baseline.resolve(), args.candidate.resolve(), args.out.resolve())
