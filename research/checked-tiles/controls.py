"""Mutation controls against a retained session; leaves the serving revision intact."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from driver import Device, TOOLS, check_backend, compile_region, require


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session', type=Path)
    args = p.parse_args()
    revision = (args.session/'current').resolve()
    table = bytes(json.loads((revision/'observed.json').read_text())['table'])
    findings = {}
    for key, source in {
        'IO':'(defn pixel [x] (println x))',
        'overflow':'(defn pixel [x] (* 4294967295 x))',
        'neighbor':'(defn pixel [x] (binary/at x 1))',
        'nonliteral divisor':'(defn pixel [x] (quot 128 x))',
    }.items():
        try:
            compile_region(source)
        except ValueError as e:
            findings[key] = str(e)
        else:
            raise RuntimeError('unsound admission: ' + key)
    original = (revision/'region.cl').read_text()
    wrong = original.replace('PIXEL(src[i])', '(PIXEL(src[i]) ^ (x + 1 == width ? 1u : 0u))')
    require(original != wrong, 'GPU mutation missed')
    with Device(TOOLS['opencl'], wrong) as device:
        try:
            check_backend(device.render, table)
        except ValueError as e:
            findings['wrong GPU edge'] = str(e)
        else:
            raise RuntimeError('GPU mutation escaped')
    proof = (revision/'Revision.lean').read_text()
    changed = proof.replace('x % tw)', 'x % tw + 1)', 1)
    require(changed != proof, 'geometry mutation missed')
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'Shifted.lean'
        path.write_text(changed)
        result = subprocess.run([TOOLS['lean'], path], capture_output=True, text=True, timeout=180)
        require(result.returncode == 1 and 'unsolved goals' in result.stdout, 'unexpected Lean control outcome')
        findings['shifted tile model'] = 'Lean refused stitch: unsolved goals'
    require(revision == (args.session/'current').resolve(), 'mutation changed publication')
    (args.session/'controls.json').write_text(json.dumps(findings, indent=2)+'\n')
    print(json.dumps(findings, indent=2))


if __name__ == '__main__':
    main()
