# Minimal reader for the Gambit-dialect Scheme the native seed emits.
import re, sys
class Sym(str):
    __slots__=()
    def __repr__(self): return 'S(%s)'%str.__repr__(self)
class Char:
    def __init__(s,c): s.c=c
class Str:
    __slots__=('s',)
    def __init__(s,v): s.s=v
class CDecl:
    def __init__(s,t): s.text=t
QUOTE=Sym('quote'); QQ=Sym('quasiquote'); UQ=Sym('unquote'); UQS=Sym('unquote-splicing')
DELIM=set(' \t\n\r()";\'`,')
CHARNAMES={'space':' ','newline':'\n','tab':'\t','nul':'\0','null':'\0','return':'\r','linefeed':'\n','delete':'\x7f','escape':'\x1b','esc':'\x1b','backspace':'\b','alarm':'\a','rubout':'\x7f'}
def read_all(t):
    n=len(t); i=0; out=[]
    def skip(i):
        while i<n:
            c=t[i]
            if c in ' \t\n\r': i+=1
            elif c==';':
                while i<n and t[i]!='\n': i+=1
            elif c=='#' and t.startswith('#|',i):
                i=t.index('|#',i)+2
            elif c=='#' and t.startswith('#;',i):
                _,i=rd(i+2)
            else: break
        return i
    def rd(i):
        i=skip(i)
        c=t[i]
        if c=='(' or c=='[':
            i+=1; xs=[]; tail=None
            while True:
                i=skip(i)
                if t[i] in ')]': return (xs if tail is None else ('dotted',xs,tail)), i+1
                if t[i]=='.' and t[i+1] in DELIM:
                    tail,i=rd(i+1); continue
                x,i=rd(i); xs.append(x)
        if c=="'": x,i=rd(i+1); return [QUOTE,x],i
        if c=='`': x,i=rd(i+1); return [QQ,x],i
        if c==',':
            if t[i+1]=='@': x,i=rd(i+2); return [UQS,x],i
            x,i=rd(i+1); return [UQ,x],i
        if c=='"':
            j=i+1; buf=[]
            while t[j]!='"':
                if t[j]=='\\':
                    e=t[j+1]
                    if e=='x':
                        k=t.index(';',j); buf.append(chr(int(t[j+2:k],16))); j=k+1; continue
                    if e=='\n':
                        j+=2
                        while t[j] in ' \t': j+=1
                        continue
                    buf.append({'n':'\n','t':'\t','r':'\r','a':'\a','0':'\0','b':'\b'}.get(e,e)); j+=2
                else: buf.append(t[j]); j+=1
            return Str(''.join(buf)), j+1
        if c=='#':
            if t.startswith('#<<',i):
                e=t.index('\n',i); tag=t[i+3:e]; k=t.index('\n'+tag,e)
                return CDecl(t[e+1:k]), k+1+len(tag)
            if t[i+1]=='(':
                x,i=rd(i+1); return ('vector',x),i
            if t[i+1]=='\\':
                j=i+3
                while j<n and t[j] not in DELIM: j+=1
                tok=t[i+2:j]
                if len(tok)==1: return Char(tok),j
                if tok in CHARNAMES: return Char(CHARNAMES[tok]),j
                if tok[0] in 'xU' and len(tok)>1:
                    try: return Char(chr(int(tok[1:],16))),j
                    except ValueError: pass
                # single char followed by non-delimiters, e.g. #\a)
                return Char(tok[0]), i+3
        if c=='|':
            j=t.index('|',i+1); return Sym(t[i+1:j]), j+1
        j=i
        while j<n and t[j] not in DELIM:
            if t[j]=='|': j=t.index('|',j+1)
            j+=1
        tok=t[i:j]
        if tok=='#t' or tok=='#true': return True,j
        if tok=='#f' or tok=='#false': return False,j
        if re.fullmatch(r'[-+]?\d+',tok): return int(tok),j
        if re.fullmatch(r'[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?',tok): return float(tok),j
        if tok.startswith('#x'): return int(tok[2:],16),j
        return Sym(tok.replace('|','')),j
    while True:
        i=skip(i)
        if i>=n: return out
        x,i=rd(i); out.append(x)
