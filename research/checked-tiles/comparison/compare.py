"""Full-process CPU and device comparisons for the default white wash."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
PIN = '9c586f094f4fc88bef440dc8b4d77a2f92c257cc'


def run(args, cwd):
    start = time.perf_counter()
    proc = subprocess.run(args, cwd=cwd, capture_output=True, timeout=180)
    if proc.returncode:
        raise RuntimeError((proc.stderr + proc.stdout).decode(errors='replace'))
    return round((time.perf_counter() - start) * 1000, 3)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session', type=Path)
    p.add_argument('bend', type=Path, help='Bend source checkout at ' + PIN)
    p.add_argument('--require-gpu', action='store_true')
    args = p.parse_args()
    session = args.session.resolve()
    d = Path(tempfile.mkdtemp(prefix='comparison-', dir=session))
    root = args.bend.resolve()
    # Git blob identities from the pinned Bend tree also work with its release tarball.
    for name, want in json.loads((HERE/'bend-blobs.json').read_text()).items():
        buf = (root/name).read_bytes()
        got = hashlib.sha1(f'blob {len(buf)}\0'.encode() + buf).hexdigest()
        if want != got:
            raise ValueError(f'{name} differs from pinned Bend')
    raw = (session/'input.rgb').read_bytes()
    rev = next((r for r in session.glob('revision-*') if (r/'receipt.json').exists()
                and (r/'source.bl').read_bytes() == (HERE.parent/'examples/wash.bl').read_bytes()), None)
    if not rev:
        raise ValueError('session has no accepted default wash')
    expected = (rev/'beam.rgb').read_bytes()
    receipt = json.loads((rev/'receipt.json').read_text())
    if len(raw) > 3145728 or hashlib.sha256(raw).hexdigest() != receipt['input_sha256']:
        raise ValueError('input exceeds comparison size or no longer matches the receipt')
    (d/'input.rgb').write_bytes(raw)
    report = {'bend': PIN, 'input': receipt['input_sha256'], 'output': receipt['output_sha256'],
              'width': receipt['width'], 'height': receipt['height'],
              'timing': 'fresh process, input read, transform and output write; compiler measured separately',
              'implementation': '256-byte IO chunks; each has 32 fork/join leaves', 'runs': {}}
    compiler = [os.getenv('BUN','bun'), str(root/'bend2/main.ts'), str(HERE/'wash.bend'), '-o', str(d/'wash')]
    report['compile_ms'] = run(compiler, d)
    variants = {'Bend CPU 1': ['./wash', '+RTS', '--threads', '1', '--gpu', 'off'],
                'Bend CPU 4': ['./wash', '+RTS', '--threads', '4', '--gpu', 'off']}
    if (d/'wash.gpu').exists() or args.require_gpu:
        variants['Bend GPU required'] = ['./wash', '+RTS', '--threads', '4', '--gpu', '512MB']
    # Apply the same channel operation with the film worker's FFmpeg dependency.
    rule = '(val+255)/2'
    variants['FFmpeg lutrgb'] = ['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24',
                                 '-s', f"{receipt['width']}x{receipt['height']}", '-i','input.rgb',
                                 '-vf',f'lutrgb=r={rule}:g={rule}:b={rule}','-threads','1','-f','rawvideo','ffmpeg.rgb']
    variants['Enchant prepared CPU process'] = [sys.executable, '-B', HERE/'prepared.py', rev, 'cpu']
    if 'gpu' in receipt:
        variants['Enchant OpenCL process'] = [sys.executable, '-B', HERE/'prepared.py', rev, 'gpu']
    for i in range(5):
        names = list(variants)
        for name in names[i%len(names):] + names[:i%len(names)]:
            out = d/('prepared.rgb' if name.startswith('Enchant') else 'ffmpeg.rgb' if name.startswith('FFmpeg') else 'bend.rgb')
            out.unlink(missing_ok=True)
            ms = run(variants[name], d)
            if out.read_bytes() != expected:
                raise ValueError(f'{name} differs from BEAM frame')
            report['runs'].setdefault(name, []).append(ms)
    report['medians_ms'] = {k: statistics.median(v) for k,v in report['runs'].items()}
    (d/'comparison.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
