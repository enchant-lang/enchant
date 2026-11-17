#!/usr/bin/env python3
"""Compare the emitted Scheme of the two targets for the A3 fixture.
Usage: diff-emitted.py BEAM.scm NATIVE.scm  (starts no process)."""
import collections
import re
import sys

beam, native = (open(p).read().split('\n') for p in sys.argv[1:3])


def shape(lines):
    text = '\n'.join(lines)
    return {'chars': len(text), 'definitions': len(lines),
            'native-remote': text.count('(native-remote "'),
            'native-remote BL namespace module': len(re.findall(r'\(native-remote "Elixir\.BeamLisp\.Ns\.', text)),
            'native-global': text.count('(native-global'),
            'bl-invoke callee': text.count('(callee bl-invoke)')}


same = sum(1 for a, b in zip(beam, native) if a == b)
mods = collections.Counter(re.findall(r'\(native-remote "(Elixir\.BeamLisp\.Ns\.[^/]*)/', '\n'.join(beam)))
globs = collections.Counter(re.findall(r'\(native-global(?:-exact)? "([^"]*)"', '\n'.join(native)))
print({'beam': shape(beam), 'native': shape(native), 'identical_definitions': same,
       'beam_remote_modules': mods.most_common(10), 'native_global_namespaces': globs.most_common(10)})
