#!/usr/bin/env python3
"""Card N2b: random map key sets for front-end/hamt-check.sh.

  hamt-keys.py OUT.bl EXPECT.json SEED

Writes OUT.bl, which builds 132 maps (11 key kinds: strings, integers small
and big, tuples, lists, byte lists, floats, mixtures; 12 sizes from 5 to
1000) and prints each map's values in iteration order, and EXPECT.json, the
order hamt_ref.py (a Python model of OTP 29's erts_internal_hash and HAMT
layout) predicts for every map over 32 keys.
"""
import random, json, sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hamt_ref import *
random.seed(int(sys.argv[3]) if len(sys.argv)>3 else 7)
def rstr():
    n=random.choice([0,1,2,3,5,7,8,9,15,16,17,24,31,32,33,40,100])
    alpha='abcdefghijklmnopqrstuvwxyz-_./!?0123456789ABCXYZ'
    s=''.join(random.choice(alpha) for _ in range(n))
    if random.random()<0.1: s+=random.choice(['é','→','日本','😀'])
    return s
def rint():
    return random.choice([random.randint(-50,50), random.randint(-2**40,2**40), random.randint(2**59-3,2**59+3),
                          -random.randint(2**59-3,2**59+3), random.randint(2**64,2**200), -random.randint(2**64,2**130)])
def rkey(kind, depth=0):
    if kind=='s': return rstr()
    if kind=='i': return rint()
    if kind=='f': return F(random.choice([0.5,-1.25,3.14159,2.75,-100.125])*random.randint(1,1000))
    if kind=='t': return T(*[rkey(random.choice('sif' if depth else 'sitl'),depth+1) for _ in range(random.randint(0,4))])
    if kind=='l': return [rkey(random.choice('i' if random.random()<.5 else 'sitl'),depth+1) if depth<2 else random.randint(0,300) for _ in range(random.randint(0,6))]
    if kind=='b': return [random.randint(0,255) for _ in range(random.randint(0,9))]
    if kind=='m': return rkey(random.choice('sitlbf'),depth)
def bl(k):
    if isinstance(k,str): return json.dumps(k, ensure_ascii=False)
    if isinstance(k,F): return repr(float(k.v)) if 'e' not in repr(float(k.v)) and 'inf' not in repr(k.v) else '(erlang/binary_to_float "%r")'%float(k.v)
    if isinstance(k,int): return str(k)
    if isinstance(k,T): return '(tuple %s)'%' '.join(bl(x) for x in k.e)
    if isinstance(k,list): return '(list %s)'%' '.join(bl(x) for x in k)
def key_id(k):
    if isinstance(k,F): return ('f',k.v)
    if isinstance(k,T): return ('t',)+tuple(key_id(x) for x in k.e)
    if isinstance(k,list): return ('l',)+tuple(key_id(x) for x in k)
    return (type(k).__name__,k)

sets=[]
for kind in ['s','s','s','i','i','t','l','b','f','m','m']:
    for size in [5,31,32,33,34,40,47,64,100,129,300,1000]:
        seen=set(); keys=[]
        while len(keys)<size:
            k=rkey(kind); kid=key_id(canon(k))
            if kid in seen: continue
            # BL/Erlang: 1.0 vs 1 are distinct keys; -0.0 vs 0.0 distinct in OTP27+; keep
            seen.add(kid); keys.append(k)
        sets.append(keys)
out=['(defn- show [i m] (println (str "M" i " " (apply str (interpose " " (Map/values m))))))']
expect=[]
for i,keys in enumerate(sets):
    out.append('(show %d (into {} [%s]))' % (i, ' '.join('[%s %d]'%(bl(k),j) for j,k in enumerate(keys))))
    if len(keys)>32:
        order=sorted(range(len(keys)), key=lambda j: order_key(ihash(keys[j])))
        expect.append('M%d %s'%(i,' '.join(map(str,order))))
    else:
        expect.append(None)
open(sys.argv[1],'w').write('\n'.join(out)+'\n')
json.dump(expect, open(sys.argv[2],'w'))
print(len(sets),'sets')
