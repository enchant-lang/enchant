#!/usr/bin/env python3
"""Card N2b: per-unit results of one front-end run, by named reason.

  reasons.py .qualify-out/nf-TAG

Reads OUT/compare.json (compare.bl), compare.txt (its FRONT-DIFF lines) and
native.txt (the native run's UNIT lines). Prints the counts per reason and the
units of each, so the handback lists every unit that is not identical.
"""
import collections, json, re, sys

root = sys.argv[1]
results = json.load(open(root + "/out/compare.json"))
diffs = {}
for line in open(root + "/compare.txt"):
    if line.startswith("FRONT-DIFF "):
        _, ns, rest = line.rstrip("\n").split(" ", 2)
        diffs[ns] = rest
failures = {}
for line in open(root + "/native.txt"):
    m = re.match(r"UNIT fail (\S+) (.*)", line)
    if m:
        failures[m.group(1)] = m.group(2)

def staging(ns):
    text = failures.get(ns, "")
    m = re.search(r"kind: :([a-z0-9-]+)", text)
    if m: return "staging: " + m.group(1)
    m = re.search(r'original: "([^"\\]{1,80})', text) or re.search(r'Erlang error: ([^"]{1,80})', text)
    return "staging: " + (m.group(1).strip() if m else "unknown")

def differs(ns):
    d = diffs.get(ns, "")
    if ":ann :line]" in d: return "differs: clause order (map over 32 keys iterates in BEAM HAMT order)"
    if ":fun :remote_fun" in d: return "differs: alias/name read as Module/fun remote"
    if ":private false" in d: return "differs: native Core metadata carries :private false"
    if re.search(r":native <<(\d+, ){15}\d+>>", d): return "differs: generated-module MD5 (custody beam vs fresh compile)"
    m = re.search(r":path \[([^]]*)\]", d)
    return "differs: " + (re.sub(r"\d+", "N", m.group(1))[-60:] if m else "unknown")

groups = collections.defaultdict(list)
for r in results:
    ns, reason = r["namespace"], r.get("reason")
    if reason is None: groups["identical"].append(ns)
    elif reason == "native-staging-failed": groups[staging(ns)].append(ns)
    elif reason == "descriptor-differs": groups[differs(ns)].append(ns)
    else: groups[reason].append(ns)
total = len(results)
for reason, units in sorted(groups.items(), key=lambda kv: (kv[0] != "identical", -len(kv[1]))):
    print("%4d %5.1f%%  %s" % (len(units), 100.0 * len(units) / total, reason))
    if reason != "identical":
        print("            " + " ".join(sorted(units)))
print("%4d units" % total)
