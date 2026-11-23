import sys, statistics
for path in sys.argv[1:]:
    xs = [int(l) for l in open(path) if l.strip()]
    xs.sort()
    print(f"{path.rsplit('/',1)[-1]:28s} n={len(xs)} median={statistics.median(xs)/1000:.2f}ms min={xs[0]/1000:.2f} max={xs[-1]/1000:.2f} p25={xs[len(xs)//4]/1000:.2f} p75={xs[3*len(xs)//4]/1000:.2f}")
