"""Run project consumers and paired native questions serially on one candidate."""
from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent
for stage in ['regression','native']:
 code=subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/'run-scalar-integration-checks.py'),stage],cwd=R).returncode
 if code:raise SystemExit(code)
