#!/usr/bin/env python3
"""Record the final build identity next to the retained benchmark evidence."""
import hashlib
import json
from pathlib import Path

base = Path(__file__).resolve().parents[2]
build = base / 'out/speed-build'
prelude = (build / 'prelude.scm').read_text()
record = {
    'schema': 'bl.native.speed-final-build', 'version': 1,
    'stage1_sha256': hashlib.sha256((build / 'stage1').read_bytes()).hexdigest(),
    'stage1_scheme_sha256': hashlib.sha256((build / 'stage1.scm').read_bytes()).hexdigest(),
    'prelude_bytes': len(prelude.encode()),
    'dynamic_native_remote_sites': prelude.count('(native-remote "'),
    'gsc_declarations': '(standard-bindings) (extended-bindings)',
    'c_flags': 'qualified defaults (-O0)',
    'source_corpus': 'NATIVE_COMPILER_SOURCE_CORPUS_OK, 0 FAIL, identical to the original qualified stage1 log',
    'emission': 'chunks.bl build-next: 55 chunks in one window',
    'closure': 'update-closure.bl recompiled native.scheme, native.eval, native.bootstrap; 15 units reused',
}
out = Path(__file__).resolve().parent / 'evidence/build.json'
out.write_text(json.dumps(record, indent=2) + '\n')
print(record['stage1_sha256'], record['dynamic_native_remote_sites'])
