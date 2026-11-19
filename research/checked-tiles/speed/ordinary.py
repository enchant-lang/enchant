"""Compile two ordinary .bl functions for the read-only packed-byte Cranelift port."""
import argparse
import json
import os
from pathlib import Path
import random
import statistics

from packed import run_arm
from run import HERE, ROOT, TOOLS, case, checked, job, sample, save

SOURCE_HASH = 'cc52bcdee649793457356ff32493b5a722a71a89150aef90b282c1b407b92e7e'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session', type=Path, help='completed speed/run output')
    p.add_argument('packed', type=Path, help='completed packed.py output')
    p.add_argument('--probe', type=Path, help='packed.py Cargo target/release/j1_probe')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir()
    bend = args.session.resolve() / 'bend'
    probe = (args.probe or args.packed / 'target/release/j1_probe').resolve()
    packed = json.loads((args.packed / 'receipt.json').read_text())
    checked(probe, packed['elf_sha256'])
    checked(bend, packed['bend_elf_sha256'])
    sdk = Path(TOOLS['sdk'])
    checked(sdk / 'artifact.json', TOOLS['descriptor_sha256'])
    source = HERE / 'byte-loops.bl'
    checked(source, SOURCE_HASH)
    proof = job([TOOLS['lean'], '-j2', HERE / 'Bytes.lean'])
    if 'sorryAx' in proof or 'ByteFold.scan_step' not in proof:
        raise ValueError('Open byte obligation')
    controls = [b'', b'/', b'0', b'9', b':', b'/09:99 2', b'7'*511,
                b'x9'*255, bytes(range(256)), bytes(reversed(range(256)))]
    save(out / 'controls.json', [list(b) for b in controls])
    modules = [ROOT / 'research/lowerers_spike/lower2.bl', source, HERE / 'byte-lower.bl']
    driver = out / 'driver.bl'
    driver.write_text('(ns speed.load (:require [system.footprint] [termination]))\n'
                      + '\n'.join(m.read_text() for m in modules))
    env = dict(os.environ, ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    env['LD_LIBRARY_PATH'] = '/run/opengl-driver/lib:' + env.get('LD_LIBRARY_PATH','')
    job([sdk / 'bin/bl','--cold','run',driver,'--',source,out], env=env, cwd=ROOT)
    expected = [[sample(k,len(b),0,b)[-1] for k in (5,3)] for b in controls]
    if expected != json.loads((out / 'answers.json').read_text()):
        raise ValueError('Source functions on BEAM disagree with independent answers')
    report = dict(proof=proof, cpu=packed['cpu'], sdk=TOOLS['descriptor_sha256'],
                  files={m.name:checked(m) for m in [*modules,HERE/'Bytes.lean',Path(__file__)]},
                  bend=checked(bend), probe=checked(probe), controls=expected, jobs={})
    for k, name in [(5,'grade'),(3,'scan')]:
        ir = out / (name + '.ir')
        divisor = int((out / (name + '.div')).read_text())
        runs = {'bend':[], 'enchant':[]}
        sizes = [0,64,4096,32768,65535]
        warm = [sample(k,len(b),0,b) for b in controls] + [case(k,n,1) for n in sizes]
        orders = []
        for block in range(4):
            rows = []
            for trial in range(5):
                batch = [case(k,n,13+block*17+trial) for n in sizes]
                random.Random(91+trial+block*7).shuffle(batch)
                rows.extend(batch)
            order = list(runs) if block % 2 == 0 else list(reversed(runs))
            orders.append(order)
            for arm in order:
                port = arm == 'enchant'
                cmd = [probe,'--serve-fold',ir] if port else [bend,'+RTS','--threads','1','--gpu','off']
                runs[arm].append(run_arm(cmd, port, env, warm+rows, len(warm),
                    out/f'{name}-{arm}-{block}.log', init_from_seed=False, divisor=divisor))
        report['jobs'][name] = dict(ir=ir.read_text(), ir_sha256=checked(ir), divisor=divisor,
            runs=runs, order=orders, medians_ms={arm:{n:statistics.median(
                x for row in results for x in row['ms'][n]) for n in sizes} for arm,results in runs.items()})
    save(out/'receipt.json',report)
    for name, row in report['jobs'].items():
        print(name, row['medians_ms'])


if __name__ == '__main__':
    main()
