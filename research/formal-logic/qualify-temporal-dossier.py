"""Qualify the executable temporal dossier against its actual live host and frames."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/temporal'
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
require(len(re.findall(r'^#\+begin_src beam-lisp\b', text, re.M)) == 49, 'forty-nine executable cells')
require('49 cells, 0 cell errors' in (E / 'dossier-cells.txt').read_text()
        and '49 cells, 0 cell errors (checked, unchanged)' in (E / 'dossier-check.txt').read_text(), 'current checked cell results')
require(pin == snapshot['sdk_pin'] == implementation['sdk_pin'], 'same SDK for code and dossier')
for name, digest in implementation['source']['sha256'].items():
    require(sha(R / name) == digest, 'unchanged qualified implementation: ' + name)
audit = read(E / 'browser-audit/audit.json')
require(audit['passed'] and all(row['passed'] for row in audit['checks']), 'all automated browser checks')
graphs = sorted({row['name'].split('/')[1].split(':')[0] for row in audit['checks']
                 if row['name'].endswith(': connected topic opens')})
require(len(graphs) == 40 and 'formal-temporal-values' in graphs, 'all connected review graphs')
images = {name: sha(E / 'browser-audit' / name) for name in audit['screenshots']}
manual = ['phone-temporal-values.png', 'phone-temporal-meaning-panel.png',
          'phone-story-temporal-values-data.png', 'phone-story-temporal-chronology-data.png',
          'phone-story-temporal-laws-data.png', 'desktop-temporal-values.png',
          'desktop-temporal-values-night.png', 'desktop-story-temporal-values-data.png',
          'desktop-story-temporal-chronology-data.png', 'desktop-story-temporal-laws-data.png']
require(all(name in images for name in manual), 'retained actual temporal frames')
visual = read(E / 'browser-audit/visual-review.json')
require(visual['inspected'] == manual and visual['status'] in ('reviewed', 'reviewed-with-capture-limitation'), 'manual frame review')
for size in ('phone', 'desktop'):
    for cell in ('story-temporal-values', 'story-temporal-chronology', 'story-temporal-laws'):
        require(any(row['name'] == size + ': visible executable result ' + cell and row['passed']
                    for row in audit['checks']), 'visible result: ' + size + '/' + cell)
host = read(E / 'dossier-host.json')
require(host['state']['ActiveState'] == 'active' and host['state']['SubState'] == 'running'
        and host['state']['MemoryMax'] == '2147483648' and host['launcher'] == pin['sdk'] + '/bin/bl'
        and host['live_process_sdk_boot'] == pin['sdk'] + '/boot.exs', 'actual capped host on selected SDK')
require(host['http']['status'] == 200 and host['http']['bytes'] > 1000000, 'actual dossier response')
blocks = Counter(re.findall(r'^#\+begin_([\w-]+)', text, re.M | re.I))
report = {'schema': 'enchant.formal.temporal-dossier-qualification.v1', 'checkpoint': 34,
    'recorded_utc': datetime.now(timezone.utc).isoformat(),
    'review_url': 'https://work.tailcb5318.ts.net:18100/', 'chapter': '#time-becomes-a-value-you-can-reason-about',
    'sdk_pin': pin, 'implementation_qualification_sha256': sha(E / 'qualification.json'),
    'document': {'path': str(D.relative_to(R)), 'sha256': sha(D), 'executable_cells': 49,
                 'cell_results_commit': snapshot['code_commit'], 'document_unchanged_since_cell_check': True,
                 'cell_run_log_sha256': sha(E / 'dossier-cells.txt'), 'cell_check_log_sha256': sha(E / 'dossier-check.txt'),
                 'block_kinds': dict(blocks), 'semantic_block_kinds': len(set(blocks) - {'src'})},
    'browser': {'audit_script_sha256': sha(P / 'story-audit.mjs'), 'browser_driver_sha256': sha(P / 'browser-driver.mjs'),
                'automated_checks': len(audit['checks']), 'screenshots': images, 'review_graphs': graphs,
                'visual_review': visual, 'audit_sha256': sha(E / 'browser-audit/audit.json')},
    'host': host, 'scope': 'Executable examples and live presentation; runtime tests are implementation checks, not a preservation theorem.',
    'compiler_proof_authority': False}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'cells': 49, 'checks': len(audit['checks']), 'screenshots': len(images),
                  'graphs': len(graphs), 'visual_status': visual['status']}))
