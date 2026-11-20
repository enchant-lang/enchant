"""Time Gambit's qualified stage-1 build recipe (gsc -c per unit, then clang per unit).

Usage: python3 gambit-build-time.py UNITS_DIR GAMBIT CLANG OUT_DIR JOBS
Reports per-phase CPU sums and wall time at the given parallelism."""
import json, os, subprocess, sys, time, resource
from concurrent.futures import ThreadPoolExecutor
units_dir, gambit, clang, out, jobs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
os.makedirs(out, exist_ok=True)
spec = json.load(open(os.path.join(units_dir, 'units.json')))
def timed(cmd):
    t = time.perf_counter()
    r = subprocess.run(['/usr/bin/env', 'time', '-f', '%U %S', *cmd], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(' '.join(cmd) + '\n' + r.stderr[-2000:])
    u, s = r.stderr.strip().splitlines()[-1].split()
    return time.perf_counter() - t, float(u) + float(s)
def scheme(u):
    src = os.path.join(units_dir, u['file']); c = os.path.join(out, u['file'][:-4] + '.c')
    return timed([gambit + '/bin/gsc', '-c', *u['scheme_flags'], '-o', c, src])
def cc(u):
    c = os.path.join(out, u['file'][:-4] + '.c')
    return timed([clang + '/bin/clang', *u['c_flags'], '-c', c, '-o', c[:-2] + '.o'])
result = {}
for phase, fn in (('scheme_to_c', scheme), ('c_to_object', cc)):
    t = time.perf_counter()
    with ThreadPoolExecutor(jobs) as ex: rows = list(ex.map(fn, spec['units']))
    result[phase] = {'wall_s': time.perf_counter() - t, 'cpu_s': sum(r[1] for r in rows),
                     'max_unit_wall_s': max(r[0] for r in rows), 'units': len(rows)}
    print(phase, json.dumps(result[phase]), flush=True)
json.dump(result, open(os.path.join(out, 'gambit-build.json'), 'w'), indent=1)
