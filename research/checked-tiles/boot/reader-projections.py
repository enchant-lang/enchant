"""Compare syntax and physical-event reader projections on fixed input bytes."""
import argparse
import hashlib
import json
import os
import statistics
from pathlib import Path

from cutover_candidate import qualified
from run import HERE, ROOT, command, sexp, sha, write


def run(baseline, candidate, out, sdk):
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
    jobs_path = out/'jobs.json'
    write(jobs_path, jobs)
    beam = None
    if sdk:
        original = ROOT/'priv/boot/reader.bl'
        source = original.read_text()
        header = '(ns reader\n'
        if source.count(header) != 1:
            raise ValueError('Unexpected candidate reader header')
        namespace = out/'overlay/cutover'
        namespace.mkdir(parents=True)
        (namespace/'reader.bl').write_text(source.replace(header, '(ns cutover.reader\n', 1))
        env = dict(os.environ, ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
        command([sdk/'bin/bl', '--cold', '-p', namespace.parent, 'run', HERE/'reader-projections.bl',
                 '--', out, jobs_path], env, out/'beam.log')
        beam = dict(sdk=sha(sdk/'artifact.json'), reader_source=sha(original),
                    runs=json.loads((out/'beam.json').read_text()))
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
          witness=reference, medians_ms=results, runs=runs, beam_overlay=beam))
    print({k: v for k, v in results.items() if k.startswith(('reader-', 'diag-'))}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--sdk', type=Path, help='Also check the candidate reader Source on this immutable SDK')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.baseline.resolve(), args.candidate.resolve(), args.out.resolve(), args.sdk.resolve() if args.sdk else None)
