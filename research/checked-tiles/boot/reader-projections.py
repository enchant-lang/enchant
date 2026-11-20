"""Compare syntax and physical-event reader projections on fixed input bytes."""
import argparse
import hashlib
import os
import statistics
from pathlib import Path

from cutover_candidate import qualified
from run import HERE, ROOT, command, sexp, sha, write


def run(baseline, candidate, out):
    builds = {'baseline': baseline, 'candidate': candidate}
    identities = {arm: qualified(build) for arm, build in builds.items()}
    if identities['baseline']['image'] == identities['candidate']['image']:
        raise ValueError('The two images must be independent native generations')
    out.mkdir()
    cases = {'reader': (ROOT/'priv/boot/reader.bl').read_bytes(),
             'diag': (ROOT/'priv/boot/diag.bl').read_bytes(),
             'metadata': '; é\r\n(^:private name :kw 12 "é😀" #_discard thing)\n'.encode(),
             'prefix': b'(#(list %1) ~name (quote item) @x #{:k 2})\n',
             'bad-close': b'(ok)\r\n[abc }\n',
             'unclosed': b'(a "unclosed)'}
    jobs = []
    for name, data in cases.items():
        source = out / (name+'.bl')
        source.write_bytes(data)
        for mode in ('read', 'syntax', 'spans'):
            jobs.append((f'{name}-{mode}', mode, str(source), name+'.bl'))
    runs = []
    reference = {}
    for index, arm in enumerate(['baseline','candidate','candidate','baseline']):
        trial = out / str(index)
        trial.mkdir()
        (trial/'jobs.scm').write_text(sexp([list(row) for row in jobs]))
        env = dict(os.environ, BOOT_OUT=str(trial), BOOT_OBSERVATIONS=str(HERE/'observations.scm'),
                   BOOT_WIRE=str(HERE/'wire.scm'))
        log = command([builds[arm]/'stage2','--eval',HERE/'reader-projections.scm','unused'],
                      env, trial/'reader.log')
        times = {name: [] for name, *_ in jobs}
        for line in log.splitlines():
            _, name, value = line.split()
            times[name].append(float(value)/1000)
        for name, *_ in jobs:
            if len(times[name]) != 5:
                raise ValueError(f'Incomplete samples for {name}')
            witness = trial/(name+'.wire')
            digest = sha(witness)
            if digest != reference.setdefault(name, digest):
                raise ValueError(f'Reader observation changed for {name}. See {witness}')
        runs.append(dict(arm=arm, milliseconds=times))
    results = {name: {arm: statistics.median(t for r in runs if r['arm']==arm for t in r['milliseconds'][name])
                      for arm in builds} for name, *_ in jobs}
    write(out/'projections.json', dict(generations=identities,
          source={name: hashlib.sha256(data).hexdigest() for name,data in cases.items()},
          witness=reference, medians_ms=results, runs=runs))
    print({k: v for k, v in results.items() if k.startswith(('reader-', 'diag-'))}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.baseline.resolve(), args.candidate.resolve(), args.out.resolve())
