"""Compare text input at equal C flags and replay source-owned boot effects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from run import BASE, HERE, IMAGE, QUAL, ROOT, command, native_elf, native_module, sexp, sha, write


def run(out):
    out.mkdir()
    qual = json.loads(QUAL.read_text())
    image = IMAGE / 'stage2'
    sha(image, qual['images']['stage2'])
    bundle = IMAGE / 'eval-prepared.scm'
    sha(bundle, qual['prepared_macro_bundle_sha256'])
    tools = json.loads((HERE.parent / 'tools.json').read_text())
    sdk = Path(tools['sdk'])
    sha(sdk / 'artifact.json', tools['descriptor_sha256'])
    env = dict(os.environ, BOOT_OUT=str(out), BOOT_BUNDLE=str(bundle),
               BOOT_WIRE=str(HERE/'wire.scm'), BOOT_OBSERVATIONS=str(HERE/'observations.scm'),
               ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    driver = out / 'oracle.bl'
    driver.write_text((HERE/'wire.bl').read_text() + '\n' + (HERE/'registry.bl').read_text())
    command([sdk/'bin/bl', '--cold', 'run', driver, '--', out], env, out/'beam.log')
    log = command([image, '--eval', HERE/'registry.scm', 'unused'], env, out/'registry.log')
    registry = []
    for phase in ('ordinary', 'seed', 'shadow'):
        for name in ('d', 'time'):
            ref = 'shadow' if phase == 'shadow' else 'ordinary'
            gold = (out/f'beam-{ref}-{name}.wire').read_text()
            value = (out/f'native-{phase}-{name}.wire').read_text()
            registry.append(dict(phase=phase, tag=name, equal=gold == value, beam=gold, native=value))
    # Copy the exact image implementation under another symbol. Only its name
    # changes. All three emitted controls now share one Gambit unit and flags.
    host = (IMAGE/'host.scm').read_text()
    start = host.index('(define (native-read-file path)')
    stock = host[start:host.index('(define (native-write-file', start)]
    source = (stock.replace('(native-read-file path)', '(boot-copy-read-file path)', 1)
              + (HERE/'transport.scm').read_text()).encode()
    cfg = native_elf.configuration(BASE, True, sha)
    cfg['flags'][0] = '-O2'
    cfg['tool_identity']['flags'] = cfg['flags']
    def cc(label, argv, cwd, build):
        subprocess.run(argv, cwd=cwd, check=True, capture_output=True, timeout=120)
    product = native_module.build_module(out/'module', source, hashlib.sha256(source).hexdigest(),
              cfg, cache=out/'objects', report={}, bind=sha, run=cc, save=lambda:None)['artifacts']['module']
    paths = sorted((ROOT/'priv/boot').glob('*.bl'))
    (out/'paths.scm').write_text(sexp([str(p.relative_to(ROOT)) for p in paths]))
    env.update(BOOT_TRANSPORT=product['path'], BOOT_PATHS=str(out/'paths.scm'))
    times = {}
    for line in command([image,'--eval',HERE/'io.scm','unused'], env, out/'io.log').splitlines():
        job, block, mode, us = line.split()
        times.setdefault(job, {}).setdefault(mode, []).append(float(us)/1000)
    assert len(paths) == 17 and all(len(v)==4 for g in times.values() for v in g.values())
    write(out/'boundary.json', dict(image=sha(image), sdk=tools['descriptor_sha256'], bundle=sha(bundle),
          stock_source=hashlib.sha256(stock.encode()).hexdigest(), native_module=product['sha256'],
          compiler_flags=cfg['flags'], files={p.name:sha(p) for p in paths},
          inputs={p:sha(HERE/p) for p in ('registry.bl','registry.scm','io.scm','transport.scm','observations.scm')},
          registrations=registry, activation_log=log, timings_ms=times))
    print([(r['phase'], r['tag'], r['equal']) for r in registry])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out.resolve())
