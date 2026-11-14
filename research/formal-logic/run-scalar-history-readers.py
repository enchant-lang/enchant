"""Recheck each older generation with its producer pin kept distinct."""
from pathlib import Path
import subprocess
P=Path(__file__).resolve().parent;R=P.parent.parent
for script in ['run-scalar-previous-word-readers.py','run-scalar-prior-retained-readers.py','run-scalar-previous-readers.py']:
 code=subprocess.run(['/home/othman/.nix-profile/bin/python3',str(P/script)],cwd=R).returncode
 if code:raise SystemExit(code)
