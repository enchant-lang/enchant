"""Serve the checked-tiles workstation experiment using only Python's standard library."""
import base64
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tempfile import TemporaryDirectory
from threading import Lock, Thread
from time import time
from urllib.parse import urlsplit
from uuid import uuid4

from region import compile_region, forms

HERE = Path(__file__).resolve().parent
PRESETS = {name: (HERE / 'examples' / (name + '.bl')).read_text()
           for name in ('wash', 'poster', 'broken')}
STATE = Path(os.environ.get('CHECKED_TILES_STATE', Path.home() / '.local/state/checked-tiles-web'))
ASSETS = {'/': ('index.html', 'text/html'), '/app.css': ('app.css', 'text/css'),
          '/app.js': ('app.js', 'text/javascript')}
HOSTS = {'localhost', '127.0.0.1', '::1', socket.gethostname().lower()}
HOSTS.update(h.strip().lower() for h in os.environ.get('CHECKED_TILES_HOSTS', '').split(',') if h)


def web_source(source):
    """Emit exactly the validated tree for BEAM and bound work per channel."""
    if not isinstance(source, str) or len(source.encode()) > 4096:
        raise ValueError('Use at most 4096 bytes of BL.')
    compile_region(source)
    trees = forms(source)
    if len(trees) > 8 or trees[-1][1] != 'pixel':
        raise ValueError('Define at most seven helpers, followed by pixel.')
    costs = {}

    def cost(node):
        if isinstance(node, str):
            return 1
        op, *args = node
        return 1 + costs.get(op, 0) + sum(cost(arg) for arg in args)

    def emit(node):
        if isinstance(node, str):
            return node
        left, right = ('[', ']') if isinstance(node, tuple) else ('(', ')')
        return left + ' '.join(map(emit, node)) + right

    for _, name, args, body in trees:
        if args != ('x',) or (name not in ('pixel', 'mix-white') and not name.startswith('tile-')):
            raise ValueError('Use [x] and name helpers mix-white or tile-… .')
        costs[name] = cost(body)
        if costs[name] > 128:
            raise ValueError('This expression exceeds the web runner’s work limit per channel.')
    return '\n'.join(map(emit, trees)) + '\n'


def image_url(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def snapshot(original, frame, receipt, source, proof, log, origin):
    return dict(original=image_url(original), frame=image_url(frame), receipt=json.loads(receipt.read_text()),
                source=source, proof=proof.read_text(), lean=log.read_text(), origin=origin)


def recorded():
    e = HERE / 'evidence'
    return snapshot(e/'original.png', e/'first.png', e/'first.json', PRESETS['wash'],
                    e/'Revision.lean', e/'lean.txt', 'Recorded example')


class Workbench:
    def __init__(self):
        self.lock = Lock()
        self.serial = 0
        self.epoch = uuid4().hex
        self.file = STATE / 'accepted.json'
        self.accepted = json.loads(self.file.read_text()) if self.file.exists() else recorded()
        self.job = {'status': 'ready'}

    def state(self, client_tag):
        with self.lock:
            tag = f'"{self.epoch}-{self.serial}"'
            payload = None if tag == client_tag else dict(accepted=self.accepted, job=self.job, presets=PRESETS)
            return tag, payload

    def start(self, req):
        mode, placement = req.get('mode'), req.get('placement')
        if mode not in ('edit', 'rehearsal', 'actors') or placement not in ('device', 'measured'):
            raise ValueError('Choose a supported experiment and placement.')
        source = web_source(req.get('source')) if mode == 'edit' else PRESETS['wash']
        with self.lock:
            if self.job['status'] == 'checking':
                raise BlockingIOError('A run is already checking on this workstation.')
            if mode != 'actors' and req.get('base') != self.accepted['receipt']['revision']:
                raise BlockingIOError('The accepted revision changed. Review the frame and try again.')
            self.job = dict(id=uuid4().hex, mode=mode, placement=placement, status='checking', started=time())
            self.serial += 1
            job = self.job.copy()
        Thread(target=self.run, args=(job, source), daemon=True).start()
        return job

    def run(self, job, source):
        accepted = None
        try:
            with TemporaryDirectory(prefix='checked-tiles-web-') as tmp:
                draft, out = Path(tmp)/'candidate.bl', Path(tmp)/'out'
                draft.write_text(source)
                argv = [sys.executable, '-B', str(HERE/'driver.py'), '--out', str(out),
                        '--source', str(draft), '--placement', job['placement']]
                if job['mode'] == 'actors':
                    argv = [sys.executable, '-B', str(HERE/'actor-lab/run.py'), '--quick', '--out', str(out)]
                elif job['mode'] == 'edit':
                    argv.append('--once')
                if job['mode'] != 'actors' and job['placement'] == 'device':
                    argv.append('--require-gpu')
                env = dict(os.environ, PATH=str(Path.home()/'.nix-profile/bin') + ':' + os.defpath
                           + ':' + os.environ.get('PATH', ''))
                with subprocess.Popen(argv, cwd=HERE, env=env, start_new_session=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True) as proc:
                    try:
                        log, _ = proc.communicate(timeout=600)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.communicate()
                        raise RuntimeError('Run exceeded the ten-minute workstation limit.')
                if job['mode'] == 'actors':
                    if proc.returncode:
                        raise RuntimeError(log.strip()[-3000:] or f'Native actor driver exited {proc.returncode}')
                    job.update(status='exercised', actors=json.loads(out.read_text()))
                    return
                witness = next(out.glob('revision-*/rejected.json'), None)
                if proc.returncode and witness and job['mode'] == 'edit':
                    job.update(status='rejected', witness=json.loads(witness.read_text()),
                               proof=witness.with_name('Revision.lean').read_text())
                elif proc.returncode:
                    raise RuntimeError(log.strip()[-3000:] or f'Driver exited {proc.returncode}')
                else:
                    d = out/'current'
                    if job['mode'] == 'rehearsal':
                        job['exercise'] = json.loads((out/'exercise.json').read_text())
                    candidate = snapshot(out/'original.png', d/'frame.png', d/'receipt.json',
                                         (d/'source.bl').read_text(), d/'Revision.lean', d/'lean.txt', 'Live run')
                    pending = self.file.with_suffix('.tmp')
                    pending.write_text(json.dumps(candidate))
                    pending.replace(self.file)
                    accepted = candidate
                    job['status'] = 'accepted'
        except Exception as exc:
            job.update(status='failed', error=str(exc))
        finally:
            with self.lock:
                if accepted is not None:
                    self.accepted = accepted
                self.job = dict(job, finished=time())
                self.serial += 1


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def send(self, status, data=b'', mime='application/json', tag=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; "
                         "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        if tag:
            self.send_header('ETag', tag)
        if status != 304:
            self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        try:
            return urlsplit('//' + self.headers.get('Host', '')).hostname in HOSTS
        except ValueError:
            return False

    def do_GET(self):
        if not self.valid_host():
            return self.send(403)
        if self.path == '/api/state':
            tag, state = self.server.bench.state(self.headers.get('If-None-Match'))
            return self.send(200, json.dumps(state).encode(), tag=tag) if state else self.send(304, tag=tag)
        asset = ASSETS.get(self.path)
        if not asset:
            return self.send(404)
        name, mime = asset
        self.send(200, (HERE/'web'/name).read_bytes(), mime + '; charset=utf-8')

    def do_POST(self):
        if self.path != '/api/runs':
            return self.send(404)
        if (not self.valid_host() or self.headers.get('X-Checked-Tiles') != '1'
                or self.headers.get('Sec-Fetch-Site') == 'cross-site'):
            return self.send(403)
        if self.headers.get_content_type() != 'application/json':
            return self.send(415)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 16384:
                return self.send(413)
            req = json.loads(self.rfile.read(size))
            if not isinstance(req, dict):
                raise ValueError('Expected a JSON object.')
            job = self.server.bench.start(req)
        except BlockingIOError as exc:
            return self.send(409, json.dumps({'error': str(exc)}).encode())
        except (ValueError, TypeError, RecursionError) as exc:
            return self.send(400, json.dumps({'error': str(exc)}).encode())
        self.send(202, json.dumps(job).encode())

    def log_request(self, code='-', size='-'):
        if self.path != '/api/state' or code not in (200, 304):
            super().log_request(code, size)


if __name__ == '__main__':
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE/'server.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with ThreadingHTTPServer((os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', 8765))), Handler) as http:
            http.bench = Workbench()
            print(f'Checked tiles listening at {http.server_address}', flush=True)
            http.serve_forever()
