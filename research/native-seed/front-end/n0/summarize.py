#!/usr/bin/env python3
"""Card N0: per-unit native vs BEAM front-end times from run.sh's outputs.

  summarize.py OUT SDK NATIVE_TAGS BEAM_TAGS > summary.json
  (tags comma-separated, e.g. 1,2,3)

Per unit and run:
  native front-to-Core = stage_us + lower_us   (write_us and gc_us apart)
  BEAM   front-to-Core = prepare_us - gen_beam_us + core_us + gen_core_us
Each unit's time is the median over runs; totals are sums of those medians,
and each run's own total is reported too. Units that failed on either side are
left out of both and listed.
"""
import json, os, re, statistics, sys

def parse(path, prefix):
    rows = {}
    for line in open(path, errors="replace"):
        if not line.startswith(prefix + " ok "): continue
        parts = line.split()
        ns = parts[2]
        kv = {parts[i]: parts[i + 1] for i in range(3, len(parts) - 1, 2)}
        rows[ns] = kv
    return rows

def warm(path, key):
    out = {}
    for line in open(path, errors="replace"):
        m = re.match(r"WARM (\S+) (\d+) total_us (\d+)", line)
        if m and key == "warm": out.setdefault(m.group(1), []).append(int(m.group(3)))
        m = re.match(r"EVAL (\S+) (\d+) us (\d+)", line)
        if m and key == "eval": out.setdefault(m.group(1), []).append(int(m.group(3)))
    return out

def med(xs): return statistics.median(xs) if xs else None

def main():
    out, sdk = sys.argv[1], sys.argv[2]
    ntags, btags = sys.argv[3].split(","), sys.argv[4].split(",")
    index = json.load(open(os.path.join(sdk, "unit-store/unit-index.json")))["units"]
    size = {ns: os.path.getsize(os.path.join(sdk, "image/priv", r["file"])) for ns, r in index.items()}
    nat = [parse(os.path.join(out, "native-%s.txt" % t), "UNIT") for t in ntags]
    bea = [parse(os.path.join(out, "beam-%s.txt" % t), "BEAM") for t in btags]
    nf = lambda r: int(r["stage_us"]) + int(r["lower_us"])
    bf = lambda r: int(r["prepare_us"]) - int(r["gen_beam_us"]) + int(r["core_us"]) + int(r["gen_core_us"])
    common = sorted(set.intersection(*[set(r) for r in nat + bea]))
    every = set().union(*[set(r) for r in nat + bea])
    units = {}
    for ns in common:
        n = med([nf(r[ns]) for r in nat]); b = med([bf(r[ns]) for r in bea])
        units[ns] = {"bytes": size.get(ns), "native_us": n, "beam_us": b,
                     "native_stage_us": med([int(r[ns]["stage_us"]) for r in nat]),
                     "native_lower_us": med([int(r[ns]["lower_us"]) for r in nat]),
                     "native_write_us": med([int(r[ns]["write_us"]) for r in nat]),
                     "native_gc_us": med([int(r[ns]["gc_us"]) for r in nat]),
                     "beam_prepare_us": med([int(r[ns]["prepare_us"]) for r in bea]),
                     "beam_gen_beam_us": med([int(r[ns]["gen_beam_us"]) for r in bea]),
                     "beam_core_us": med([int(r[ns]["core_us"]) + int(r[ns]["gen_core_us"]) for r in bea]),
                     "custody_us": med([int(r[ns]["custody_us"]) for r in bea]),
                     "same_desc": all(r[ns]["same_desc"] == "true" for r in bea),
                     "same_core": all(r[ns]["same_core"] == "true" for r in bea),
                     "ratio_beam_over_native": (b / n) if n else None}
    tot = lambda k: sum(u[k] for u in units.values())
    ratios = [u["ratio_beam_over_native"] for u in units.values() if u["ratio_beam_over_native"]]
    largest = sorted(units.items(), key=lambda kv: -(kv[1]["bytes"] or 0))[:10]
    summary = {
        "units_measured": len(units),
        "units_left_out": sorted(every - set(common)),
        "native_runs": ntags, "beam_runs": btags,
        "per_run_total_ms": {
            "native": [round(sum(nf(r[ns]) for ns in common) / 1000) for r in nat],
            "beam": [round(sum(bf(r[ns]) for ns in common) / 1000) for r in bea]},
        "total_ms": {"native": round(tot("native_us") / 1000), "beam": round(tot("beam_us") / 1000),
                     "native_write": round(tot("native_write_us") / 1000), "native_gc": round(tot("native_gc_us") / 1000),
                     "beam_prepare_raw": round(tot("beam_prepare_us") / 1000),
                     "beam_generated_beam_compile_removed": round(tot("beam_gen_beam_us") / 1000),
                     "custody": round(tot("custody_us") / 1000),
                     "native_stage": round(tot("native_stage_us") / 1000), "native_lower": round(tot("native_lower_us") / 1000),
                     "beam_lower": round(tot("beam_core_us") / 1000)},
        "median_unit_ms": {"native": med([u["native_us"] for u in units.values()]) / 1000,
                           "beam": med([u["beam_us"] for u in units.values()]) / 1000},
        "ratio_beam_over_native": {"of_totals": tot("beam_us") / tot("native_us"),
                                   "median_per_unit": med(ratios),
                                   "p10": statistics.quantiles(ratios, n=10)[0],
                                   "p90": statistics.quantiles(ratios, n=10)[-1],
                                   "units_native_2x_faster": sum(1 for r in ratios if r >= 2),
                                   "units_native_faster": sum(1 for r in ratios if r > 1)},
        "identity": {"same_descriptors": sum(u["same_desc"] for u in units.values()),
                     "same_core_terms": sum(u["same_core"] for u in units.values())},
        "largest_10": [{"namespace": ns, "bytes": u["bytes"], "native_ms": u["native_us"] / 1000,
                        "beam_ms": u["beam_us"] / 1000, "ratio": round(u["ratio_beam_over_native"], 3)}
                       for ns, u in largest],
        "warm": {},
    }
    # Fixed cost and slope: the 20 smallest units, size quartiles, and a
    # least-squares line time = a + b * bytes on each side.
    by_size = sorted(units.values(), key=lambda u: u["bytes"] or 0)
    smallest = by_size[:20]
    summary["smallest_20_median_ms"] = {"native": med([u["native_us"] for u in smallest]) / 1000,
                                        "beam": med([u["beam_us"] for u in smallest]) / 1000,
                                        "bytes_max": smallest[-1]["bytes"]}
    q = len(by_size) // 4
    summary["by_size_quartile"] = [
        {"bytes": [part[0]["bytes"], part[-1]["bytes"]],
         "native_median_ms": med([u["native_us"] for u in part]) / 1000,
         "beam_median_ms": med([u["beam_us"] for u in part]) / 1000,
         "ratio_median": med([u["ratio_beam_over_native"] for u in part])}
        for part in (by_size[:q], by_size[q:2 * q], by_size[2 * q:3 * q], by_size[3 * q:])]
    def fit(key):
        xs = [u["bytes"] for u in by_size]; ys = [u[key] / 1000 for u in by_size]
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        return {"fixed_ms": round(my - b * mx, 1), "ms_per_kb": round(b * 1024, 2)}
    summary["linear_fit"] = {"native": fit("native_us"), "beam": fit("beam_us")}
    nw = [warm(os.path.join(out, "native-%s.txt" % t), "warm") for t in ntags]
    bw = [warm(os.path.join(out, "beam-%s.txt" % t), "warm") for t in btags]
    be = [warm(os.path.join(out, "beam-%s.txt" % t), "eval") for t in btags]
    for ns in sorted(set().union(*[set(w) for w in nw + bw])):
        # the first repeat is dropped: it is the one closest to the corpus pass
        n = [x for w in nw for x in w.get(ns, [])[1:]]
        b = [x for w in bw for x in w.get(ns, [])[1:]]
        e = [x for w in be for x in w.get(ns, [])[1:]]
        summary["warm"][ns] = {"bytes": size.get(ns),
                               "native_ms": {"median": med(n) / 1000 if n else None, "min": min(n) / 1000 if n else None, "n": len(n)},
                               "beam_prepare_ms": {"median": med(b) / 1000 if b else None, "min": min(b) / 1000 if b else None, "n": len(b)},
                               "beam_eval_string_ms": {"median": med(e) / 1000 if e else None, "min": min(e) / 1000 if e else None, "n": len(e)}}
    summary["units"] = units
    json.dump(summary, sys.stdout, indent=1, sort_keys=False)

main()
