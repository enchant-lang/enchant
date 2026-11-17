import json
r2 = json.load(open('research/native-seed/speed/final/evidence-r2/comparison.json'))
r3 = json.load(open('research/native-seed/out/round3-bench/comparison.json'))
print('scheme byte-equal native/BEAM:', r3['scheme_byte_equal'])
print(f"{'phase':9} {'native':>9} {'BEAM':>9} {'ratio':>6}   r2: {'native':>9} {'BEAM':>9} {'ratio':>6}")
for k in ['read', 'compile', 'emit', 'pipeline']:
    a, b = r3['phases'][k], r2['phases'][k]
    n, be = a['native_median_seconds'] * 1e3, a['beam_median_seconds'] * 1e3
    n2, b2 = b['native_median_seconds'] * 1e3, b['beam_median_seconds'] * 1e3
    print(f"{k:9} {n:8.3f}ms {be:8.3f}ms {n/be:5.1f}x   r2: {n2:8.3f}ms {b2:8.3f}ms {n2/b2:5.1f}x")
