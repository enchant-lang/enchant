"""Record the authorized review host's actual capped process and HTTP response."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

P=Path(__file__).resolve().parent
E=P/'evidence/explicit-points'
pin=json.loads((P/'sdk-pin.json').read_text())
raw=subprocess.check_output(['systemctl','--user','show','work-enchant-formal-review.service',
                             '--property=ActiveState,SubState,ExecMainPID,MemoryMax'],text=True)
state=dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
pid=int(state['ExecMainPID']);assert pid>0
argv=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
boots=[v.decode() for v in argv if v.endswith(b'/boot.exs')]
assert boots==[pin['sdk']+'/boot.exs']
assert state['ActiveState']=='active' and state['SubState']=='running' and state['MemoryMax']=='2147483648'
launcher=Path('/home/othman/.local/state/workstation/enchant-formal-review/run.sh')
script=launcher.read_bytes();assert (pin['sdk']+'/bin/bl').encode() in script
with urllib.request.urlopen('http://127.0.0.1:24089/',timeout=60) as response:
    body=response.read();status=response.status
assert status==200
report={'recorded_utc':datetime.now(timezone.utc).isoformat(),'state':state,
        'launcher':pin['sdk']+'/bin/bl','live_process_sdk_boot':boots[0],
        'launcher_script_sha256':hashlib.sha256(script).hexdigest(),
        'http':{'status':status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()},
        'review_url':'https://work.tailcb5318.ts.net:18100/','profile':0}
(E/'dossier-host.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'pid':pid,'http':status,'bytes':len(body),'sdk':pin['sdk']}))
