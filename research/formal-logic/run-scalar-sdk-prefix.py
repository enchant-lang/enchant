"""Run the candidate's first disjoint gates serially, stopping at any failure."""
from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent
for stage in ['preflight','preflight-controls','focused']:
 code=subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/'run-scalar-integration-checks.py'),stage],cwd=R).returncode
 if code:raise SystemExit(code)
