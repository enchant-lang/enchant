"""Gambit vs Chez vs warm BEAM on the journal's matched reader.bl translation.

Usage (repository root):
  python3 research/substrate-ab/compare.py --image research/native-seed/out/cutover-core-build-v3 \
      --work /tmp/ab-work --out /tmp/ab-compare

Gambit runs the qualified stage-2 image. Chez runs the same prelude.scm,
translated by translate.ss and compiled at optimize-level 2. BEAM runs the
pinned SDK through speed/attrib/beam-attrib.bl with the image's pinned native
emitter sources, exactly as checked-tiles/boot/pipeline.py does. Each arm
times REPS warm rounds inside one process; the emitted Scheme must be
byte-identical across arms."""
import argparse, hashlib, json, os, re, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ATTR = ROOT / 'research/native-seed/speed/attrib'
TOOLS = ROOT / 'research/checked-tiles/tools.json'
FIXTURE = '93a224b6b74fb52209e9f13b913a459f8b5cfef10f73f9173d3f2143653102ef'
REV = '507346397e954cff891fca4382a6f32ee47e9d78'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_at(path, expected):
    local = ROOT / path
    if local.exists() and sha(local) == expected:
        return local.read_bytes()
    for rev in subprocess.check_output(['git', 'log', '-120', '--format=%H', '--', path], cwd=ROOT, text=True).split():
        data = subprocess.check_output(['git', 'show', f'{rev}:{path}'], cwd=ROOT)
        if hashlib.sha256(data).hexdigest() == expected:
            return data
    raise ValueError('missing qualified source ' + path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--work', required=True, type=Path, help='Chez translation and build directory')
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--reps', type=int, default=8)
    a = p.parse_args()
    image, work, out = a.image.resolve(), a.work.resolve(), a.out.resolve()
    out.mkdir(parents=True)
    work.mkdir(parents=True, exist_ok=True)
    inp = out / 'in'
    inp.mkdir()
    (inp / 'reader.bl').write_bytes(subprocess.check_output(['git', 'show', f'{REV}:priv/boot/reader.bl'], cwd=ROOT))
    assert sha(inp / 'reader.bl') == FIXTURE
    (inp / 'eval-prepared.scm').write_bytes((image / 'eval-prepared.scm').read_bytes())
    ns = out / 'pinned/native'
    ns.mkdir(parents=True)
    for prov in json.loads((image / 'identity.json').read_text())['providers']:
        if prov['path'].startswith('research/native-seed/src/native/'):
            (ns / Path(prov['path']).name).write_bytes(source_at(prov['path'], prov['sha256']))
    sdk = Path(json.loads(TOOLS.read_text())['sdk'])
    chez = ['nix', 'shell', 'nixpkgs#chez', 'nixpkgs#gcc', '--command']
    if not (work / 'prelude.ss').exists():
        subprocess.run([*chez, 'scheme', '--script', str(HERE / 'translate.ss'), str(image / 'prelude.scm'),
                        str(work / 'prelude.ss'), str(work / 'host.c')], check=True)
    subprocess.run([*chez, str(HERE / 'run-chez.sh'), 'compile2', str(work), str(inp), str(out / 'chez-build'), '1'],
                   check=True, stdout=open(out / 'chez-build.log', 'w'), stderr=subprocess.STDOUT)
    arms = {
        'gambit': [str(HERE / 'run-gambit.sh'), str(image / 'stage2'), str(inp), None, str(a.reps)],
        'chez': [*chez, str(HERE / 'run-chez.sh'), 'compile2', str(work), str(inp), None, str(a.reps)],
        'beam': [str(sdk / 'bin/bl'), '--cold', '-p', str(ns.parent), 'run', str(ATTR / 'beam-attrib.bl'), '--',
                 str(inp / 'reader.bl'), None, str(a.reps), 'snapshot', 'timing'],
    }
    env = dict(os.environ, ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    runs = []
    for block, order in enumerate([['gambit', 'chez', 'beam'], ['beam', 'chez', 'gambit']]):
        for name in order:
            d = out / f'{name}-{block}'
            d.mkdir()
            cmd = [str(d) if x is None else x for x in arms[name]]
            t = time.perf_counter()
            log = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
            (d / 'log.txt').write_text(log.stdout + log.stderr)
            text = log.stdout + log.stderr
            if name == 'beam':
                rows = [[float(v) / 1000 for v in l.split()[1:]] for l in text.splitlines() if l.startswith('A3_TIMING_US ')]
                emitted = d / 'beam.scm'
            else:
                rows = [[float(v) for v in l.split()[1:]] for l in text.splitlines() if l.startswith('AB_TIMING_MS ')]
                emitted = d / 'emitted.scm'
            if len(rows) != a.reps or not re.search(r'definitions 104 emit-failures 0', text):
                raise RuntimeError(f'{name} incomplete:\n' + text[-1500:])
            runs.append(dict(arm=name, block=block, timings_ms=rows, emitted_sha256=sha(emitted),
                             process_s=time.perf_counter() - t))
            print(name, block, [round(sum(r)) for r in rows], sha(emitted)[:12], flush=True)
    med = {}
    for name in arms:
        rows = [r for x in runs if x['arm'] == name for r in x['timings_ms']]
        med[name] = dict(zip(['read', 'compile', 'emit'], [statistics.median(c) for c in zip(*rows)]),
                         total=statistics.median(map(sum, rows)))
    result = dict(schema='bl.substrate-ab.v1', image=str(image), stage2_sha256=sha(image / 'stage2'),
                  prelude_sha256=sha(image / 'prelude.scm'), chez_prelude_ss_sha256=sha(work / 'prelude.ss'),
                  sdk=str(sdk), fixture_sha256=FIXTURE, host=os.uname().nodename, reps=a.reps, runs=runs,
                  medians_ms=med, same_emitted_bytes=len({r['emitted_sha256'] for r in runs}) == 1)
    (out / 'compare.json').write_text(json.dumps(result, indent=1))
    print(json.dumps(dict(medians_ms=med, same_emitted_bytes=result['same_emitted_bytes']), indent=1))


if __name__ == '__main__':
    main()
