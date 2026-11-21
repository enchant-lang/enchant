"""Extract or replace the BL source of units in a native compiler bundle.

Usage:
  python3 bundle-src.py extract BUNDLE.scm DIR        # DIR/<ns>.bl per unit, plus DIR/units.json
  python3 bundle-src.py replace BUNDLE.scm DIR OUT.scm  # units whose DIR/<ns>.bl changed get new source

A bundle unit is `(bl-map ... (bl-key "ns") "<ns>" ... (bl-key "source") "<text>" ...)`,
with text encoded by native.scheme/text: \\" \\\\ \\n \\r \\t, \\xHH; for other controls,
everything else verbatim UTF-8. The native stage compiles each unit from that text
(native.bootstrap/prepare), so replacing it is how a compiler-source candidate is built
without a BEAM SDK. Only the source strings change; every other byte is kept.
"""
import hashlib, json, re, sys
from pathlib import Path

ESC = {'"': '"', '\\': '\\', 'n': '\n', 'r': '\r', 't': '\t'}


def decode(s, i):
    """Decode the Scheme string literal starting at s[i] == '"'; return (text, end index)."""
    assert s[i] == '"'
    out, i = [], i + 1
    while True:
        c = s[i]
        if c == '"':
            return ''.join(out), i + 1
        if c == '\\':
            n = s[i + 1]
            if n == 'x':
                j = s.index(';', i)
                out.append(chr(int(s[i + 2:j], 16))); i = j + 1; continue
            out.append(ESC[n]); i += 2; continue
        out.append(c); i += 1


def encode(text):
    parts = []
    for c in text:
        o = ord(c)
        if c == '"': parts.append('\\"')
        elif c == '\\': parts.append('\\\\')
        elif c == '\n': parts.append('\\n')
        elif c == '\r': parts.append('\\r')
        elif c == '\t': parts.append('\\t')
        elif o < 32 or o == 127: parts.append('\\x%x;' % o)
        else: parts.append(c)
    return '"' + ''.join(parts) + '"'


def units(s):
    """Yield (ns, path, source, start, end) for each unit's source literal."""
    for m in re.finditer(r'\(bl-key "ns"\) ', s):
        ns, after_ns = decode(s, m.end())
        k = s.index('(bl-key "source") ', after_ns)
        # the unit map's keys are sorted, so path and requires sit between ns and source
        path = re.search(r'\(bl-key "path"\) "([^"]*)"', s[after_ns:k])
        start = k + len('(bl-key "source") ')
        text, end = decode(s, start)
        yield ns, path.group(1) if path else None, text, start, end


def main():
    mode, bundle = sys.argv[1], Path(sys.argv[2])
    s = bundle.read_text()
    if mode == 'extract':
        out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        index = []
        for ns, path, text, _, _ in units(s):
            (out / f'{ns}.bl').write_text(text)
            index.append({'ns': ns, 'path': path, 'sha256': hashlib.sha256(text.encode()).hexdigest()})
        (out / 'units.json').write_text(json.dumps(index, indent=1))
        print(len(index), 'units')
    elif mode == 'replace':
        src, out = Path(sys.argv[3]), Path(sys.argv[4])
        pieces, at, changed = [], 0, []
        for ns, _, text, start, end in units(s):
            new = (src / f'{ns}.bl').read_text()
            if new != text:
                pieces.append(s[at:start]); pieces.append(encode(new)); at = end; changed.append(ns)
        pieces.append(s[at:])
        out.write_text(''.join(pieces))
        print(json.dumps({'changed': changed}))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
