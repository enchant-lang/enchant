"""Split each traced first command into phases (ms). usage: split.py DIR..."""
import json, sys, statistics
def rows_of(d, kind, i):
    out = []
    for l in open(f"{d}/{kind}-{i}.trace", encoding="latin-1"):
        p = l.rstrip("\n").split("\t")
        if len(p) >= 6: out.append((int(p[0]), int(p[1]), p[2], p[4], p[5]))
    return sorted(out)
def first(rows, fn, arg=None):
    for r in rows:
        if fn in r[3] and (arg is None or r[4].startswith(arg)): return r
    return None
table = {"warm": [], "cold": []}
for d in sys.argv[1:]:
    for l in open(f"{d}/rows.jsonl"):
        r = json.loads(l); k = r["kind"]
        rows = rows_of(d, k, r["i"]); t0 = r["t0_us"]; end = r["t1_us"]
        ms = lambda us: round((us - t0) / 1000)
        vm = first(rows, "vm-start"); cli = first(rows, "Loader:ensure_loaded/1", "bl.cli")
        bt = first(rows, "Loader:ensure_loaded/1", "reload.ward")
        ph = {"wall": round(r["wall_ms"]), "to_vm_start": ms(vm[0]), "vm_boot_to_bl.cli": ms(cli[0] + cli[1]) - ms(vm[0])}
        if k == "warm":
            ss = first(rows, "Vm.Session:start/2"); ls = first(rows, "Vm.Net:listen/3")
            rq = first(rows, "Session:request-handler/2", "{request"); hv = first(rows, "Daemon:handle-in-vm/3")
            bs = first(rows, "boot-realm-services!")
            ph.update({"session_ns_loads": ms(ss[0]) - ms(cli[0] + cli[1]),
                       "session_to_listening": ms(ls[0] + ls[1]) - ms(ss[0]),
                       "listening_to_request": ms(rq[0]) - ms(ls[0] + ls[1]),
                       "boot_services_after_request": max(0, ms(bs[0] + bs[1]) - ms(rq[0])),
                       "request_to_handler": ms(hv[0]) - ms(rq[0]),
                       "handler_to_test": ms(bt[0]) - ms(hv[0])})
        else:
            ph["bl.cli_to_test"] = ms(bt[0]) - ms(cli[0] + cli[1])
        ph["test"] = round((end - bt[0]) / 1000)
        table[k].append(ph)
for k, runs in table.items():
    keys = list(runs[0].keys())
    print(k, "n", len(runs))
    for key in keys:
        xs = [p[key] for p in runs]
        print(f"  {key:30s} median {statistics.median(xs):7.0f}  {xs}")
