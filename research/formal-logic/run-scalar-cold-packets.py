"""Keep all portable-record checks SDK-only, cold, private and sequential."""
from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent
for stage in ['packets','text-packets','evidence-packets']:
 code=subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/'run-scalar-integration-checks.py'),stage],cwd=R).returncode
 if code:raise SystemExit(code)
