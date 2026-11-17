#!/usr/bin/env python3
"""Inspect a running loopback example with the repository's owned CDP driver.

Usage: python3 test/scripts/observatory_browser.py http://127.0.0.1:4056 OUTPUT
The caller owns the app listener; this check always disposes its browser.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
url, output_name = sys.argv[1:]
assert url.startswith('http://127.0.0.1:'), 'Use the owned loopback example'
output = Path(output_name).resolve()
output.mkdir(parents=True, exist_ok=True)
driver = ROOT / 'research/formal-logic/browser-driver.mjs'
browser = subprocess.Popen(['node', str(driver), str(output)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)


def exact(size):
    result = b''
    while len(result) < size:
        part = browser.stdout.read(size - len(result))
        if not part:
            raise RuntimeError('Browser driver exited early')
        result += part
    return result


def rpc(op, **options):
    body = json.dumps(dict(op=op, **options)).encode()
    browser.stdin.write(struct.pack('>I', len(body)) + body)
    browser.stdin.flush()
    size, = struct.unpack('>I', exact(4))
    assert size <= 1048576
    response = json.loads(exact(size))
    assert response['ok'], response
    return response['result']


try:
    rpc('open', width=1320, height=1050, mobile=False)
    rpc('navigate', url=url + '/')
    assert rpc('eval', expression="document.querySelector('a[href=\"/__enchant\"]')!==null")
    rpc('click', selector='a[href="/__enchant"]')
    desktop = rpc('eval', expression="""({
      title:document.title, instruments:document.querySelectorAll('.plate').length,
      overflow:document.documentElement.scrollWidth>innerWidth,
      scripts:document.scripts.length,
      manual:document.body.innerText.includes('no polling'),
      unknown:document.body.innerText.includes('not yet instrumented')
    })""")
    assert desktop['instruments'] == 5 and not desktop['overflow'], desktop
    assert desktop['scripts'] == 0 and desktop['manual'] and desktop['unknown'], desktop
    rpc('screenshot', path=str(output / 'desktop.png'))
    rpc('viewport', width=390, height=844, mobile=True)
    narrow = rpc('eval', expression="""({
      overflow:document.documentElement.scrollWidth>innerWidth,
      columns:getComputedStyle(document.querySelector('.grid')).gridTemplateColumns,
      navigation:[...document.querySelectorAll('nav a')].every(e=>e.getBoundingClientRect().width>40)
    })""")
    assert not narrow['overflow'] and narrow['navigation'], narrow
    assert len(narrow['columns'].split()) == 1, narrow
    rpc('screenshot', path=str(output / 'narrow.png'))
    rpc('click', selector='nav a[href="/__enchant"]')
    assert rpc('eval', expression="location.pathname==='/__enchant'")
    with urllib.request.urlopen(url + '/__enchant/snapshot.json', timeout=15) as response:
        sample = json.load(response)
        assert response.headers['Cache-Control'] == 'no-store'
    assert sample['schema'] == 'enchant.observatory.v1'
    assert all(row.get('demand') == 0 and row.get('counts', {}).get('started') == 0
               for row in sample['projections']), sample
    assert sample['projections'], 'Example must expose its real projection owner'
    record = dict(status='passed', url=url, desktop=desktop, narrow=narrow,
                  sample=sample, driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest(),
                  check_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output / 'browser.json').write_text(json.dumps(record, indent=2) + '\n')
    print(output / 'browser.json')
finally:
    try:
        rpc('stop')
    finally:
        browser.stdin.close()
        try:
            browser.wait(timeout=10)
        except subprocess.TimeoutExpired:
            browser.terminate()
            browser.wait(timeout=5)
