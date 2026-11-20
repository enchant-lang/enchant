"""Qualify the native compiler on Chez against the recorded Gambit fixpoint.

Usage (repository root):
  python3 research/substrate-ab/chez-fixpoint.py --image research/native-seed/out/cutover-core-build-v3 \
      --work /tmp/chez-fixpoint

Gates, each checked against the Gambit qualification receipt (full-fixpoint.json):
  1. stage1 (v3 stage1.scm on Chez) runs the source corpus with the recorded output,
     with both the macro bundle and the prepared evaluation bundle.
  2. stage1 on Chez self-emits stage2 Scheme byte-identical to Gambit stage1's stage2.scm.
  3. stage2 built from that Chez-emitted Scheme runs the corpus identically and emits
     stage3 Scheme byte-identical to stage2 (fixpoint).
  4. The original actor corpus overlay passes all checks with the oracle's labels and
     traces at every budget, using the original driver's observe().
Timings for each command sit beside the recorded Gambit seconds."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = ROOT / 'research/native-seed'
spec = importlib.util.spec_from_file_location('fixpoint_full', SEED / 'fixpoint-full.py')
fixpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixpoint)
ENTRY, BUDGETS = fixpoint.ENTRY, fixpoint.BUDGETS


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True, type=Path)
    p.add_argument('--work', required=True, type=Path)
    p.add_argument('--level', default='2')
    p.add_argument('--skip-actors', action='store_true')
    a = p.parse_args()
    image, work = a.image.resolve(), a.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    receipt = json.loads((image / 'full-fixpoint.json').read_text())
    chez = shutil.which('scheme')
    if not chez:
        sys.exit('scheme (Chez) must be on PATH')
    env = dict(os.environ, AB_HERE=str(HERE))
    result = {'schema': 'bl.substrate-ab.chez-fixpoint.v1', 'image': str(image), 'level': a.level,
              'chez': chez, 'gambit_receipt_sha256': sha(image / 'full-fixpoint.json'),
              'builds': {}, 'runs': [], 'gates': {}}
    gambit_seconds = {r['label']: r['seconds'] for r in receipt['runs']}

    def save():
        (work / 'chez-fixpoint.json').write_text(json.dumps(result, indent=1))

    def build(name, scheme_source):
        ss, so = work / f'{name}.ss', work / f'{name}.so'
        t = time.perf_counter()
        subprocess.run([chez, '--script', str(HERE / 'translate.ss'), str(scheme_source), str(ss), str(work / 'host.c')],
                       check=True, env=env, stdout=subprocess.DEVNULL)
        translated = time.perf_counter() - t
        host = work / 'host.so'
        if not host.exists():
            text = (work / 'host.c').read_text()
            import re
            (work / 'host-export.c').write_text(re.sub(r'(?m)^static (.*bl_text_[a-z]+\()', r'\1', text))
            subprocess.run(['gcc', '-O2', '-shared', '-fPIC', '-o', str(host), str(work / 'host-export.c'), '-ldl'], check=True)
        t = time.perf_counter()
        # Compile without running the entry: native-main is the last form and runs at load.
        script = (f'(optimize-level {a.level}) (load-shared-object "{host}") (load "{HERE}/chez-shim.ss")'
                  f' (compile-file "{ss}" "{so}")')
        subprocess.run([chez, '-q'], input=script, text=True, check=True, env=env, stdout=subprocess.DEVNULL)
        compiled = time.perf_counter() - t
        launcher = work / f'{name}-run.ss'
        launcher.write_text(f'(load-shared-object "{host}")\n(load "{HERE}/chez-shim.ss")\n(load "{so}")\n')
        result['builds'][name] = {'source_sha256': sha(scheme_source), 'translate_s': translated, 'compile_s': compiled,
                                  'so_bytes': so.stat().st_size}
        print('built', name, f'translate {translated:.1f}s compile {compiled:.1f}s', flush=True)
        save()
        return launcher

    def run(label, launcher, args, *, extra_env=None, timeout=1200):
        t = time.perf_counter()
        r = subprocess.run([chez, '--script', str(launcher), *map(str, args)], cwd=ROOT, env={**env, **(extra_env or {})},
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        seconds = time.perf_counter() - t
        (work / f'{label}.log').write_bytes(r.stdout)
        row = {'label': label, 'exit': r.returncode, 'seconds': seconds, 'log_sha256': hashlib.sha256(r.stdout).hexdigest(),
               'gambit_seconds': gambit_seconds.get(label)}
        result['runs'].append(row)
        print(label, 'exit', r.returncode, f'{seconds:.2f}s', 'gambit', row['gambit_seconds'], flush=True)
        save()
        if r.returncode:
            raise RuntimeError(label + ' failed:\n' + r.stdout.decode(errors='replace')[-3000:])
        return r.stdout

    def gate(name, ok, detail=None):
        result['gates'][name] = {'pass': bool(ok), **({'detail': detail} if detail else {})}
        print('GATE', name, 'PASS' if ok else 'FAIL', detail or '', flush=True)
        save()
        if not ok:
            raise RuntimeError('gate failed: ' + name)

    corpus = SEED / 'fixtures/compiler-source.bl'
    expected_corpus = receipt['source_results']['stage1']['output_sha256']

    def source_gate(stage, launcher):
        out = run(f'{stage}-source-corpus', launcher, ['--eval', image / 'bundle.scm', corpus])
        gate(f'{stage}-source-corpus', hashlib.sha256(out).hexdigest() == expected_corpus)
        out = run(f'{stage}-prepared-source-corpus', launcher, ['--eval', image / 'eval-prepared.scm', corpus])
        gate(f'{stage}-prepared-source-corpus', hashlib.sha256(out).hexdigest() == expected_corpus)

    stage1 = build('stage1', image / 'stage1.scm')
    source_gate('stage1', stage1)
    stage2_src = work / 'stage2.scm'
    run('stage1-builds-stage2', stage1, ['--compile', image / 'bundle.scm', image / 'host.scm', stage2_src])
    gate('stage1-emits-gambit-stage2-bytes', stage2_src.read_bytes() == (image / 'stage2.scm').read_bytes(),
         sha(stage2_src))
    stage2 = build('stage2', stage2_src)
    source_gate('stage2', stage2)
    stage3_src = work / 'stage3.scm'
    run('stage2-builds-stage3', stage2, ['--compile', image / 'bundle.scm', image / 'host.scm', stage3_src])
    gate('stage2-stage3-byte-equal', stage3_src.read_bytes() == stage2_src.read_bytes(), sha(stage3_src))
    if not a.skip_actors:
        body = Path(receipt['actor_capture']['body']['path'])
        oracle = json.loads((image / 'actor-check/paired/oracle.json').read_text())
        for stage, src in (('stage1', image / 'stage1.scm'), ('stage2', stage2_src)):
            original = src.read_bytes()
            assert original.endswith(ENTRY)
            overlay = work / f'{stage}-actors.scm'
            overlay.write_bytes(original[:-len(ENTRY)] + b'\n' + body.read_bytes())
            launcher = build(f'{stage}-actors', overlay)
            for budget in BUDGETS:
                extra = {'NATIVE_ACTOR_BUDGET': budget}
                text = run(f'{stage}-actors-{budget}', launcher, [], extra_env=extra).decode()
                observed = fixpoint.observe(text, budget, 'NATIVE')
                expected = oracle['budgets'][budget]
                gate(f'{stage}-actors-{budget}', observed['labels'] == expected['labels']
                     and observed['traces'] == expected['traces'], f"{len(observed['labels'])} checks")
    result['status'] = 'qualified' if all(g['pass'] for g in result['gates'].values()) else 'failed'
    save()
    print('STATUS', result['status'])


if __name__ == '__main__':
    main()
