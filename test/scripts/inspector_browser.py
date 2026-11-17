#!/usr/bin/env python3
"""Check the injected app inspector on one owned loopback preview."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
url, output_name = sys.argv[1:]
assert url.startswith('http://127.0.0.1:')
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
    reply = json.loads(exact(size))
    assert reply['ok'], reply
    return reply['result']


def evaluate(expression):
    return rpc('eval', expression=expression)


def wait(expression):
    return evaluate("""new Promise((resolve,reject)=>{
      const end=performance.now()+15000;
      function check(){if(%s)return resolve(true);
        if(performance.now()>end)return reject(Error('Condition did not settle'));
        setTimeout(check,40)}check()})""" % expression)


def action(name):
    evaluate("document.getElementById('enchant-inspector').shadowRoot.querySelector('[data-action=\"%s\"]').click()" % name)


try:
    rpc('open', width=1280, height=900, mobile=False)
    rpc('navigate', url=url + '/__enchant')
    wait("window.EnchantInspector && document.documentElement.dataset.live==='1'")
    assert evaluate("location.pathname==='/'")
    initial = evaluate("""(()=>{const h=document.getElementById('enchant-inspector'),r=h.getBoundingClientRect();
      return {...EnchantInspector.debug(),width:r.width,height:r.height,
        hosts:document.querySelectorAll('#enchant-inspector').length,
        hidden:h.shadowRoot.querySelector('.panel').hidden,
        overflow:document.documentElement.scrollWidth>innerWidth}})()""")
    assert initial['hosts'] == 1 and initial['hidden'] and not initial['overflow'], initial
    assert initial['height'] <= 42 and initial['width'] <= 260, initial
    assert initial['requests'] == 0 and not initial['pollScheduled'], initial
    rpc('screenshot', path=str(output / 'desktop.png'))

    rpc('click', selector='#demo-add')
    wait("document.getElementById('demo-count').innerText.trim()==='1'")
    wait('EnchantInspector.debug().frames>0')
    assert evaluate('EnchantInspector.debug().requests===0')

    action('pick')
    rpc('click', selector='#demo-add')
    assert evaluate("document.getElementById('demo-count').innerText.trim()==='1'")
    assert evaluate("document.getElementById('enchant-inspector').shadowRoot.querySelector('.tokens').children.length===4")
    assert evaluate("document.getElementById('enchant-inspector').shadowRoot.querySelector('.selection').innerText.includes('counter')")
    rpc('screenshot', path=str(output / 'loom-picker.png'))
    evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")

    action('paint')
    rpc('click', selector='#demo-add')
    wait("document.getElementById('demo-count').innerText.trim()==='2'")
    wait('EnchantInspector.debug().flashes>0')
    # Flood the existing event seam; retained frames and overlays stay bounded.
    bounded = evaluate("""(()=>{
      const ops=Array.from({length:10000},()=>['text',[],'unused']);
      for(let n=0;n<100;n++)document.dispatchEvent(new CustomEvent('live:patch',{detail:{root:Live.root,ops}}));
      return EnchantInspector.debug()})()""")
    assert bounded['frames'] == 32 and bounded['flashes'] <= 16, bounded
    assert bounded['requests'] == 0 and not bounded['pollScheduled'], bounded
    action('paint')

    # Hold a real-browser request to prove the one-flight and late-result rules.
    evaluate("""window.inspectorFetch=window.fetch;window.heldSamples=[];
      window.fetch=(...args)=>new Promise(resolve=>heldSamples.push({args,resolve}));""")
    action('server')
    for _ in range(20):
        evaluate("document.getElementById('enchant-inspector').shadowRoot.querySelector('[data-action=refresh]')?.click()")
    assert evaluate('heldSamples.length===1 && EnchantInspector.debug().activeRequests===1')
    action('close')
    evaluate("heldSamples[0].resolve({ok:true,json:async()=>({schema:'enchant.observatory.v1',runtime:{vm:{memory:99999999999}},work:[],projections:[]})})")
    wait('!EnchantInspector.debug().inFlight')
    assert evaluate('!EnchantInspector.debug().open && !EnchantInspector.debug().pollScheduled')
    evaluate('window.fetch=window.inspectorFetch')
    action('server')
    wait("!EnchantInspector.debug().inFlight && document.getElementById('enchant-inspector').shadowRoot.querySelector('.stats')")
    assert evaluate('EnchantInspector.debug().peakFlights===1')
    assert evaluate("!document.getElementById('enchant-inspector').shadowRoot.innerText.includes('95367 MB')")
    rpc('screenshot', path=str(output / 'server.png'))
    action('close')
    assert evaluate('!EnchantInspector.debug().pollScheduled')

    rpc('viewport', width=390, height=844, mobile=True)
    action('pick')
    rpc('click', selector='#demo-add')
    narrow = evaluate("""(()=>{const r=document.getElementById('enchant-inspector').shadowRoot.querySelector('.panel').getBoundingClientRect();
      return {overflow:document.documentElement.scrollWidth>innerWidth,width:r.width,left:r.left,right:r.right}})()""")
    assert not narrow['overflow'] and narrow['width'] <= 294 and narrow['left'] >= 0 and narrow['right'] <= 390, narrow
    rpc('screenshot', path=str(output / 'mobile.png'))
    evaluate('EnchantInspector.dispose();EnchantInspector.dispose()')
    assert evaluate('EnchantInspector.debug().disposed && !EnchantInspector.debug().pollScheduled && !EnchantInspector.debug().inFlight')
    assert evaluate("!document.getElementById('enchant-inspector-overlays')")
    record = dict(status='passed', url=url, initial=initial, bounded=bounded, narrow=narrow,
                  tests=['injected compact dock','real Live updates','read-only Loom picker',
                         '32 frames / 16 overlays','one in-flight sample','late result discarded',
                         'closed panel stops sampling','phone layout','idempotent disposal'],
                  screenshots=['desktop.png','loom-picker.png','server.png','mobile.png'],
                  check_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  driver_sha256=hashlib.sha256(driver.read_bytes()).hexdigest())
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
