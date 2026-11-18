#!/usr/bin/env python3
"""Prepare the A3 attribution run for a retained stage-1 image.

Starts no VM and no native process. Writes OUT/observer.scm (the --eval
payload), OUT/targets.scm (every linked BL slot and host procedure the
counting pass wraps) and OUT/preparation.json (argv and input digests).
The image and its Scheme are read only.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scheme_string(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def decode_ident(ident):
    # native.scheme/ident: "v" then "_<codepoint>" per character.
    return ''.join(chr(int(c)) for c in ident[2:].split('_'))


def targets(stage1_scm):
    text = stage1_scm.read_text()
    first_bl = text.index('\n(define v_')
    host_part = text[:first_bl]
    rows = []
    host = sorted(set(re.findall(r'^\(define \(?([^ ()\n]+)', host_part, re.M)))
    for name in host:
        if name.startswith(('v_', 'lv_')) or not re.fullmatch(r'[A-Za-z0-9!$%&*/:<=>?^_~+\-.@#]+', name):
            continue
        rows.append(('host', name, name))
    slots = re.findall(r'^\(define (v_[0-9_]+)\$([0-9]+|v|g) ', text, re.M)
    for ident, slot in slots:
        label = decode_ident(ident) + '/' + slot
        rows.append(('slot', ident + '$' + slot, label))
    body = '\n'.join('(list %s (quote %s) %s)' % (scheme_string(k), '|' + s + '|' if '$' in s else s,
                                                   scheme_string(l)) for k, s, l in rows)
    return '(list\n' + body + ')\n', {'host': len(host), 'slots': len(slots)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True, help='the real namespace, e.g. priv/boot/reader.bl')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reps', type=int, default=5)
    parser.add_argument('--interval', default='0.0005')
    parser.add_argument('--samples-only', action='store_true',
                        help='omit the separately instrumented, high-overhead exact call count pass')
    args = parser.parse_args()
    build, out = args.build.resolve(), args.out.resolve()
    if out.exists():
        parser.error('select a fresh output directory')
    out.mkdir(parents=True)
    here = Path(__file__).resolve().parent
    listing, sizes = targets(build / 'stage1.scm')
    (out / 'targets.scm').write_text(listing)
    observer = (here / 'native-attrib.scm.in').read_text()
    for key, value in {'@SOURCE@': scheme_string(str(args.source.resolve())),
                       '@BUNDLE@': scheme_string(str(build / 'bundle.scm')),
                       '@TARGETS@': scheme_string(str(out / 'targets.scm')),
                       '@OUT@': scheme_string(str(out)),
                       '@REPS@': str(args.reps), '@INTERVAL@': args.interval,
                       '@COUNTS@': '#f' if args.samples_only else '#t'}.items():
        observer = observer.replace(key, value)
    assert '@' not in re.sub(r'"[^"]*"', '', observer).replace('##', ''), 'unresolved placeholder'
    (out / 'observer.scm').write_text(observer)
    inputs = {str(p): digest(p) for p in [build / 'stage1', build / 'stage1.scm', build / 'bundle.scm',
                                          args.source.resolve(), here / 'native-attrib.scm.in',
                                          Path(__file__).resolve()]}
    result = {'schema': 'bl.native.a3-attribution-preparation', 'version': 1,
              'inputs': inputs, 'targets': sizes, 'reps': args.reps, 'interval': args.interval,
              'instrument_calls': not args.samples_only,
              'argv': [str(build / 'stage1'), '--eval', str(out / 'observer.scm'), str(build / 'bundle.scm')]}
    (out / 'preparation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['argv']))


if __name__ == '__main__':
    main()
