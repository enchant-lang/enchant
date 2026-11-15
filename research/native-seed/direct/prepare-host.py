#!/usr/bin/env python3
"""Assemble the direct compiler host once. Writes text only; starts no VM."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def quoted(text):
    return json.dumps(text, ensure_ascii=False)


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen-host', type=Path, default=base / 'out/compiler-closure/host.scm')
    parser.add_argument('--out', type=Path, default=base / 'out/direct-host')
    args = parser.parse_args()
    tools = json.loads((base / 'toolchain-pin.json').read_text())
    gambit, clang = Path(tools['gambit']), Path(tools['clang'])
    paths = [('frozen-host', args.frozen_host.resolve())] + [(role, base / 'direct' / filename) for role, filename in [
        ('direct-machine', 'direct-machine.scm'), ('source-control-frames', 'direct-control-frames.scm'),
        ('shared-raw-function', 'direct-shared-raw.scm'),
        ('deferred-static-mfa', 'direct-remote.scm'), ('external-function-peeling', 'direct-make-fun.scm'),
        ('dynamic-loader', 'direct-loader.scm'),
        ('clang-loader', 'direct-loader-clang.scm'), ('unit-host-services', 'host-direct-units.scm'),
        ('late-compiler-router', 'direct-router.scm')]]
    parts, components, inputs = [], [], {}
    for role, path in paths:
        data = path.read_bytes()
        if role == 'direct-machine' and data.count(b'(define native-c-action-abi 2)') != 1:
            raise RuntimeError('direct machine lacks action ABI2')
        if role == 'frozen-host' and b'native-raw-function?' not in data:
            raise RuntimeError('frozen host lacks the strict shared raw-function ABI')
        parts.append(data)
        components.append({'role': role, 'sha256': sha(data)})
        inputs[str(path)] = sha(data)
    header = base / 'direct/native-direct.h'
    if re.findall(r'^#define BL_NATIVE_DIRECT_ABI ([0-9]+)$', header.read_text(), re.MULTILINE) != ['2']:
        raise RuntimeError('direct header lacks its unique action ABI2 stamp')
    config = ('(native-c-require-action-abi! 2)\n(native-c-configure-clang! ' + ' '.join(map(quoted, [str(gambit / 'bin/gsc'),
        str(clang / 'bin/clang'), str(gambit / 'gambit/include'),
        str(gambit / 'gambit/bin/gambuild-C'), header.read_text()])) + ' 120000)\n'
        '(set! native-c-backend (bl-key "c"))\n').encode()
    parts.append(config)
    components.append({'role': 'pinned-compiler-configuration', 'sha256': sha(config)})
    host = b'\n'.join(parts) + b'\n'
    ledger = {'schema': 'bl.native.direct-host', 'version': 1, 'action-abi': 2,
              'source_sha256': sha(host), 'components': components}
    # Exactly the same owned data c-produce projects from the JSON companion.
    records = ' '.join('(bl-map (bl-key "role") ' + quoted(row['role']) +
                       ' (bl-key "sha256") ' + quoted(row['sha256']) + ')' for row in components)
    scheme = ('(bl-map (bl-key "schema") "bl.native.direct-host" (bl-key "version") 1 (bl-key "action-abi") 2 '
              '(bl-key "source-sha256") ' + quoted(ledger['source_sha256']) +
              ' (bl-key "components") (bl-vec (list ' + records + ')))\n')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'host.scm').write_bytes(host)
    (args.out / 'host.components.json').write_text(json.dumps(ledger, indent=2) + '\n')
    (args.out / 'host.components.scm').write_text(scheme)
    # Provenance is deliberately outside emitted compiler manifests. Output
    # directory paths therefore cannot spoil stage2/stage3 byte fixpoints.
    (args.out / 'preparation.json').write_text(json.dumps({'inputs': inputs,
        'toolchain': tools, 'action-abi': 2, 'header-action-abi': 2, 'header_sha256': sha(header.read_bytes()),
        'host_sha256': sha(host), 'status': 'assembled-not-executed'}, indent=2) + '\n')
    print('DIRECT_HOST_PREPARED ' + ledger['source_sha256'])


if __name__ == '__main__':
    main()
