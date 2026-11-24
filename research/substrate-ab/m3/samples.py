import sys, collections
f = sys.argv[1]
by = collections.defaultdict(collections.Counter)
tot = collections.Counter()
for l in open(f, encoding="latin-1"):
    b, lab, mod, n = l.rstrip("\n").split("\t")
    b = int(b); n = int(n)
    by[b][lab] += n
    tot[b] += n
for b in sorted(by):
    top = ", ".join(f"{k[:45]}={v}" for k, v in by[b].most_common(4))
    print(f"{b*250:6d}ms total={tot[b]:4d}  {top}")
