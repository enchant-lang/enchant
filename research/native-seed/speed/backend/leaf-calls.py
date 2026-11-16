#!/usr/bin/env python3
"""List the remote calls in scheme.bl and whether the native image registers them as leaves."""
import json
import re
import sys

leaves = set(json.load(open(sys.argv[1]))['registered_leaves'])
src = open(sys.argv[2]).read()
names = {'Enum': 'Elixir.Enum', 'Integer': 'Elixir.Integer', 'BeamLisp.Vector': 'Elixir.BeamLisp.Vector',
         'BeamLisp.CompilerData': 'Elixir.BeamLisp.CompilerData', 'BeamLisp.Decimal': 'Elixir.BeamLisp.Decimal'}
pattern = r'\((Enum|lists|erlang|unicode|maps|Integer|BeamLisp\.Vector|BeamLisp\.CompilerData|BeamLisp\.Decimal)/([A-Za-z_?!]+)'
for mod, fun in sorted(set(re.findall(pattern, src))):
    full = names.get(mod, mod)
    hits = sorted(k for k in leaves if k.startswith(full + '/' + fun + '/'))
    print(mod + '/' + fun, hits or 'NOT A REGISTERED LEAF')
