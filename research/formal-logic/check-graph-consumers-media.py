"""Actual declared PNG bytes, browser wait bound and undeclared-media refusals."""
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

P = Path(__file__).resolve().parent
E = P / 'evidence/graph-consumers'
base = 'http://127.0.0.1:24089'
checks = []
for step in (3, 5):
    path = '/witness-media/formal-browser-witness/frame-' + str(step) + '.png'
    started = time.monotonic()
    with urllib.request.urlopen(base + path, timeout=6) as response:
        body = response.read()
        status = response.status
        mime = response.headers.get_content_type()
    elapsed = time.monotonic() - started
    actual = hashlib.sha256(body).hexdigest()
    expected = hashlib.sha256((P / 'evidence/story/walkthrough/frames' / ('frame-' + str(step) + '.png')).read_bytes()).hexdigest()
    assert status == 200 and mime == 'image/png' and body.startswith(bytes.fromhex('89504e47'))
    assert actual == expected and elapsed < 6, (path, elapsed)
    checks.append({'path': path, 'status': status, 'sha256': actual, 'seconds': round(elapsed, 3)})
for path in ('/witness-media/formal-browser-witness/frame-999.png',
             '/witness-media/missing-witness/frame-5.png',
             '/witness-media/formal-browser-witness/frame-0.png'):
    try:
        urllib.request.urlopen(base + path, timeout=6)
        raise AssertionError('undeclared media accepted: ' + path)
    except urllib.error.HTTPError as error:
        assert error.code == 404
        checks.append({'path': path, 'status': error.code})
report = {'status': 'passed', 'browser_wait_seconds': 6, 'checks': checks,
          'scope': 'Actual local media routes on the capped dossier host; two exact recorded PNGs and three undeclared-media refusals.'}
(E / 'media-checks.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'checks': len(checks), 'png_seconds': [row['seconds'] for row in checks[:2]]}))
