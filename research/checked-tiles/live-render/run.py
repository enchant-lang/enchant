"""One renderer process, a warm native self-compiler and an independent Source serving slot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import sys
from threading import Event, Thread
import time

HERE = Path(__file__).resolve().parent
TILES = HERE.parent
ROOT = TILES.parents[1]
FILM = ROOT / 'research/ora-intro-film/proof'
SEED = ROOT / 'research/native-seed'
TOOLS = json.loads((TILES / 'tools.json').read_text())
FRAME = 300
W, H = 1920, 1080


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def atomic(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_bytes(data)
    tmp.replace(path)


def write_json(path, value):
    atomic(path, (json.dumps(value, indent=2) + '\n').encode())


def elapsed(start):
    return round((time.perf_counter() - start) * 1000, 3)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def call(argv, cwd, env=None):
    result = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=180, text=True)
    check(result.returncode == 0, result.stdout[-3000:])
    return result.stdout


class Service:
    def __init__(self, argv, cwd, log, env=None):
        self.log = log.open('w')
        try:
            self.proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=self.log, text=True, bufsize=1)
        except BaseException:
            self.log.close()
            raise
        self.lines = Queue()
        def collect():
            for line in self.proc.stdout:
                if line.startswith('LIVE '):
                    self.lines.put(line[5:].rstrip('\n'))
                else:
                    self.log.write(line)
            self.lines.put(None)
        self.reader = Thread(target=collect, daemon=True)
        self.reader.start()

    def get(self):
        try:
            line = self.lines.get(timeout=180)
        except Empty:
            raise RuntimeError('Timed out waiting for ' + self.log.name) from None
        if line is None:
            self.log.flush()
            raise RuntimeError('Worker exited: ' + Path(self.log.name).read_text()[-2000:])
        return line

    def send(self, line):
        try:
            self.proc.stdin.write(line + '\n')
            self.proc.stdin.flush()
        except BrokenPipeError:
            self.log.flush()
            raise RuntimeError('Worker stopped: ' + Path(self.log.name).read_text()[-2000:]) from None

    def request(self, op, **kwargs):
        self.send(json.dumps(dict(op=op, **kwargs)))
        result = json.loads(self.get())
        check('failure' not in result, result)
        return result

    def close(self):
        try:
            self.proc.stdin.close()
        except BrokenPipeError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.reader.join()
        self.proc.stdout.close()
        self.log.close()


class Proofs:
    def __init__(self, out):
        self.dir = out / 'proofs'
        self.dir.mkdir()
        self.env = dict(os.environ, LEAN_PATH=str(self.dir))
        self.lean = TOOLS['lean']
        for name, src in [('Tiles', TILES / 'Tiles.lean'), ('Grade', HERE / 'Grade.lean')]:
            (self.dir / f'{name}.lean').write_bytes(src.read_bytes())
            call([self.lean, '-j2', '-o', name + '.olean', name + '.lean'], self.dir, self.env)
        self.static = sha((self.dir / 'Grade.olean').read_bytes() + (self.dir / 'Tiles.olean').read_bytes())
        self.cache = {}

    def qualify(self, values):
        check(len(values) == 256 and all(type(v) is int and v >= 0 for v in values), 'non-natural channel domain')
        key = sha(json.dumps([self.lean, self.static, values], separators=(',', ':')).encode())
        if key in self.cache:
            return dict(self.cache[key], reused=True)
        bad = next(([x, y] for x, y in enumerate(values) if not x <= y < 256), None)
        verdict = 'true' if bad is None else 'false'
        proof = ('import Grade\nset_option maxRecDepth 10000\nset_option maxHeartbeats 4000000\n'
                 f'def bytes : List Nat := {values}\n'
                 f'theorem verdict : FilmGrade.exactGrade bytes = {verdict} := by decide\n#print axioms verdict\n')
        if bad:
            x, y = bad
            proof += (f'theorem witness : bytes[{x}]? = some {y} ∧ ¬ CheckedTiles.BrightByte {x} {y} := by decide\n'
                      '#print axioms witness\n')
        src = self.dir / ('Grade_' + key + '.lean')
        src.write_text(proof)
        log = call([self.lean, '-j2', src.name], self.dir, self.env)
        check('sorryAx' not in log and 'verdict' in log, 'unclosed grade proof')
        self.cache[key] = dict(subject=key, static_olean=self.static, proof_sha256=sha(proof.encode()),
                               verdict=verdict, witness=bad, reused=False)
        return self.cache[key]


def native_table(service, name):
    row = service.get().split()
    check(row[:2] == ['TABLE', name] and len(row) == 258, 'incomplete native export: ' + str(row[:8]))
    return list(map(int, row[2:]))


def compiled(service, name):
    row = service.get().split()
    check(row[:2] == ['DEFS', name] and len(row) == 4, 'missing compile observation: ' + str(row))
    return dict(compiled=row[2].split(','), reused=[] if row[3] == '-' else row[3].split(',')), native_table(service, name)


def native_build(service, action, name, helper, entry):
    service.send(f'({action} {name} {json.dumps(str(helper))} {json.dumps(str(entry))})')


def materialize(out, name, helper, entry):
    folder = out / name
    folder.mkdir()
    part = folder / 'blend.bl'
    part.write_bytes(helper)
    path = folder / 'grade.bl'
    path.write_bytes(b'(ns ora-film.grade)\n' + helper + b'\n' + entry.read_bytes())
    return part, path


def run(out, edit, manual):
    out.mkdir()
    evidence = {'frame': FRAME, 'viewport': [W, H], 'clock': 'monotonic wall milliseconds',
                'revisions': {}, 'events': [], 'source_published': []}
    start = time.perf_counter()
    def event(name, **facts):
        evidence['events'].append(dict(event=name, ms=elapsed(start), **facts))

    def status(phase, visible):
        write_json(out / 'state.json', dict(phase=phase, visible=visible))
    status('warming', None)
    sdk = Path(TOOLS['sdk'])
    check(sha((sdk / 'artifact.json').read_bytes()) == TOOLS['descriptor_sha256'], 'journal SDK changed')
    donor = SEED / 'out/compiler-native-owner'
    receipt = json.loads((SEED / 'evidence/scheme-fixpoint/qualification.json').read_text())
    image_sha = next(x['executable_sha256'] for x in receipt['builds'] if x['stage'] == 'stage2')
    bundle_sha = next(v for k, v in receipt['inputs'].items() if k.endswith('/compiler-native-owner/bundle.scm'))
    check(receipt['stage2-stage3-byte-equal'] and sha((donor / 'stage2').read_bytes()) == image_sha
          and sha((donor / 'bundle.scm').read_bytes()) == bundle_sha, 'qualified native compiler drift')
    evidence['compiler'] = dict(stage2_sha256=image_sha, bundle_sha256=bundle_sha, sdk=str(sdk))
    worker = module(FILM / 'worker.py', 'live_ora_layers')
    gpu = module(ROOT / 'examples/scene-renderer/showcase_worker.py', 'live_scene_gpu')
    libs = Path('/nix/store/mj9klbkhzal0vc1aazsajrydkimhc0h2-libglvnd-1.7.0/lib')
    os.environ.setdefault('__EGL_VENDOR_LIBRARY_FILENAMES', '/run/opengl-driver/share/glvnd/egl_vendor.d/50_mesa.json')
    plan_path = FILM / 'evidence/plan.json.gz'
    plan_bytes = gzip.decompress(plan_path.read_bytes())
    check(sha(plan_bytes) == json.loads((FILM / 'evidence/report.json').read_text())['plan_sha256'],
          'film plan differs from captured plan')
    frame = worker.validate(json.loads(plan_bytes))['frames'][FRAME]
    del plan_bytes
    evidence['render_inputs'] = {p.name: sha(p.read_bytes()) for p in
                                 [plan_path, FILM / 'worker.py', Path(gpu.__file__), *sorted((FILM / 'shaders').glob('*'))]}
    entry = out / 'entry.bl'
    entry.write_bytes((HERE / 'entry.bl').read_bytes())
    a = materialize(out, 'A', (HERE / 'blend.bl').read_bytes(), entry)
    if edit is None:
        edit = HERE / 'edited.bl'
    with ExitStack() as lifetime:
        native = Service([donor / 'stage2', '--eval', HERE / 'compiler.scm', donor / 'bundle.scm'], ROOT, out / 'native.log')
        lifetime.callback(native.close)
        check(native.get() == 'READY', 'native session did not start')
        native.send(f'(prime {json.dumps(str(entry))})')
        check(native.get() == 'PRIMED pixel,channel-table', 'stable entries did not compile')
        event('native compiler ready', pid=native.proc.pid)
        owner = Service([sdk / 'bin/bl', '--cold', 'run', HERE / 'owner.bl'], ROOT, out / 'source.log',
                        env=dict(os.environ, BEAM_LISP_RELOAD='1', ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1'))
        lifetime.callback(owner.close)
        check(json.loads(owner.get()) == {'ready': True}, 'Source slot did not start')
        proofs = Proofs(out)
        draw, gpu_info = lifetime.enter_context(worker.open_renderer(gpu, FILM / 'shaders',
                                               os.environ.get('SCENE_EGL', str(libs / 'libEGL.so.1')),
                                               os.environ.get('SCENE_GLES', str(libs / 'libGLESv2.so.2'))))
        evidence['renderer'] = gpu_info
        pool = lifetime.enter_context(ThreadPoolExecutor(max_workers=1))

        def prepare(label, files):
            t = time.perf_counter()
            native_build(native, 'build', label, files[0], entry)
            reuse, values = compiled(native, label)
            emit_ms = elapsed(t)
            t = time.perf_counter()
            reference = owner.request('prepare', id=label, path=str(files[1]))
            check(reference['table'] == values, 'native vs ordinary prepared Source export differs')
            source_ms = elapsed(t)
            t = time.perf_counter()
            proof = proofs.qualify(values)
            row = dict(source_sha256=sha(files[1].read_bytes()), digest=reference['digest'], **reuse,
                       proof=proof, native_ms=emit_ms, source_prepare_and_observe_ms=source_ms, proof_ms=elapsed(t))
            evidence['revisions'][label] = row
            return row, values, reference['table']

        def render_accepted(label, row, values, expected):
            check(row['proof']['verdict'] == 'true', 'attempt to render unqualified grade')
            table = bytes(values)
            def grade(raw, w, h):
                result = worker.grade_rgba(raw, w, h, table)
                # Independent oracle uses the BEAM table on each channel.
                for k in range(4):
                    reference = raw[k::4]
                    if k < 3:
                        reference = reference.translate(bytes(expected))
                    check(result[k::4] == reference, 'ordinary frame differential failed')
                return result
            t = time.perf_counter()
            packed = draw(frame, grade)
            path = out / label / 'frame.png'
            gpu.png(path, packed, W, H)
            row.update(frame_sha256=sha(path.read_bytes()), rgba_sha256=sha(packed), render_and_png_ms=elapsed(t))

        def publish(label, row, previous):
            selected = owner.request('publish', id=label, expected=previous)
            check(selected == {'status': 'applied', 'digest': row['digest']}, selected)
            # The new frame exists in immutable storage before the serving slot flips.
            status('serving', label)
            evidence['source_published'].append(selected['digest'])

        row_a, values_a, ref_a = prepare('A', a)
        render_accepted('A', row_a, values_a, ref_a)
        publish('A', row_a, None)
        event('A visible', digest=row_a['digest'])
        for key in ('frame', 'compile'):
            check(owner.request('pin', ticket=key)['digest'] == row_a['digest'], 'wrong admission')
        started, resume = Event(), Event()
        def old_frame(raw, w, h):
            def finish():
                split = h // 2
                offset = 4*w*split
                table = bytes(values_a)
                top = worker.grade_rgba(raw[:offset], w, split, table)
                started.set()
                check(resume.wait(420), 'old frame barrier timed out')
                return top + worker.grade_rgba(raw[offset:], w, h-split, table)
            return pool.submit(finish)
        pending = draw(frame, old_frame)
        try:
            check(started.wait(15), 'A frame did not finish its first strip')
            native_build(native, 'hold', 'outstanding', a[0], entry)
            check(native.get() == 'PARKED native.scheme/ident', 'A compile did not reach native identifier emission')
            event('A frame and compile both pending')
            status('ready-to-save', 'A')
            if manual:
                limit = time.monotonic() + 180
                while not (out / 'save').exists():
                    check(time.monotonic() < limit, 'No save received within three minutes')
                    time.sleep(.025)
            status('saving', 'A')
            save = time.perf_counter()
            b = materialize(out, 'B', edit.read_bytes(), entry)
            event('B source saved')
            row_b, values_b, ref_b = prepare('B', b)
            check(row_b['proof']['verdict'] == 'true', 'requested B edit violates law: ' + str(row_b['proof']['witness']))
            render_accepted('B', row_b, values_b, ref_b)
            check(row_b['frame_sha256'] != row_a['frame_sha256'], 'edit has no visible effect on selected frame')
            publish('B', row_b, row_a['digest'])
            evidence['save_to_readable_png_ms'] = elapsed(save)
            check(owner.request('select')['digest'] == row_b['digest'], 'reader did not select B')
            event('B visible while A frame and compile pending')
            if manual:
                status('awaiting-display', 'B')
                limit = time.monotonic() + 60
                while not (out / 'displayed').exists():
                    check(time.monotonic() < limit, 'No decoded B frame acknowledged within one minute')
                    time.sleep(.025)
                event('browser acknowledged decoded B before old jobs resumed')
            status('checking-late-jobs', 'B')
        finally:
            resume.set()
        check(sha(pending.result()) == row_a['rgba_sha256'], 'old frame changed during save')
        check(owner.request('observe',ticket='frame')['table'] == values_a, 'old frame Source lease lost')
        stale_frame = owner.request('publish', id='A', expected=row_a['digest'])
        check(stale_frame == {'status': 'stale', 'digest': row_b['digest']}, stale_frame)
        evidence['late_frame_publication'] = stale_frame
        owner.request('release', ticket='frame')
        event('old frame discarded; compiler lease holds A')
        native.send('(resume)')
        _, old_values = compiled(native, 'outstanding')
        check(old_values == owner.request('observe',ticket='compile')['table'] == values_a, 'held compile mixed revisions')
        check(proofs.qualify(old_values)['reused'], 'unmodified table lost its evidence')
        stale = owner.request('publish', id='A', expected=row_a['digest'])
        check(stale == {'status': 'stale', 'digest': row_b['digest']}, stale)
        waiting = owner.request('retire', id='A')
        check(waiting['status'] == 'waiting', waiting)
        event('A retirement waiting on compile registration')
        evidence['late_compile_publication'] = stale
        owner.request('release',ticket='compile')
        retired = owner.request('retire',id='A')
        check(retired['status'] == 'retired', retired)
        event('old compile rejected by serving slot; A retired')
        for label in ('A', 'outstanding'):
            native.send(f'(drop {label})')
            check(native.get() == f'DROPPED {label} collected', 'native generation still reachable: ' + label)
        event('retired native environment roots collected')
        native_build(native, 'clean', 'cleanB', b[0], entry)
        clean_work, clean_values = compiled(native, 'cleanB')
        check(clean_values == values_b, 'warm edit differs from clean native compilation')
        evidence['clean_B'] = dict(**clean_work, same_values=True, proof_reused=proofs.qualify(clean_values)['reused'])
        bad = materialize(out, 'bad', (HERE / 'rejected.bl').read_bytes(), entry)
        broken, _, _ = prepare('bad', bad)
        check(broken['proof']['witness'] == [64, 63] and broken['proof']['verdict'] == 'false', 'missing rejection')
        still = owner.request('select')
        check(still['digest'] == row_b['digest'] and still['table'] == values_b, 'bad edit changed selection')
        check(sha((out/'B/frame.png').read_bytes()) == row_b['frame_sha256'], 'bad edit changed visible bytes')
        check(owner.request('retire', id='bad')['status'] == 'retired', 'rejected graph leak')
        packed_again = draw(frame, lambda raw, w, h: worker.grade_rgba(raw, w, h, bytes(still['table'])))
        check(sha(packed_again) == row_b['rgba_sha256'], 'fresh frame after rejection differs')
        evidence['after_rejection'] = dict(digest=still['digest'], fresh_rgba_sha256=sha(packed_again))
        event('bad edit rejected; new frame served from B')
        check(owner.request('close')['status'] == 'closed', 'slot shutdown failed')
        check(owner.request('retire', id='B')['status'] == 'retired', 'serving graph leaked at shutdown')
        for label in ('B', 'bad', 'cleanB'):
            native.send(f'(drop {label})')
            check(native.get() == f'DROPPED {label} collected', 'native root leak: ' + label)
        native.send('(stop)')
    evidence['status'] = 'passed'
    write_json(out / 'receipt.json', evidence)
    status('complete', 'B')
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='new session directory')
    parser.add_argument('--helper', type=Path, help='trusted local replacement defining mix-white')
    parser.add_argument('--wait-for-save', action='store_true', help='wait for the browser to signal the save')
    args = parser.parse_args()
    result = run(args.out.resolve(), args.helper, args.wait_for_save)
    print(f"Source save to readable film frame: {result['save_to_readable_png_ms']} ms. Receipt: {args.out / 'receipt.json'}")
