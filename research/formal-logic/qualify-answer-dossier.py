"""Bind checkpoint 29's executable dossier to its actual browser and host records."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / 'evidence/answer-integrity'
D = P / 'ATLAS.bl.org'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise AssertionError(message)


snapshot = read(E / 'dossier-source-pin.json')
require(sha(D) == snapshot['document_sha256'], 'exact checked dossier')
require(subprocess.check_output(['git', 'show', snapshot['code_commit'] + ':' + str(D.relative_to(R))], cwd=R)
        == D.read_bytes(), 'committed unchanged results')
text = D.read_text()
require(len(re.findall(r'^#\+begin_src beam-lisp\b', text, re.M)) == 39, 'thirty-nine executable cells')
require('39 cells, 0 cell errors' in (E / 'dossier-cells.txt').read_text(), 'successful cells')
require('39 cells, 0 cell errors (checked, unchanged)' in (E / 'dossier-check.txt').read_text(), 'unchanged results')
implementation = read(E / 'qualification.json')
pin = read(P / 'sdk-pin.json')
require(implementation['sdk_pin'] == pin == snapshot['sdk_pin'], 'selected SDK shared by code and dossier')
for name, digest in implementation['source']['sha256'].items():
    require(sha(R / name) == digest, 'qualified implementation unchanged: ' + name)
audit = read(E / 'browser-audit/audit.json')
require(audit['passed'] and all(row['passed'] for row in audit['checks']), 'all browser checks passed')
graphs = sorted({row['name'].split('/')[1].split(':')[0] for row in audit['checks']
                 if row['name'].endswith(': connected topic opens')})
require(len(graphs) == 35 and 'formal-answer-integrity' in graphs, 'all thirty-five review graphs')
images = {name: sha(E / 'browser-audit' / name) for name in audit['screenshots']}
manual = ['phone-answer-integrity.png', 'phone-answer-context-panel.png',
          'phone-story-answer-integrity-data.png', 'phone-story-answer-context-data.png',
          'phone-story-nested-equality-data.png', 'desktop-answer-integrity-night.png',
          'desktop-story-nested-equality-data.png']
require(all(name in images for name in manual), 'actual frames retained')
visual = read(E / 'browser-audit/visual-review.json')
require(visual['inspected'] == manual and visual['passed'], 'manual visual inspection record')
for size in ('phone', 'desktop'):
    for cell in ('story-answer-integrity', 'story-answer-context', 'story-nested-equality'):
        require(any(row['name'] == size + ': visible executable result ' + cell and row['passed']
                    for row in audit['checks']), 'visible executable result: ' + size + '/' + cell)
host = read(E / 'dossier-host.json')
require(host['state']['ActiveState'] == 'active' and host['state']['SubState'] == 'running'
        and host['state']['MemoryMax'] == '2147483648' and pin['sdk'] + '/bin/bl' in host['launcher'],
        'live intended host uses this exact SDK and resource cap')
require(host['http']['status'] == 200 and host['http']['bytes'] > 1000000, 'actual dossier served')
blocks = Counter(re.findall(r'^#\+begin_([\w-]+)', text, re.M | re.I))
report = {
    'schema': 'enchant.formal.answer-integrity-dossier-qualification.v1', 'checkpoint': 29,
    'recorded_utc': datetime.now(timezone.utc).isoformat(),
    'review_url': 'https://work.tailcb5318.ts.net:18100/', 'chapter': '#an-answer-has-to-fit-its-question',
    'internal_url': audit['base'], 'sdk_pin': pin,
    'implementation_qualification_sha256': sha(E / 'qualification.json'),
    'document': {'path': str(D.relative_to(R)), 'sha256': sha(D), 'executable_cells': 39,
                 'cell_results_commit': snapshot['code_commit'], 'document_unchanged_since_cell_check': True,
                 'cell_run_log_sha256': sha(E / 'dossier-cells.txt'), 'cell_check_log_sha256': sha(E / 'dossier-check.txt'),
                 'block_kinds': dict(blocks), 'semantic_block_kinds': len(set(blocks) - {'src'})},
    'browser': {'audit_script_sha256': sha(P / 'story-audit.mjs'),
                'audit_report_sha256': sha(E / 'browser-audit/audit.json'), 'checks': len(audit['checks']),
                'screenshots': len(images), 'passed': True, 'connected_review_graphs': len(graphs),
                'review_graph_ids': graphs, 'visible_answer_cells': True,
                'viewports': [{'width': 390, 'height': 844, 'mobile': True},
                              {'width': 1440, 'height': 1000, 'mobile': False}]},
    'visual_review': visual, 'image_sha256': images, 'host': host,
    'persistent_owner': {'deliverable': 'live formal-logic dossier', 'unit': 'work-enchant-formal-review.service',
                         'retirement': 'research/formal-logic/review stop when the user retires this review'},
    'scope': 'Presentation, executed recorded examples, declared source/evidence access and live review. '
             'Tracked context guards remain cooperative APIs; raw transport and mutable bookkeeping escape hatches remain. '
             'No universal implementation proof or compiler authority.',
    'compiler_proof_authority': False,
}
(E / 'dossier-qualification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'cells': 39, 'checks': len(audit['checks']), 'screenshots': len(images),
                  'graphs': len(graphs), 'passed': True}))
