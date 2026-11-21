"""Decode Chez profile names of the form v_<code>_<code>...$arity into BL names."""
import re, sys
def name(m):
    return ''.join(chr(int(c)) for c in m.group(1)[1:].split('_')) + (m.group(2) or '')
for line in sys.stdin:
    print(re.sub(r'v((?:_\d+)+)(\$\d+)?', name, line), end='')
