import argparse
import ctypes as C
import _ctypes
import weakref
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
from threading import Event, Lock
import time
import zlib
import struct

from region import compile_region
from opencl_device import Device, Unavailable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TOOLS = json.loads((HERE / 'tools.json').read_text())
DEFAULT_IMAGE = ROOT / 'research/ora-intro-film/proof/evidence/frame-300.png'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def command(*argv, cwd=None):
    p = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=180)
    if p.returncode:
        raise RuntimeError((p.stderr + p.stdout).decode(errors='replace')[-4000:])
    return p.stdout


def rgb_png(data, width, height):
    def chunk(name, payload):
        return struct.pack('>I', len(payload)) + name + payload + struct.pack('>I', zlib.crc32(name + payload))
    stride = width * 3
    scan = b''.join(b'\0' + data[i:i+stride] for i in range(0, len(data), stride))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(scan)) + chunk(b'IEND', b''))


def elapsed(start):
    return round((time.perf_counter() - start) * 1000, 6)


def timings(render, expected, count=5):
    samples = []
    for _ in range(count):
        start = time.perf_counter()
        got = render()
        samples.append(elapsed(start))
        require(got == expected, "frame differs from compiled BEAM reference")
    return {'samples_ms': samples, 'median_ms': statistics.median(samples)}


def check_backend(render, table):
    for w, h, tile in [(0, 3, 8), (4, 0, 8), (1, 1, 1), (16, 16, 4), (257, 1, 16), (17, 19, 8)]:
        data = bytes(i % 256 for i in range(w*h))
        actual = render(data, w, h, tile)
        expected = data.translate(table)
        require(len(actual) == len(expected), f"wrong output size at {w}x{h}")
        if actual != expected:
            i = next(i for i in range(len(data)) if actual[i] != expected[i])
            raise ValueError(f"{w}x{h} tile {tile}, channel ({i%w},{i//w}): "
                             f"{data[i]} became {actual[i]}, expected {expected[i]}")


class NativeRegion:
    """A request retaining this object also retains its ELF mapping."""
    def __init__(self, path):
        # libgomp workers can outlive the last region. Keep the shared runtime
        # mapped for the process lifetime; each region ELF can still retire.
        self.scheduler = C.CDLL(TOOLS['openmp'], mode=os.RTLD_NODELETE)
        self.library = C.CDLL(str(path))
        self.release = weakref.finalize(self, _ctypes.dlclose, self.library._handle)
        self.fn = self.library.render
        self.fn.argtypes = [C.c_char_p, C.c_void_p, C.c_uint, C.c_uint, C.c_uint, C.c_int]
        self.fn.restype = None

    def __call__(self, data, w, h, tile, threads=1):
        require(self.release.alive and len(data) == w*h and 0 <= w*h < 2**32
                and 1 <= tile <= 16, "invalid CPU launch")
        buf = C.create_string_buffer(len(data))
        self.fn(data, buf, w, h, tile, threads)
        return buf.raw


@dataclass
class Candidate:
    directory: Path
    table: bytes
    cpu: NativeRegion
    frame: bytes
    receipt: dict


class Rejected(ValueError):
    pass


def prepare(source, root, raw, args):
    t0 = time.perf_counter()
    c, lean, entry = compile_region(source)
    d = Path(tempfile.mkdtemp(prefix='revision-', dir=root))
    (d / 'source.bl').write_text(source)
    proof = (HERE / 'Tiles.lean').read_text()
    capture = (HERE / 'capture.bl').read_text()
    (d / 'capture.bl').write_text(source + '\n' + capture)
    sdk = Path(TOOLS['sdk'])
    require(digest((sdk / 'artifact.json').read_bytes()) == TOOLS['descriptor_sha256'], "SDK identity drift")
    command(sdk / 'bin/bl', '--cold', 'run', d / 'capture.bl', '--',
            root / 'input.rgb', d / 'observed.json', d / 'beam.rgb', cwd=ROOT)
    obs = json.loads((d / 'observed.json').read_text())
    require(obs['sdk'] == str(sdk) and len(obs['table']) == 256, "incomplete BEAM domain")
    beam_ms = elapsed(t0)
    require(all(type(v) is int and v >= 0 for v in obs['table']), 'non-natural observation')
    bad = next(((x, y) for x, y in enumerate(obs['table']) if not x <= y < 256), None)
    if bad is None:
        theorem = f"∀ x : Fin 256, CheckedTiles.BrightByte x.val ({entry} x.val)"
    else:
        x, y = bad
        theorem = f"{entry} {x} = {y} ∧ ¬ CheckedTiles.BrightByte {x} ({entry} {x})"
    proof += f"""
set_option maxRecDepth 10000
set_option maxHeartbeats 4000000
{lean}
def observed : List Nat := {obs['table']}
theorem observed_agrees : (List.range 256).map {entry} = observed := by decide
theorem channel_verdict : {theorem} := by decide
#print axioms channel_verdict
#print axioms CheckedTiles.launched
#print axioms observed_agrees
#print axioms CheckedTiles.stitch
#print axioms CheckedTiles.owner
#print axioms CheckedTiles.clipped
"""
    start = time.perf_counter()
    (d / 'Revision.lean').write_text(proof)
    verdict = command(TOOLS['lean'], d / 'Revision.lean').decode()
    require('sorryAx' not in verdict, 'proof contains an admission')
    (d / 'lean.txt').write_text(verdict)
    lean_ms = elapsed(start)
    if bad is not None:
        x, y = bad
        write_json(d/'rejected.json', {'input': x, 'output': y, 'proof': digest(proof.encode()),
                                        'source': digest(source.encode()), 'sdk': str(sdk)})
        raise Rejected(f"channel {x} returned {y}; Lean checked the violation of {x} ≤ output ≤ 255")
    table = bytes(obs['table'])
    ref = (d / 'beam.rgb').read_bytes()
    require(ref == raw.translate(table), "source frame disagrees with exhaustive channel observations")
    headers = c + f'\n#define PIXEL {entry}\n'
    cpu_source = headers + (HERE / 'cpu.c').read_text()
    gpu_source = headers + (HERE / 'tile.cl').read_text()
    (d / 'region.c').write_text(cpu_source)
    (d / 'region.cl').write_text(gpu_source)
    start = time.perf_counter()
    command(TOOLS['cc'], '-O3', '-fopenmp', '-shared', '-fPIC', d / 'region.c', '-o', d / 'region.so')
    cpu = NativeRegion(d / 'region.so')
    cpu_build_ms = elapsed(start)
    stride = args.width * 3
    identity = {name: digest((d / name).read_bytes()) for name in
                ('source.bl', 'capture.bl', 'Revision.lean', 'region.c', 'region.cl', 'region.so')}
    identity['tools.json'] = digest((HERE / 'tools.json').read_bytes())
    revision = digest(json.dumps(identity, sort_keys=True).encode())
    receipt = {'revision': revision, 'artifacts': identity, 'sdk': str(sdk), 'input_sha256': digest(raw),
               'width': args.width, 'height': args.height, 'tile': args.tile,
               'beam_frame_ms': obs['frame_us']/1000, 'beam_capture_process_ms': beam_ms,
               'lean_process_ms': lean_ms, 'cpu_compile_ms': cpu_build_ms, 'output_sha256': digest(ref),
               'law': 'all 256 channels brighten or preserve, remain bytes; checked model of tiled indexing',
               'reference': 'original BL compiled on BEAM', 'timings': {}}
    check_backend(cpu, table)
    for threads in (1, 4):
        receipt['timings'][f'cpu_{threads}'] = timings(lambda: cpu(raw, stride, args.height, args.tile, threads), ref)
    receipt['timings']['cpu_lookup'] = timings(lambda: raw.translate(table), ref)
    frame = cpu(raw, stride, args.height, args.tile, 4)
    receipt['backend'] = 'CPU / OpenMP'
    if args.sweep:
        # Independently checked table supplies the reference for larger repeated frames.
        receipt['sweep'] = {}
        def sweep(name, render):
            for w, h in ((24, 8), (960, 180), (5760, 1080)):
                size = w*h
                sample = (raw * ((size + len(raw) - 1)//len(raw)))[:size]
                result = sample.translate(table)
                row = receipt['sweep'].setdefault(f'{w} channels x {h} rows', {})
                row[name] = timings(lambda: render(sample, w, h, args.tile), result)
        sweep('cpu_4', lambda data, w, h, tile: cpu(data, w, h, tile, 4))
        sweep('cpu_lookup', lambda data, w, h, tile: data.translate(table))
    if not args.cpu_only:
        try:
            start = time.perf_counter()
            with Device(TOOLS['opencl'], gpu_source) as gpu:
                receipt['gpu_setup_ms'] = elapsed(start)
                receipt['gpu'] = gpu.info
                check_backend(gpu.render, table)
                if args.sweep:
                    sweep('gpu_whole_call', gpu.render)
                receipt['timings']['gpu_whole_call'] = timings(lambda: gpu.render(raw, stride, args.height, args.tile), ref)
                frame = gpu.render(raw, stride, args.height, args.tile)
                receipt['backend'] = 'OpenCL / ' + gpu.info['device']
        except Unavailable as exc:
            if args.require_gpu:
                raise
            receipt['gpu_unavailable'] = str(exc)
    if args.placement == 'measured':
        # The native/GPU paths have all been checked. Select from whole-call
        # times on this exact input; lookup is an executable finite specialization.
        # The GPU result above is retained until this decision.
        fastest = min(receipt['timings'], key=lambda k: receipt['timings'][k]['median_ms'])
        if fastest == 'cpu_lookup':
            frame = raw.translate(table)
        elif fastest in ('cpu_1', 'cpu_4'):
            frame = cpu(raw, stride, args.height, args.tile, int(fastest[-1]))
        receipt['backend'] = fastest if fastest != 'gpu_whole_call' else 'OpenCL / ' + receipt['gpu']['device']
    require(frame == ref, 'last render failed differential')
    (d / 'frame.png').write_bytes(rgb_png(frame, args.width, args.height))
    write_json(d / 'receipt.json', receipt)
    print(f"Checked {revision[:12]} on {receipt['backend']} ({elapsed(t0)} ms including preparation)", flush=True)
    return Candidate(d, table, cpu, frame, receipt)


class Publication:
    """One process owns one fresh session directory. Readers follow one rename."""
    def __init__(self, root):
        self.root = root
        self.active = None
        self.lock = Lock()

    def accept(self, revision):
        with self.lock:
            tmp = self.root / '.next'
            tmp.symlink_to(revision.directory.name)
            tmp.replace(self.root / 'current')
            self.active = revision

    def finish(self, revision, frame):
        require(frame == revision.frame, 'in-flight frame changed meaning')
        with self.lock:
            if revision is not self.active:
                return 'stale result discarded'
            path = revision.directory
            tmp = path / '.completed.png'
            tmp.write_bytes(rgb_png(frame, revision.receipt['width'], revision.receipt['height']))
            tmp.replace(path / 'frame.png')
            return 'current frame published'


def main():
    p = argparse.ArgumentParser(description='Compile, prove and render an ordinary BL channel definition.')
    p.add_argument('--source', type=Path, default=HERE/'examples/wash.bl')
    p.add_argument('--image', type=Path, default=DEFAULT_IMAGE)
    p.add_argument('--width', type=int, default=129)
    p.add_argument('--height', type=int, default=73)
    p.add_argument('--tile', type=int, choices=range(1, 17), default=8)
    p.add_argument('--sweep', action='store_true', help='also measure an 8x8 patch, 320x180 and 1920x1080 RGB')
    p.add_argument('--placement', choices=['measured', 'device'], default='measured')
    group = p.add_mutually_exclusive_group()
    group.add_argument('--cpu-only', action='store_true')
    group.add_argument('--require-gpu', action='store_true')
    group = p.add_mutually_exclusive_group()
    group.add_argument('--watch', action='store_true', help='recheck on each saved source edit')
    group.add_argument('--once', action='store_true', help='only build the selected source')
    p.add_argument('--out', type=Path, help='new output directory (default: fresh temporary directory)')
    args = p.parse_args()
    require(0 < args.width <= 1024 and 0 < args.height <= 1024, 'choose dimensions from 1 to 1024')
    root = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix='checked-tiles-'))
    if args.out:
        root.mkdir(parents=True, exist_ok=False)
    print(f'Session {root}', flush=True)
    raw = command('ffmpeg', '-nostdin', '-v', 'error', '-i', args.image, '-frames:v', '1',
                  '-vf', f'scale={args.width}:{args.height}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-threads', '1', '-')
    require(len(raw) == args.width*args.height*3, 'incomplete input frame')
    (root/'input.rgb').write_bytes(raw)
    (root/'original.png').write_bytes(rgb_png(raw, args.width, args.height))
    owner = Publication(root)
    source = args.source.read_text()
    first = prepare(source, root, raw, args)
    owner.accept(first)
    require(owner.finish(first, first.frame) == 'current frame published', 'current publication failed')
    print(f'Open {root}/current/frame.png', flush=True)
    if args.watch:
        del first
        while True:
            time.sleep(.4)
            try:
                candidate = args.source.read_text()
                if candidate == source:
                    continue
                source = candidate
                ready = prepare(source, root, raw, args)
                if args.source.read_text() == source:
                    owner.accept(ready)
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                print(f'Previous revision retained: {exc}', flush=True)
    if args.once:
        return
    started, resume = Event(), Event()
    def in_flight():
        # One owned request straddles activation. Pause between real native strips.
        stride = args.width*3
        rows = (args.height+1)//2
        cut = stride*rows
        top = first.cpu(raw[:cut], stride, rows, args.tile)
        started.set()
        require(resume.wait(300), "second strip timed out")
        tail = first.cpu(raw[cut:], stride, args.height-rows, args.tile)
        return owner.finish(first, top + tail)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(in_flight)
        try:
            require(started.wait(5), 'first strip did not finish')
            edited = source.replace('(quot (+ x 255) 2)', '(quot (+ (* 3 x) 255) 4)')
            if edited == source:
                edited = (HERE/'examples/wash.bl').read_text()
            second = prepare(edited, root, raw, args)
            owner.accept(second)
        finally:
            resume.set()
        stale = task.result()
    require(stale == 'stale result discarded', 'stale completion accepted')
    first.cpu.release()
    old_path = str(first.directory/'region.so')
    unmapped = old_path not in Path('/proc/self/maps').read_text()
    require(unmapped and not first.cpu.release.alive, 'retired region ELF is still mapped')
    third = prepare((HERE/'examples/poster.bl').read_text(), root, raw, args)
    owner.accept(third)
    try:
        prepare((HERE/'examples/broken.bl').read_text(), root, raw, args)
    except Rejected as exc:
        witness = str(exc)
    else:
        raise RuntimeError('broken edit passed')
    require((root/'current').resolve() == third.directory, 'rejection changed serving revision')
    trace = {'first': first.receipt['revision'], 'edited': second.receipt['revision'], 'in_flight': stale,
             'old_elf_released_after_join': unmapped, 'second_operation': third.receipt['revision'], 'rejected': witness,
             'serving': str((root/'current').resolve().name)}
    write_json(root/'exercise.json', trace)
    print(json.dumps(trace, indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
