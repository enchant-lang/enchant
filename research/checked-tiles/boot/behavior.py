"""Exercise a real public entry from each newly emitted boot namespace."""
import argparse
import json
import os
from pathlib import Path
from run import HERE, IMAGE, QUAL, command, sha, write


def run(surface, out):
    out.mkdir()
    receipt = json.loads((surface/'surface.json').read_text())
    image = IMAGE/'stage2'
    sha(image, receipt['image'])
    bundle = IMAGE/'eval-prepared.scm'
    sha(bundle, json.loads(QUAL.read_text())['prepared_macro_bundle_sha256'])
    tools = json.loads((HERE.parent/'tools.json').read_text())
    sdk = Path(tools['sdk'])
    sha(sdk/'artifact.json',tools['descriptor_sha256'])
    # Tie the dynamically loaded products to the previous measurement.
    for ns,row in receipt['units'].items():
        obj, = (surface/ns).glob('*.o1')
        sha(obj,row['object'])
    env = dict(os.environ,BOOT_BUNDLE=str(bundle),BOOT_OUT=str(out),BOOT_OBJECTS=str(surface/'objects.scm'),
               BOOT_WIRE=str(HERE/'wire.scm'),BOOT_OBSERVATIONS=str(HERE/'observations.scm'),
               ELIXIR_ERL_OPTIONS='+S 2:2 +SDcpu 1:1 +SDio 1')
    driver = out/'oracle.bl'
    driver.write_text((HERE/'wire.bl').read_text()+'\n'+(HERE/'behavior.bl').read_text())
    command([sdk/'bin/bl','--cold','run',driver,'--',out],env,out/'beam.log')
    command([image,'--eval',HERE/'behavior.scm','unused'],env,out/'native.log')
    results = []
    for ns in receipt['units']:
        gold=(out/f'beam-{ns}.wire').read_text()
        value=(out/f'native-{ns}.wire').read_text()
        if not gold.startswith('L2:A2:ok'):
            raise ValueError('Oracle failed '+gold)
        results.append(dict(ns=ns,same=gold==value,beam=gold,native=value))
    write(out/'behavior.json',dict(image=sha(image),sdk=tools['descriptor_sha256'],surface=sha(surface/'surface.json'),
          probes=results,inputs={p:sha(HERE/p) for p in ('behavior.scm','behavior.bl','behavior.py')}))
    print([(r['ns'],r['same']) for r in results])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('surface',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    run(a.surface.resolve(),a.out.resolve())
