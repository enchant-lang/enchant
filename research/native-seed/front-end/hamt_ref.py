"""Card N2b: a Python model of OTP 29's map iteration order for maps over 32
keys: erts_internal_hash (erl_term_hashing.c, make_internal_hash) and the
HAMT's child order (4-bit hash digits, lowest first). Keys as BL builds them:
integral floats are integers (BL canonicalises map keys)."""
import struct
M=(1<<64)-1
C1=0x87C37B91114253D5; C2=0x4CF5AD432745937F
def rotl(x,r): return ((x<<r)|(x>>(64-r)))&M
def mix64(h):
    h^=h>>33; h=(h*0xFF51AFD7ED558CCD)&M; h^=h>>33; h=(h*0xC4CEB9FE1A85EC53)&M; h^=h>>33; return h
class T:  # tuple marker
    def __init__(s,*e): s.e=e
class F:
    def __init__(s,v): s.v=v
class B:
    def __init__(s,b): s.b=b
MIN_SMALL=-(1<<59); MAX_SMALL=(1<<59)-1
def immediate(t): return (isinstance(t,int) and MIN_SMALL<=t<=MAX_SMALL) or (isinstance(t,list) and len(t)==0)
def eterm(t):
    if isinstance(t,list): return 0x3B
    return ((t<<4)+0xF)&M
def canon(t):
    if isinstance(t,F) and float(t.v).is_integer(): return int(t.v)
    if isinstance(t,T): return T(*[canon(x) for x in t.e])
    if isinstance(t,list): return [canon(x) for x in t]
    return t
def ihash(term):
    term=canon(term)
    if immediate(term): return mix64(eterm(term))
    st={'a':0,'b':0,'t':0}
    def A(e):
        e=(e*C1)&M; e=rotl(e,31); e=(e*C2)&M
        st['a']^=e; st['a']=rotl(st['a'],27); st['a']=(st['a']+st['b'])&M; st['a']=(st['a']*5+0x52DCE729)&M; st['t']+=1
    def Bm(e):
        e=(e*C2)&M; e=rotl(e,33); e=(e*C1)&M
        st['b']^=e; st['b']=rotl(st['b'],31); st['b']=(st['b']+st['a'])&M; st['b']=(st['b']*5+0x38495AB5)&M; st['t']+=1
    def A2(x,y): A((x|(y<<32))&M)
    def B2(x,y): Bm((x|(y<<32))&M)
    stack=[]
    def push(t):
        if immediate(t): A(1); Bm(eterm(t))
        else: A(2); stack.append(t)
    term=term
    while True:
        if isinstance(term,list) and term:
            lst=term; i=0; value=0; nb=0
            while i<len(lst) and isinstance(lst[i],int) and 0<=lst[i]<=255:
                value=(value<<8)|lst[i]; nb+=1
                if nb%4==0: A2(5|(nb<<8),value); value=0; nb=0
                i+=1
            if nb>0: A2(5|(nb<<8),value)
            rest=lst[i:]
            if rest:
                head=rest[0]; tail=rest[1:]
                if immediate(head):
                    A2(1,3); Bm(eterm(head))
                    if not tail: pass  # tail '() is a list (NIL is_list? no!)
                    term=tail
                    # is_not_list(tail): NIL is not a list cell -> CDR mixed when tail empty
                    if not tail: A(4)
                    continue
                else:
                    stack.append(tail)
                    if not tail: stack.append('CDR')
                    A(3); term=head; continue
            term=[]  # NIL
            continue
        if immediate(term):
            A(1); Bm(eterm(term))
        elif isinstance(term,T):
            A(6); Bm(len(term.e))
            if term.e:
                for x in term.e[:-1]: push(x)
                term=term.e[-1]; continue
        elif isinstance(term,(str,B)):
            data=term.encode() if isinstance(term,str) else term.b
            A(12); Bm(8*len(data))
            n=len(data); it=0
            while it+16<=n:
                A(int.from_bytes(data[it:it+8],'little')); Bm(int.from_bytes(data[it+8:it+16],'little')); it+=16
            r=n%16
            if r>8:
                v=int.from_bytes(data[it+8:it+r],'little'); v=(v*C2)&M; v=rotl(v,33); v=(v*C1)&M; st['b']^=v
            if r>0:
                v=int.from_bytes(data[it:it+min(r,8)],'little'); v=(v*C1)&M; v=rotl(v,31); v=(v*C2)&M; st['a']^=v
        elif isinstance(term,int):
            n=abs(term); digits=[]
            while n: digits.append(n&M); n>>=64
            A2(15 if term<0 else 16, len(digits))
            i=0
            while i+2<=len(digits): A(digits[i]); Bm(digits[i+1]); i+=2
            if i<len(digits): Bm(digits[i])
        elif isinstance(term,F):
            A(21); Bm(struct.unpack('<Q',struct.pack('<d',term.v))[0])
        else: raise Exception(term)
        # pop_next
        while True:
            if not stack:
                a,b,t=st['a'],st['b'],st['t']
                a^=t; b^=t; a=(a+b)&M; b=(b+a)&M; a=mix64(a); b=mix64(b); a=(a+b)&M; b=(b+a)&M
                return a^b
            term=stack.pop()
            if term=='CDR': Bm(4); term=stack.pop()
            break
def order_key(h): return int(''.join(reversed('%016x'%h)),16)

def bl(k):
    if isinstance(k,str): return json.dumps(k, ensure_ascii=False)
    if isinstance(k,F): return repr(float(k.v)) if 'e' not in repr(float(k.v)) and 'inf' not in repr(k.v) else None
    if isinstance(k,int): return str(k)
    if isinstance(k,T): return '(tuple %s)'%' '.join(bl(x) for x in k.e)
    if isinstance(k,list): return '(list %s)'%' '.join(bl(x) for x in k)

import json
