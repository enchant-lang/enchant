"""Classify link differences between BEAM closure-ANF emission (OUT/beam) and
the native image's source compile (OUT/native-before, OUT/native).
Usage: analyze-links.py OUT"""
import collections, re, sys
from pathlib import Path
out = Path(sys.argv[1])
pairs = re.findall(r'\(bl-vec \(list "([^"]*)" "([^"]*)"\)\)', (out / 'sample.scm').read_text())
CELL = re.compile(r'v_[0-9_]+\$(?:[0-9]+|v|g)\b')
def dec(t):
    m = re.match(r'v_([0-9_]+)(.*)', t)
    return ''.join(chr(int(c)) for c in m.group(1).strip('_').split('_') if c) + m.group(2)
for side in ('native-before', 'native'):
    classes = collections.Counter()
    for i, (ns, name) in enumerate(pairs):
        p = out / side / f'{i}.scm'
        if not p.exists():
            continue
        b = collections.Counter(dec(t) for t in CELL.findall((out / 'beam' / f'{i}.scm').read_text()))
        n = collections.Counter(dec(t) for t in CELL.findall(p.read_text()))
        for k in set(b) | set(n):
            if b[k] > n[k] and k.endswith('$g'):  # BEAM reads a global where native links
                target = k.split('/')[0]
                where = 'core' if target == 'core' else ('own-namespace' if target == ns else 'other-member')
                classes[f'BEAM global, native linked: {where}'] += b[k] - n[k]
            elif n[k] > b[k] and k.endswith('$g'):
                target = k.split('/')[0]
                where = 'core' if target == 'core' else ('own-namespace' if target == ns else 'other-member')
                classes[f'BEAM linked, native global: {where}'] += n[k] - b[k]
    print(f'CLASSES {side}: ' + ', '.join(f'{k}={v}' for k, v in sorted(classes.items())))
