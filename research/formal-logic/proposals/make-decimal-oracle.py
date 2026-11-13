"""Compile the existing captured JVM cases as ordinary BL expressions.

Expected results stay in a separate fixture; the generated program contains
only the expressions and a common observation function. No cases are dropped.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

P = Path(__file__).resolve().parent.parent
R = P.parent.parent
source = R / 'test/bl/decimal_oracle_port_test.bl'
pattern = r'^\s*\[("(?:\\.|[^"\\])*")\s+("(?:\\.|[^"\\])*")\s+("(?:\\.|[^"\\])*")\]\s*$'
rows = [[json.loads(item) for item in row] for row in re.findall(pattern, source.read_text(), re.M)]
assert len(rows) == 1051
fixture = {'schema': 'bl.captured-decimal-oracle-cases.v1',
           'source': str(source.relative_to(R)), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'rows': [{'jvm': jvm, 'source': bl, 'expected': expected} for jvm, bl, expected in rows],
           'scope': 'The existing 1051 JVM-captured cases. ERROR compares raisedness, not exception type/message or effects.',
           'compiler_proof_authority': False}
parts = ['(ns semantics.decimal-oracle (:require [decimal :as d]))\n',
         ';; Generated from the committed JVM corpus; no expected answers occur here.\n',
         '(defn- observe [f]\n (try (let [value (f)] (if (string? value) value (str value)))\n  (catch _ "ERROR")))\n']
chunks = []
for start in range(0, len(rows), 50):
    name = 'chunk-' + str(start // 50)
    chunks.append(name)
    parts.append('(defn- ' + name + ' []\n [\n' + ''.join('  (observe (fn [] ' + row[1] + '))\n' for row in rows[start:start+50]) + ' ])\n')
parts.append('(defn results [] (vec (concat ' + ' '.join('(' + name + ')' for name in chunks) + ')))\n')
outputs = {P / 'proposals/decimal-oracle-cases.json': json.dumps(fixture, indent=2) + '\n',
           P / 'semantics-src/semantics/decimal-oracle.bl': '\n'.join(parts)}
if sys.argv[1:] == ['--check']:
    assert all(path.read_text() == body for path, body in outputs.items())
    print(json.dumps({'status': 'unchanged', 'cases': len(rows), 'chunks': len(chunks)}))
else:
    assert not sys.argv[1:]
    for path, body in outputs.items():
        path.write_text(body)
    print(json.dumps({'status': 'generated', 'cases': len(rows), 'chunks': len(chunks)}))
