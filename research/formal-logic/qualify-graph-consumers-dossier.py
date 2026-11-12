"""Qualify the executed question graph chapter against the selected host and actual frames."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/graph-consumers'
D = P / 'ATLAS.bl.org'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, why):
    if not ok:
        raise AssertionError(why)


snapshot, pin, implementation = read(E / 'dossier-source-pin.json'), read(P / 'sdk-pin.json'), read(E / 'qualification.json')
require(sha(D) == snapshot['document_sha256'], 'exact checked document')
require(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + str(D.relative_to(R))], cwd=R)
        == D.read_bytes(), 'committed cell results')
text = D.read_text()
require(len(re.findall(r'^#\+begin_src beam-lisp\b', text, re.M)) == 80, '80 executable cells')
require('80 cells, 0 cell errors' in (E / 'doc-run-checks.txt').read_text()
        and '80 cells, 0 cell errors (checked, unchanged)' in (E / 'doc-check-checks.txt').read_text(), 'unchanged executed results')
require(pin == snapshot['sdk_pin'] == implementation['sdk_pin'], 'same SDK for code and dossier')
for name, digest in read(E / 'sdk-source-pin.json')['source_sha256'].items():
    require(sha(R / name) == digest, 'unchanged implementation: ' + name)
audit = read(E / 'browser-audit/audit.json')
require(audit['passed'] and all(row['passed'] for row in audit['checks']), 'all automated browser checks')
graphs = sorted({row['name'].split('/')[1].split(':')[0] for row in audit['checks']
                 if row['name'].endswith(': connected topic opens')})
require(len(graphs) == 49 and 'formal-graph-consumers' in graphs, 'all 49 connected review graphs')
images = {name: sha(E / 'browser-audit' / name) for name in audit['screenshots']}
frames = ('graph-consumers', 'graph-selected-panel', 'graph-ledger-panel', 'story-graph-selected-data', 'story-graph-native-data', 'story-graph-intercepted-data', 'story-graph-durable-data')
manual = [size + '-' + frame + '.png' for size in ('phone', 'desktop') for frame in frames]
manual.append('desktop-graph-consumers-night.png')
manual.append('phone-graph-ledger-details.png')
require(all(name in images for name in manual), 'retained actual response frames')
visual = read(E / 'browser-audit/visual-review.json')
require(visual['inspected'] == manual and visual['status'] in ('reviewed', 'reviewed-with-capture-limitation'), 'manual frame review')
for size in ('phone', 'desktop'):
    for cell in ('story-graph-selected','story-graph-native','story-graph-intercepted','story-graph-durable'):
        require(any(row['name'] == size + ': visible graph consumer result ' + cell and row['passed']
                    for row in audit['checks']), 'visible executed result: ' + size + '/' + cell)
host_sources = read(E / 'host-source-pin.json')
for name, digest in host_sources['source_sha256'].items():
    require(sha(R / name) == digest, 'qualified host source: ' + name)
    committed = subprocess.check_output(['git', 'show', host_sources['code_commit'] + ':' + name], cwd=R)
    require(hashlib.sha256(committed).hexdigest() == digest, 'committed host source: ' + name)
host = read(E / 'dossier-host.json')
warmup = read(E / 'host-warmup-exit.json')
cache_check = read(E / 'host-cache-exit.json')
require(cache_check['exit_code'] == 0 and cache_check['runtime_retired']
        and '52 passed' in (E / 'host-cache-checks.txt').read_text(),
        '52 focused revision/role/cache concurrency checks on selected SDK')
require(warmup['exit_code'] == 0 and warmup['ready_timeout_seconds'] == 120
        and warmup['memory_max'] == '2G' and warmup['profile'] == 0,
        'actual cold startup passes existing readiness and memory limits')
require(host['state']['ActiveState'] == 'active' and host['state']['SubState'] == 'running'
        and host['state']['MemoryMax'] == '2147483648' and host['launcher'] == pin['sdk'] + '/bin/bl'
        and host['live_process_sdk_boot'] == pin['sdk'] + '/boot.exs', 'actual capped host on the selected SDK')
require(host['http']['status'] == 200 and host['http']['bytes'] > 1000000, 'actual dossier response')
require(host['document_sha256'] == sha(D) and host['http']['completed_interface_and_corpus_caption'],
        'actual response warmed from the current corrected document')
blocks = Counter(re.findall(r'^#\+begin_([\w-]+)', text, re.M | re.I))
report = {'schema': 'enchant.formal.graph-consumers-dossier-qualification.v1', 'checkpoint': 44,
          'recorded_utc': datetime.now(timezone.utc).isoformat(),
          'review_url': 'https://work.tailcb5318.ts.net:18100/', 'chapter': '#use-the-saved-question-without-unpacking-its-history',
          'sdk_pin': pin, 'implementation_qualification_sha256': sha(E / 'qualification.json'),
          'document': {'path': str(D.relative_to(R)), 'sha256': sha(D), 'executable_cells': 80,
                       'cell_results_commit': snapshot['code_commit'], 'document_unchanged_since_cell_check': True,
                       'cell_run_log_sha256': sha(E / 'doc-run-checks.txt'), 'cell_check_log_sha256': sha(E / 'doc-check-checks.txt'),
                       'block_kinds': dict(blocks), 'semantic_block_kinds': len(set(blocks) - {'src'})},
          'browser': {'audit_script_sha256': sha(P / 'story-audit.mjs'), 'browser_driver_sha256': sha(P / 'browser-driver.mjs'),
                      'automated_checks': len(audit['checks']), 'screenshots': images, 'review_graphs': graphs,
                      'visual_review': visual, 'audit_sha256': sha(E / 'browser-audit/audit.json')},
          'host': host, 'host_sources': host_sources,
          'host_warmup': warmup, 'host_warmup_log_sha256': sha(E / 'host-warmup-checks.txt'),
          'host_cache_checks': {'assertions': 52, 'log_sha256': sha(E / 'host-cache-checks.txt')},
          'host_cache_scope': 'Existing revision/role/variant cache with a read-only page warmed before listener admission. Focused cache checks, actual cold startup and current presentation are exercised on SDK 44; preceding broader qualification remains historical.',
          'scope': 'Executed examples, retained records and live presentation. These checks do not establish source/compiler preservation or whole-language totality.',
          'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'cells': 80, 'checks': len(audit['checks']), 'screenshots': len(images), 'graphs': len(graphs), 'visual_status': visual['status']}))
