#!/usr/bin/env python3
"""Record round-2 build identity and copy the retained BEAM-vs-native evidence."""
import hashlib
import json
import shutil
from pathlib import Path

seed = Path(__file__).resolve().parents[2]
build = seed / 'out/round2-build'
bench = seed / 'out/round2-bench'
out = Path(__file__).resolve().parent / 'evidence-r2'
out.mkdir(exist_ok=True)
for path in (bench / 'comparison.json', bench / 'native.log', bench / 'beam.log', bench / 'preparation.json',
             build / 'source-corpus.log', build / 'stage2-emit.log'):
    shutil.copy(path, out / path.name)
prelude = (build / 'prelude.scm').read_text()
pin = json.loads((seed / 'sdk-pin.json').read_text())
record = {
    'schema': 'bl.native.speed-final-build', 'version': 2,
    'sdk': pin['sdk'], 'sdk_descriptor_sha256': pin['descriptor_sha256'],
    'stage1_sha256': hashlib.sha256((build / 'stage1').read_bytes()).hexdigest(),
    'stage1_scheme_sha256': hashlib.sha256((build / 'stage1.scm').read_bytes()).hexdigest(),
    'prelude_bytes': len(prelude.encode()),
    'dynamic_native_remote_sites': prelude.count('(native-remote "'),
    'closure_units': 33, 'chunks': 75, 'stage1_units': 70,
    'host_leaves': 456, 'dead_leaves': 0, 'unresolved_remotes': 0,
    'source_corpus': 'NATIVE_COMPILER_SOURCE_CORPUS_OK, 0 FAIL, identical to round 1',
    'self_emission': 'stage1 --compile fails after 59 s: native resolution: global context '
                     'namespace absent from closure (lower)',
}
(out / 'build.json').write_text(json.dumps(record, indent=2) + '\n')
print(record['stage1_sha256'], record['dynamic_native_remote_sites'])
