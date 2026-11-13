"""Read partial status lines only; never declare an unfinished native gate passed."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

P = Path(__file__).resolve().parent
E = P / 'evidence/word-integration'
baseline = {row['id']: row for row in json.loads((P / 'evidence/retained-request/native.json').read_text())['rows']}
text = (E / 'native-checks.txt').read_text()
seen = {}
for case, engine, status in re.findall(r'^([^\n]+) (z3|oxiz)=([a-z-]+) ms=', text, re.M):
    seen.setdefault(case, {})[engine] = status
completed = {case: results for case, results in seen.items() if set(results) == {'z3', 'oxiz'}}
differences = [{'id': case, 'backend': engine, 'before': baseline[case][engine]['solver-status'], 'after': status}
               for case, results in completed.items() for engine, status in results.items()
               if status != baseline[case][engine]['solver-status']]
progress = {'status': 'running-partial-observation', 'recorded_utc': datetime.now(timezone.utc).isoformat(),
            'completed_pairs': len(completed), 'total_questions': len(baseline),
            'latest_completed_pair': list(completed)[-1] if completed else None,
            'reported_status_differences_so_far': differences,
            'scope': 'Observed log statuses only. Complete graph identities, point validation and final gate exit still require their actual audit.',
            'compiler_proof_authority': False}
(E / 'native-progress.json').write_text(json.dumps(progress, indent=2) + '\n')
print(json.dumps(progress))
