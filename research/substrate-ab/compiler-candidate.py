"""Build and qualify a native compiler candidate from edited BL compiler source.

Usage (repository root):
  python3 research/substrate-ab/compiler-candidate.py --image QUALIFIED_IMAGE \
      --stage1 QUALIFIED_STAGE1_LAUNCHER --out OUT_DIR [--skip-actors]

The qualified image's bundle carries each compiler unit's BL source, and every unit
there is byte-identical to its file in this checkout. The candidate bundle takes each
unit's source from its checkout path (bundle-src.py's encoding); nothing else changes.

  1. The qualified stage 1 (on Chez) compiles the candidate bundle: S2.
  2. A candidate image holds S2 as stage1.scm and as the expected stage2.scm, so
     chez-fixpoint.py checks: S2 runs both source corpora with the recorded output;
     S2 compiles the candidate bundle into S2 again (the changed compiler emits what
     the qualified one emitted); stage2 = stage3; and the actor corpus at all budgets.
  3. S2 also compiles the ORIGINAL bundle into the qualified image's stage2.scm, byte
     for byte: the changed compiler gives the old compiler's output on the old input.
"""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('bundle_src', HERE / 'bundle-src.py')
bundle_src = importlib.util.module_from_spec(spec); spec.loader.exec_module(bundle_src)
ENTRY = '(native-main (native-command-line))\n'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--stage1', required=True, type=Path, help='Chez launcher (.ss) of the qualified stage 1')
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--skip-actors', action='store_true')
    a = p.parse_args()
    image, out = a.image.resolve(), a.out.resolve()
    out.mkdir(parents=True)
    env = dict(os.environ, AB_HERE=str(HERE))
    chez = shutil.which('scheme') or sys.exit('scheme (Chez) must be on PATH')
    receipt = {'schema': 'bl.substrate-ab.compiler-candidate.v1', 'image': str(image),
               'stage1': str(a.stage1), 'units': [], 'gates': {}}

    def save():
        (out / 'candidate.json').write_text(json.dumps(receipt, indent=1))

    # 1. candidate bundle from checkout sources
    text = (image / 'bundle.scm').read_text()
    pieces, at = [], 0
    for ns, path, source, start, end in bundle_src.units(text):
        new = (ROOT / path).read_text()
        if new != source:
            pieces += [text[at:start], bundle_src.encode(new)]; at = end
            receipt['units'].append({'ns': ns, 'path': path, 'old_sha256': hashlib.sha256(source.encode()).hexdigest(),
                                     'new_sha256': hashlib.sha256(new.encode()).hexdigest()})
    pieces.append(text[at:])
    bundle = out / 'bundle.scm'
    bundle.write_text(''.join(pieces))
    print('changed units', [u['ns'] for u in receipt['units']], flush=True)
    save()

    def compile_with(launcher, bundle_path, output, label):
        t = time.perf_counter()
        r = subprocess.run([chez, '--script', str(launcher), '--compile', str(bundle_path), str(image / 'host.scm'), str(output)],
                           cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1200)
        (out / f'{label}.log').write_bytes(r.stdout)
        receipt.setdefault('runs', []).append({'label': label, 'exit': r.returncode, 'seconds': time.perf_counter() - t})
        save()
        if r.returncode:
            sys.exit(f'{label} failed:\n' + r.stdout.decode(errors='replace')[-4000:])

    s2 = out / 'S2.scm'
    compile_with(a.stage1, bundle, s2, 'qualified-stage1-builds-S2')
    receipt['S2_sha256'] = sha(s2)

    # 2. candidate image for chez-fixpoint.py
    cand = out / 'image'; cand.mkdir()
    for f in image.iterdir():
        if f.name not in ('bundle.scm', 'stage1.scm', 'stage2.scm', 'stage3.scm', 'prelude.scm', 'derived.json'):
            (cand / f.name).symlink_to(f.resolve())
    (cand / 'bundle.scm').symlink_to(bundle)
    (cand / 'stage1.scm').symlink_to(s2)
    (cand / 'stage2.scm').symlink_to(s2)
    s2_text = s2.read_text()
    assert s2_text.endswith(ENTRY)
    (cand / 'prelude.scm').write_text(s2_text[:-len(ENTRY)])
    fix = out / 'fixpoint'
    cmd = [sys.executable, str(HERE / 'chez-fixpoint.py'), '--image', str(cand), '--work', str(fix)]
    if a.skip_actors:
        cmd.append('--skip-actors')
    r = subprocess.run(cmd, cwd=ROOT, env=env)
    gates = json.loads((fix / 'chez-fixpoint.json').read_text())
    receipt['gates'].update(gates['gates'])
    receipt['fixpoint_runs'] = gates['runs']
    save()
    if r.returncode or gates.get('status') != 'qualified':
        sys.exit('candidate fixpoint failed')

    # 3. new compiler, old input -> old output
    old_out = out / 'S2-on-original-bundle.scm'
    compile_with(fix / 'stage1-run.ss', image / 'bundle.scm', old_out, 'S2-builds-original-bundle')
    same = old_out.read_bytes() == (image / 'stage2.scm').read_bytes()
    receipt['gates']['candidate-on-original-bundle-emits-qualified-stage2'] = {'pass': same, 'detail': sha(old_out)}
    receipt['status'] = 'qualified' if same and all(g['pass'] for g in receipt['gates'].values()) else 'failed'
    save()
    print('STATUS', receipt['status'])
    if receipt['status'] != 'qualified':
        sys.exit(1)


if __name__ == '__main__':
    main()
