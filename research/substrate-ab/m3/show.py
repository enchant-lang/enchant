import json, sys
rows_f, kind, i, mn = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
r = [json.loads(l) for l in open(rows_f) if json.loads(l)["kind"] == kind and json.loads(l)["i"] == i][0]
t0 = r["t0_us"]
print(kind, i, "wall", r["wall_ms"], "client", r["client_us"])
rows = []
for l in open(rows_f.rsplit("/", 1)[0] + f"/{kind}-{i}.trace", encoding="latin-1"):
    p = l.rstrip("\n").split("\t")
    if len(p) < 6: continue
    rows.append((int(p[0]), int(p[1]), p[2], p[4], p[5][:60]))
rows.sort()
for s, d, pid, f, a in rows:
    if d >= mn * 1000 or "vm-start" in f:
        print(f"{(s-t0)/1000:8.0f} {d/1000:8.0f} {(s+d-t0)/1000:8.0f} {pid:13s} {f[:80]:80s} {a}")
print("end", r["wall_ms"])
