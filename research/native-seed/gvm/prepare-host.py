#!/usr/bin/env python3
"""Assemble a GVM-native host as text only. Starts no compiler or VM."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


QUALIFIED_HOST = 'd00c0c75a33cc4afc90315620d3039c48ed31464fdc0c32e5ac2841aa9d1ab8a'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def quoted(text):
    # Paths in this finite configuration must be ASCII. JSON's Unicode escape
    # spelling is not Scheme's; reject instead of silently changing a path.
    if any(not 32 <= ord(char) <= 126 for char in text):
        raise ValueError('finite host configuration requires printable ASCII strings')
    return json.dumps(text)


def main():
    here = Path(__file__).resolve()
    root = next(p for p in here.parents if (p / 'research/native-seed/toolchain-pin.json').is_file())
    base = root / 'research/native-seed'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen-host', type=Path, default=base / 'out/compiler-native-owner/host.scm')
    parser.add_argument('--out', type=Path, default=base / 'out/gvm-host')
    parser.add_argument('--python', type=Path, default=Path(shutil.which('python3')))
    args = parser.parse_args()
    tools_path = base / 'toolchain-pin.json'
    tools = json.loads(tools_path.read_text())
    python = args.python.resolve(strict=True)
    gvm = base / 'gvm'
    paths = [('frozen-host', args.frozen_host.resolve(strict=True))] + [
        (role, gvm / name) for role, name in (
            ('gvm-value-runtime', 'gvm-runtime.scm'),
            ('gvm-io', 'gvm-host-io.scm'),
            ('gvm-dynamic-loader', 'gvm-loader.scm'),
            ('gvm-entry-router', 'gvm-router.scm'))]
    inputs, parts, components = {}, [], []
    for role, path in paths:
        data = path.read_bytes()
        if role == 'frozen-host' and sha(data) != QUALIFIED_HOST:
            raise ValueError('GVM host requires the exact retained qualified value/compiler host')
        if role == 'gvm-value-runtime' and data.count(b'(define native-gvm-runtime-abi 1)') != 1:
            raise ValueError('GVM value runtime needs its unique ABI1 declaration')
        parts.append(data)
        inputs[str(path)] = sha(data)
        components.append({'role': role, 'sha256': sha(data)})
    backend_inputs = [python, gvm / 'build-module.py', gvm / 'import.scm',
                      gvm / 'reader-check.scm', tools_path]
    for path in backend_inputs:
        inputs[str(path)] = sha(path.read_bytes())
    if '--route' not in (gvm / 'build-module.py').read_text():
        raise ValueError('dynamic GVM loading requires the explicit C-only builder route')
    expected = '(list ' + ' '.join('(cons ' + quoted(str(path)) + ' ' +
                quoted(inputs[str(path)]) + ')' for path in backend_inputs) + ')'
    config = ('(native-gvm-require-runtime-abi! 1)\n'
              '(native-gvm-configure! ' + quoted(str(python)) + ' ' +
              quoted(str(gvm / 'build-module.py')) + ' ' + expected + ' 120000)\n').encode()
    parts.append(config)
    components.append({'role': 'pinned-backend-configuration', 'sha256': sha(config)})
    source = b'\n'.join(parts) + b'\n'
    ledger = {'schema': 'bl.native.gvm-host', 'version': 1, 'runtime-abi': 1,
              'source_sha256': sha(source), 'components': components}
    records = ' '.join('(bl-map (bl-key "role") ' + quoted(row['role']) +
                      ' (bl-key "sha256") ' + quoted(row['sha256']) + ')' for row in components)
    # bootstrap/data sorts keyword map keys by string; use that same finite
    # order and whitespace, so native and SDK ledger DATA are byte-identical.
    projection = ('(bl-map (bl-key "components") (bl-vec (list ' + records +
                  ')) (bl-key "runtime-abi") 1 (bl-key "schema") "bl.native.gvm-host" '
                  '(bl-key "source-sha256") ' + quoted(sha(source)) + ' (bl-key "version") 1)')
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'host.scm').write_bytes(source)
    (args.out / 'host.components.json').write_text(json.dumps(ledger, indent=2) + '\n')
    (args.out / 'host.components.scm').write_text(projection)
    (args.out / 'preparation.json').write_text(json.dumps({
        'schema': 'bl.native.gvm-host-preparation', 'version': 1,
        'status': 'assembled-not-executed', 'qualification': False,
        'inputs': inputs, 'preparer_sha256': sha(here.read_bytes()), 'toolchain': tools,
        'host_sha256': sha(source), 'runtime-abi': 1,
        'dynamic-route': 'c', 'dynamic-timeout-ms': 120000,
        'dynamic-address-space-bytes': 2147483648,
        'authored-scheme-bodies': False, 'gvm-interpreter': False,
        'source-interpreter': False, 'c-lambda-stepper': False,
    }, indent=2) + '\n')
    print('GVM_HOST_PREPARED ' + sha(source))


if __name__ == '__main__':
    main()
