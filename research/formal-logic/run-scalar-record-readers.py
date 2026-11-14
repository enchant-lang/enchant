"""Open the captured durable store in two fresh SDK readers, then qualify cleanup."""
from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent
for stage in ['reader-one','reader-two','reader-controls']:
 code=subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/'run-scalar-records.py'),stage],cwd=R).returncode
 if code:raise SystemExit(code)
raise SystemExit(subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/'qualify-scalar-records.py')],cwd=R).returncode)
