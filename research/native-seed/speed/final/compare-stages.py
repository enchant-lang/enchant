#!/usr/bin/env python3
"""Compare stage1.scm (BEAM-emitted) with stage2.scm (native self-emission).

Prints the raw byte verdict, then the number of lines that still differ after
renaming gensym locals (`name_<n>`) per line in order of first appearance,
with the first few differing contexts.
Usage: compare-stages.py BUILD_DIR
"""
import re
import sys
from itertools import zip_longest
from pathlib import Path

LOCAL = re.compile(r'v(?:_\d+)+?_95(?:_(?:4[89]|5[0-7]))+\b')


def norm(text):
    out = []
    for line in text.split('\n'):
        names = {}
        out.append(LOCAL.sub(lambda m: names.setdefault(m.group(0), 'L%d' % len(names)), line))
    return out


build = Path(sys.argv[1])
a_text = (build / 'stage1.scm').read_text()
b_text = (build / 'stage2.scm').read_text()
print('BYTE_IDENTICAL' if a_text == b_text else 'BYTES_DIFFER')
a, b = norm(a_text), norm(b_text)
diff = [i for i, (x, y) in enumerate(zip_longest(a, b)) if x != y]
print('lines', len(a), len(b), 'differing after local renaming', len(diff))
for i in diff[:3]:
    x = a[i] if i < len(a) else "<missing line>"
    y = b[i] if i < len(b) else "<missing line>"
    j = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), min(len(x), len(y)))
    print(i, 'BEAM  :', x[max(0, j - 100):j + 100])
    print(i, 'native:', y[max(0, j - 100):j + 100])
sys.exit(bool(diff))
