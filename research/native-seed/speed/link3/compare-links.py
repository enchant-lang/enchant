"""Compare link decisions of sampled definitions: BEAM closure ANF emission
(OUT/beam) against the native image's source compile (OUT/native-before,
OUT/native). Usage: compare-links.py OUT"""
import collections, re, sys
from pathlib import Path

out = Path(sys.argv[1])
CELL = re.compile(r'v_[0-9_]+\$(?:[0-9]+|v|g)\b')
LEAF = re.compile(r'\blv_[0-9_]+')
REMOTE = re.compile(r'\(native-remote "[^"]*"\)')
GLOBAL = re.compile(r'\(native-global(?:-exact)? "[^"]*" "[^"]*"\)')

def decode(token):
    m = re.match(r'(l?v)_([0-9_]+)(.*)', token)
    if not m:
        return token
    return m.group(1) + ':' + ''.join(chr(int(c)) for c in m.group(2).strip('_').split('_') if c) + m.group(3)

def tokens(text):
    c = collections.Counter()
    for kind, rx in (('cell', CELL), ('remote', REMOTE), ('global', GLOBAL), ('leaf', LEAF)):
        for t in rx.findall(text):
            c[(kind, decode(t))] += 1
    return c

sample = sorted(int(p.stem) for p in (out / 'beam').glob('*.scm'))
summary = {}
for side in ('native-before', 'native'):
    equal = differ = missing = 0
    kinds = collections.Counter()
    examples = []
    for i in sample:
        path = out / side / f'{i}.scm'
        if not path.exists():
            missing += 1
            continue
        b = tokens((out / 'beam' / f'{i}.scm').read_text())
        n = tokens(path.read_text())
        # leaves are compared separately: the image predates BACKEND's N1
        # templates, so a leaf/template difference is an emitter difference.
        bl = {k: v for k, v in b.items() if k[0] != 'leaf'}
        nl = {k: v for k, v in n.items() if k[0] != 'leaf'}
        if bl == nl:
            equal += 1
        else:
            differ += 1
            for k in set(bl) | set(nl):
                if bl.get(k) != nl.get(k):
                    kinds[k[0]] += 1
                    if len(examples) < 12:
                        examples.append((i, k, bl.get(k, 0), nl.get(k, 0)))
    summary[side] = (equal, differ, missing)
    print(f'LINKS {side}: sampled={len(sample)} equal={equal} different={differ} refused={missing} differing-token-kinds={dict(kinds)}')
    for e in examples:
        print('   ', e)
