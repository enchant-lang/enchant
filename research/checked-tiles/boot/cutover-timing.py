"""Compare independently qualified native generations on identical complete jobs."""
import argparse
import json
import os
from pathlib import Path

from cutover_candidate import qualified
from field_pipeline import CLOCK, medians, rows
from run import BASE, HERE, ROOT, command, sexp, sha, write


def run(baseline, candidate, out):
    out.mkdir()
    pipeline = BASE / 'out/checked-boot-replay/pipeline'
    template = (pipeline / 'observer.scm').read_text()
    selected = {'baseline': baseline, 'candidate': candidate}
    generations = {arm: qualified(build) for arm, build in selected.items()}
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
