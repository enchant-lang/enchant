"""Run the pinned original-term Lean checker on the three exported span laws."""
import argparse
import json
from pathlib import Path
from term_refutation import run

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('root', type=Path)
args = parser.parse_args()
root = args.root.resolve()
rows = json.loads((root / 'law-packets.json').read_text())['rows']
assert len(rows) == 3
accepted = []
for row in rows:
    result = run(root / (row['id'] + '.json'), root / 'law-execution' / row['id'], 'choice-free')
    assert result['status'] == 'checked-term-entailment'
    assert result['packet'] == row['packet']
    accepted.append({'id': row['id'], **result})
(root / 'law-execution/accepted.json').write_text(json.dumps(accepted, indent=2) + '\n')
print(json.dumps({'checked_original_term_laws': len(accepted), 'compiler_proof_authority': False}))
