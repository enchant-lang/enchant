"""Measure native compiler process and prelude reuse on fixed boot translations."""
import argparse
import json
import os
import statistics
import time
from pathlib import Path

from cutover_candidate import qualified
from run import BASE, HERE, ROOT, command, sexp, sha, write


def run(build, out):
    generation = qualified(build)
    out.mkdir()
    qualification = json.loads((HERE.parent/'evidence/boot-self-hosted-fields.json').read_text())
    worker = HERE/'reuse/translate.scm'
    image = build/'stage2'
    env = dict(os.environ, BL_REPEAT_BUNDLE=str(build/'eval-prepared.scm'))
    env.pop('BL_REPEAT_FIXED_BATCH', None)
    labels = ['reader', 'diag', 'reader']
    runs = []
    for index, arm in enumerate(['fresh', 'resident', 'resident', 'fresh']*2):
        trial = out / str(index)
        trial.mkdir()
        jobs = []
        for i, ns in enumerate(labels):
            label = f'priv/boot/{ns}.bl'
            path = ROOT/label if ns != 'reader' else BASE/'out/checked-boot-replay/pipeline/reader.bl'
            sha(path, qualification['jobs'][ns]['source'])
            job = trial/str(i)
            job.mkdir()
            (job/'source').write_bytes(path.read_bytes())
            (job/'selected').write_text('all\n')
            jobs.append([str(job), ns, label, 'staged'])
        batch = trial/'batch.scm'
        batch.write_text(sexp(jobs))
        args = [image, '--eval', worker, 'unused']
        start = time.monotonic_ns()
        if arm == 'resident':
            log = command(args, dict(env, BL_REPEAT_FIXED_BATCH=str(batch)), trial/'worker.log')
        else:
            log = ''.join(command(args, dict(env, BL_REPEAT_JOB=root, BL_REPEAT_NS=ns, BL_REPEAT_LABEL=label,
                        BL_REPEAT_ORDER=order), trial/f'worker-{i}.log')
                        for i, (root, ns, label, order) in enumerate(jobs))
        wall_ms = (time.monotonic_ns()-start)/1e6
        rows = [line.split() for line in log.splitlines()]
        if len(rows) != len(jobs):
            raise ValueError(f'Wrong request count in {trial}')
        samples = []
        for (root, ns, _, _), (definitions, micros) in zip(jobs, rows):
            reference = qualification['jobs'][ns]
            samples.append(dict(job=ns, defs=int(definitions), native_ms=int(micros)/1000,
                                output=sha(Path(root)/'result', reference['output'])))
        runs.append(dict(arm=arm, wall_ms=wall_ms, jobs=samples))
    result = {arm: statistics.median(row['wall_ms'] for row in runs if row['arm'] == arm)
              for arm in ('fresh', 'resident')}
    write(out/'workers.json', dict(generation=generation, worker=sha(worker), runs=runs, wall_ms=result))
    print(result, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=BASE/'out/checked-fields-build')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.build.resolve(), args.out.resolve())
