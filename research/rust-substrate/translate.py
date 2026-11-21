#!/usr/bin/env python3
"""Translate the native seed's stage Scheme (stage2.scm) into Rust.

Usage: translate.py STAGE.scm OUT_DIR
Every Scheme value is a reference-counted `V`; no collector. See README.md.
"""
import sys, os, re, collections
sys.setrecursionlimit(1000000)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sx import *

class NotLoop(Exception): pass

# A let that binds one immutable local to another shares its Rust variable instead of cloning (RS_SHARE=0 disables).
SHARE = os.environ.get('RS_SHARE', '1') != '0'

# Globals the running stage rebinds by name (memoised leaves); they keep a slot and are never called directly.
_dyn = os.environ.get('RS_DYNAMIC', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dynamic-globals.txt'))
DYNAMIC = set(open(_dyn).read().split()) if os.path.exists(_dyn) else set()

BOOL_PRIMS = {'eq?':2,'eqv?':2,'equal?':2,'null?':1,'pair?':1,'vector?':1,'procedure?':1,'fixnum?':1,
 'string?':1,'symbol?':1,'boolean?':1,'exact-integer?':1,'integer?':1,'number?':1,'exact?':1,'list?':1,
 'zero?':1,'even?':1,'eof-object?':1,'uninterned-symbol?':1,'not':1,'fx<':2,'fx>':2,'fx<=':2,'fx>=':2,
 'fx=':2,'<':2,'>':2,'<=':2,'>=':2,'=':2,'char=?':2,'char<=?':2,'char>=?':2,'string=?':2,'##unbound?':1}
VAL_PRIMS = {'cons':2,'car':1,'cdr':1,'cadr':1,'cddr':1,'caddr':1,'cadddr':1,'caar':1,'cdar':1,'cadar':1,
 'vector-ref':2,'vector-length':1,'vector-set!':3,'list->vector':1,'vector->list':1,'vector-copy':1,
 'subvector':3,'subvector-move!':5,'fx+':2,'fx-':2,'fx*':2,'fxquotient':2,'fxmin':2,'quotient':2,
 'remainder':2,'modulo':2,'expt':2,'abs':1,'max':2,'min':2,'exact->inexact':1,'inexact->exact':1,
 'truncate':1,'floor':1,'numerator':1,'denominator':1,'arithmetic-shift':2,'bitwise-not':1,
 'string-length':1,'string-ref':2,'substring':3,'string-set!':3,'string-copy':1,'string->list':1,
 'list->string':1,'string->symbol':1,'symbol->string':1,'string->number':1,'string-upcase':1,
 'string-downcase':1,'substring-move!':5,'char->integer':1,'integer->char':1,'char-upcase':1,
 'length':1,'reverse':1,'list-ref':2,'memv':2,'member':2,'memq':2,'assoc':2,'map':2,'for-each':2,
 'apply':2,'table-ref':3,'table-for-each':2,'raise':1,'with-exception-catcher':2,
 'call-with-current-continuation':1,'dynamic-wind':3,'make-parameter':1,'open-output-string':0,
 'get-output-string':1,'open-input-string':1,'read-char':1,'read':1,'current-error-port':0,
 'current-output-port':0,'force-output':1,'write-substring':4,'eval':2,'interaction-environment':0,
 'command-line':0,'getenv':2,'call-with-input-file':2,'call-with-output-file':2,
 'with-output-to-string':2,'current-time':0,'time->seconds':1,'display-exception':2,
 '##make-global-var':1,'##global-var-ref':1,'##global-var-set!':2,'##gc':0}
VAR_PRIMS = ['list','vector','+','-','*','/','string-append','append','error','make-table','table-set!',
 'number->string','display','write','newline','make-string','string','make-vector','write-char']
SPECIAL = {'define','lambda','let','let*','letrec','letrec*','if','cond','case','and','or','begin','set!',
 'quote','case-lambda','c-lambda','c-declare'}

def san(name):
    if name in ('-', 'fx-'): return {'-': 'sub', 'fx-': 'fxsub'}[name]
    s = name.replace('->', '_to_')
    out = []
    for ch in s:
        if ch.isalnum() and ch.isascii(): out.append(ch)
        elif ch in '-_': out.append('_')
        else: out.append({'?':'_p','!':'_x','<':'lt','>':'gt','=':'eq','+':'add','*':'mul','/':'div',
                          '#':'h',':':'_c','$':'_d','.':'_o'}.get(ch, '_u%x_' % ord(ch)))
    return ''.join(out)

def rstr(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"': out.append('\\"')
        elif ch == '\\': out.append('\\\\')
        elif 32 <= o < 127: out.append(ch)
        else: out.append('\\u{%x}' % o)
    out.append('"')
    return ''.join(out)

def decode_v(name):
    """v_114_116 -> the BL spelling, for comments and local names."""
    m = re.fullmatch(r'(l?v)((?:_\d+)+)(\$.*)?', name)
    if not m: return name
    try: return ''.join(chr(int(c)) for c in m.group(2)[1:].split('_')) + (m.group(3) or '')
    except ValueError: return name

def formals_of(fs):
    """-> (required, optionals[(name, default)], rest or None)"""
    if isinstance(fs, Sym): return [], [], fs
    rest = None
    if isinstance(fs, tuple): rest = fs[2]; fs = fs[1]
    req, opt, mode = [], [], 'req'
    i = 0
    while i < len(fs):
        x = fs[i]
        if x == '#!optional': mode = 'opt'
        elif x == '#!rest': rest = fs[i+1]; i += 1
        elif mode == 'opt': opt.append((x[0], x[1]) if isinstance(x, list) else (x, False))
        else: req.append(x)
        i += 1
    return req, opt, rest

def define_parts(f):
    """(name, value-form) with (define (f . formals) body) normalised to a lambda."""
    t = f[1]
    if isinstance(t, Sym): return t, (f[2] if len(f) > 2 else None)
    if isinstance(t, list): return t[0], [Sym('lambda'), t[1:]] + f[2:]
    return t[1][0], [Sym('lambda'), ('dotted', t[1][1:], t[2])] + f[2:]

class Tr:
    def __init__(self, forms):
        self.forms = forms
        self.gslots = {}; self.gnames = []
        self.syms = {}; self.symnames = []
        self.consts = {}; self.constsrc = []
        self.lnames = {}; self.lused = set()
        self.externs = {}; self.cdecl = []
        self.uid = 0
        self.missing = collections.Counter()
        defined = collections.Counter(); setg = set()
        def scan(x):
            if isinstance(x, list) and x:
                if x[0] == 'quote': return
                if x[0] == 'set!' and isinstance(x[1], Sym): setg.add(x[1])
                for y in x: scan(y)
            elif isinstance(x, tuple):
                for y in x[1]: scan(y)
        for f in forms:
            scan(f)
            if isinstance(f, list) and f and f[0] == 'define': defined[define_parts(f)[0]] += 1
        self.defined = defined
        self.gfn = {}   # name -> arity, for directly callable global functions
        for f in forms:
            if isinstance(f, list) and f and f[0] == 'define':
                name, val = define_parts(f)
                if defined[name] == 1 and name not in setg and name not in DYNAMIC and isinstance(val, list) and val and val[0] == 'lambda':
                    req, opt, rest = formals_of(val[1])
                    if not opt and rest is None: self.gfn[name] = len(req)
        for name in defined: self.gidx(name)
        self.prim_slots = {}
        for name in list(BOOL_PRIMS) + list(VAL_PRIMS) + VAR_PRIMS:
            if name not in defined: self.prim_slots[name] = True; self.gidx(name)
    # ---- tables
    def gidx(self, name):
        if name not in self.gslots:
            self.gslots[name] = len(self.gnames); self.gnames.append(name)
        return self.gslots[name]
    def sym(self, name):
        if name not in self.syms:
            self.syms[name] = len(self.symnames); self.symnames.append(name)
        return self.syms[name]
    def const(self, src):
        if src not in self.consts:
            self.consts[src] = len(self.constsrc); self.constsrc.append(src)
        return self.consts[src]
    def fresh(self, p):
        self.uid += 1; return '%s%d' % (p, self.uid)
    def lname(self, name):
        """A Rust local unique to one binding, so an alias can never be shadowed."""
        self.uid += 1
        return 'l_%s_%d' % (san(decode_v(name))[:32], self.uid)
    # ---- data
    def datum(self, x):
        if x is True: return '#t'
        if x is False: return '#f'
        if isinstance(x, Sym): return '|' + x + '|'
        if isinstance(x, int): return str(x)
        if isinstance(x, float): return repr(x)
        if isinstance(x, Str): return '"' + ''.join('\\x%x;' % ord(c) if (c in '"\\' or ord(c) < 32 or ord(c) > 126) else c for c in x.s) + '"'
        if isinstance(x, Char): return '#\\x%x' % ord(x.c)
        if isinstance(x, list): return '(' + ' '.join(self.datum(y) for y in x) + ')'
        if isinstance(x, tuple) and x[0] == 'dotted': return '(' + ' '.join(self.datum(y) for y in x[1]) + ' . ' + self.datum(x[2]) + ')'
        if isinstance(x, tuple) and x[0] == 'vector': return '#(' + ' '.join(self.datum(y) for y in x[1]) + ')'
        raise Exception('datum %r' % (x,))
    def lit(self, x):
        """(owned expr, ref expr) for a self-evaluating or quoted datum."""
        if x is True or x is False: e = 'V::Bool(%s)' % ('true' if x else 'false'); return e, '&' + e
        if isinstance(x, int) and not isinstance(x, bool) and -2**60 <= x < 2**60:
            e = 'V::Fix(%d)' % x; return e, '&' + e
        if isinstance(x, Sym):
            if x == '#!void': return 'V::Void', '&V::Void'
            e = 'V::Sym(%d)' % self.sym(x); return e, '&' + e
        if isinstance(x, Char): e = 'V::Char(%s)' % ("'\\u{%x}'" % ord(x.c)); return e, '&' + e
        if isinstance(x, list) and not x: return 'V::Null', '&V::Null'
        k = self.const(self.datum(x))
        return 'kc(%d).clone()' % k, 'kc(%d)' % k
    # ---- free variables
    def fv(self, x, bound, out):
        if isinstance(x, Sym):
            if x not in bound: out.add(x)
            return
        if not isinstance(x, list) or not x: return
        h = x[0]
        if isinstance(h, Sym) and h not in bound:
            if h == 'quote' or h == 'c-lambda' or h == 'c-declare': return
            if h == 'lambda':
                req, opt, rest = formals_of(x[1]); b = bound | set(req) | {o[0] for o in opt}
                for o in opt: self.fv(o[1], bound, out)
                if rest is not None: b = b | {rest}
                self.fvbody(x[2:], b, out); return
            if h == 'case-lambda':
                for cl in x[1:]:
                    req, opt, rest = formals_of(cl[0]); b = bound | set(req)
                    if rest is not None: b = b | {rest}
                    self.fvbody(cl[1:], b, out)
                return
            if h == 'let' and isinstance(x[1], Sym):
                for b in x[2]: self.fv(b[1], bound, out)
                self.fvbody(x[3:], bound | {x[1]} | {b[0] for b in x[2]}, out); return
            if h == 'let':
                for b in x[1]: self.fv(b[1], bound, out)
                self.fvbody(x[2:], bound | {b[0] for b in x[1]}, out); return
            if h == 'let*':
                e = bound
                for b in x[1]: self.fv(b[1], e, out); e = e | {b[0]}
                self.fvbody(x[2:], e, out); return
            if h in ('letrec', 'letrec*'):
                e = bound | {b[0] for b in x[1]}
                for b in x[1]: self.fv(b[1], e, out)
                self.fvbody(x[2:], e, out); return
            if h == 'cond':
                for cl in x[1:]:
                    for y in cl:
                        if y not in ('else', '=>'): self.fv(y, bound, out)
                return
            if h == 'case':
                self.fv(x[1], bound, out)
                for cl in x[2:]:
                    for y in cl[1:]: self.fv(y, bound, out)
                return
            if h in ('if', 'and', 'or', 'begin', 'set!', 'define'):
                for y in x[1:]: self.fv(y, bound, out)
                return
        for y in x: self.fv(y, bound, out)
    def fvbody(self, bs, bound, out):
        names = {define_parts(b)[0] for b in bs if isinstance(b, list) and b and b[0] == 'define'}
        for b in bs: self.fv(b, bound | names, out)
    def set_targets(self, xs):
        out = set()
        def w(x):
            if isinstance(x, list) and x:
                if x[0] == 'quote': return
                if x[0] == 'set!': out.add(x[1])
                for y in x: w(y)
            elif isinstance(x, tuple):
                for y in x[1]: w(y)
        for x in xs: w(x)
        return out
    # ---- expressions
    def bind(self, env, name, init, boxed):
        """statement binding `name` to the owned Rust expr `init`; returns (stmt, env')"""
        r = self.lname(name); e = dict(env)
        if name in boxed: e[name] = ('box', r); return 'let %s = bx(%s);' % (r, init), e
        e[name] = ('val', r); return 'let %s: V = %s;' % (r, init), e
    def ref(self, x, env):
        """A Rust expression of type &V."""
        if isinstance(x, Sym):
            b = env.get(x)
            if b is not None:
                if b[0] == 'val': return '&' + b[1]
                if b[0] == 'ref': return b[1]
                if b[0] == 'box': return '&' + b[1] + '.get()'
                if b[0] == 'loop': raise NotLoop()
                if b[0] == 'gfn': return 'g(%d)' % self.gidx(b[1])
            elif x.endswith(':'): return self.lit(x)[1]
            elif x in ('+inf.0', '-inf.0', '1/2'): return 'kc(%d)' % self.const(x)
            else: return 'g(%d)' % self.global_ref(x)
        if isinstance(x, (bool, int, float, Str, Char)): return self.lit(x)[1]
        if isinstance(x, list) and x and x[0] == 'quote' and 'quote' not in env: return self.lit(x[1])[1]
        return '&(' + self.ex(x, env, False) + ')'
    def global_ref(self, name):
        if name not in self.defined and name not in self.gslots:
            if name in BOOL_PRIMS or name in VAL_PRIMS or name in VAR_PRIMS: self.prim_slots[name] = True
            elif not name.startswith('lv_'): self.missing[name] += 1
        return self.gidx(name)
    def boolex(self, x, env):
        """A Rust bool expression, or a Python bool when it folds."""
        if x is False: return False
        if isinstance(x, (bool, int, float, Str, Char)): return True
        if isinstance(x, list) and x and isinstance(x[0], Sym) and x[0] not in env:
            h = x[0]
            if h == 'not' and len(x) == 2:
                b = self.boolex(x[1], env)
                return (not b) if isinstance(b, bool) else '!(%s)' % b
            if h in ('and', 'or'):
                parts = []
                for y in x[1:]:
                    b = self.boolex(y, env)
                    if isinstance(b, bool):
                        if b == (h == 'and'): continue
                        if not parts: return b
                        parts.append('true' if b else 'false'); break
                    parts.append(b)
                if not parts: return h == 'and'
                return '(' + (' && ' if h == 'and' else ' || ').join(parts) + ')'
            if h == 'procedure?' and len(x) == 2 and isinstance(x[1], Sym):
                b = env.get(x[1])
                if b is not None and b[0] in ('loop', 'gfn'): return True
                if b is None and x[1] in self.gfn: return True
            if h == 'eq?' and len(x) == 3:
                for a, o in ((x[1], x[2]), (x[2], x[1])):
                    if a is False: return 'is_false(%s)' % self.ref(o, env)
                    if isinstance(a, list) and len(a) == 2 and a[0] == 'quote' and isinstance(a[1], Sym):
                        return 'is_sym(%s, %d)' % (self.ref(o, env), self.sym(a[1]))
                    if isinstance(a, int) and not isinstance(a, bool):
                        return 'is_fix(%s, %d)' % (self.ref(o, env), a)
            if h in BOOL_PRIMS and h not in self.defined and BOOL_PRIMS[h] == len(x) - 1:
                return 'pb_%s(%s)' % (san(h), ', '.join(self.ref(y, env) for y in x[1:]))
        return 'truthy(%s)' % self.ref(x, env)
    def body(self, bs, env, tail):
        """Rust statements + tail expression for a Scheme body (no braces)."""
        if any(isinstance(b, list) and b and b[0] == 'define' for b in bs):
            binds = [list(define_parts(b)) for b in bs if isinstance(b, list) and b and b[0] == 'define']
            rest = [b for b in bs if not (isinstance(b, list) and b and b[0] == 'define')]
            return self.ex([Sym('letrec'), binds] + rest, env, tail)
        out = []
        for b in bs[:-1]: out.append('let _ = %s;' % self.ex(b, env, False))
        out.append(self.ex(bs[-1], env, tail))
        return ' '.join(out)
    def ex(self, x, env, tail):
        """An owned-V Rust expression."""
        if isinstance(x, Sym):
            b = env.get(x)
            if b is not None:
                if b[0] in ('val', 'ref'): return b[1] + '.clone()'
                if b[0] == 'box': return b[1] + '.get()'
                if b[0] == 'loop': raise NotLoop()
            return self.ref(x, env) + '.clone()'
        if isinstance(x, (bool, int, float, Str, Char)): return self.lit(x)[0]
        if not isinstance(x, list): raise Exception('expr %r' % (x,))
        if not x: raise Exception('empty application')
        h = x[0]
        if isinstance(h, Sym) and h not in env and h in SPECIAL:
            return getattr(self, 'x_' + {'let*': 'letstar', 'letrec*': 'letrec', 'set!': 'set',
                                           'case-lambda': 'caselambda', 'c-lambda': 'clambda',
                                           'c-declare': 'cdeclare'}.get(h, h))(x, env, tail)
        return self.app(x, env, tail)
    def args(self, xs, env): return ', '.join(self.ref(y, env) for y in xs)
    def app(self, x, env, tail):
        h = x[0]; n = len(x) - 1
        if isinstance(h, Sym):
            b = env.get(h)
            if b is not None and b[0] == 'loop':
                _, label, curs, st = b
                if not tail or n != len(curs): raise NotLoop()
                st['used'] = True
                ts = [self.fresh('t') for _ in curs]
                return '{ %s %s continue %s; }' % (
                    ' '.join('let %s = %s;' % (t, self.ex(a, env, False)) for t, a in zip(ts, x[1:])),
                    ' '.join('%s = %s;' % (c, t) for c, t in zip(curs, ts)), label)
            name = b[1] if (b is not None and b[0] == 'gfn') else (h if b is None else None)
            if name is not None:
                if name in self.gfn and self.gfn[name] == n:
                    return 'f_%d(%s)' % (self.gidx(name), self.args(x[1:], env))
                if name not in self.defined:
                    if name in BOOL_PRIMS and BOOL_PRIMS[name] == n:
                        c = self.boolex([Sym(name)] + x[1:], {k: v for k, v in env.items() if k != name})
                        return 'V::Bool(%s)' % ({True: 'true', False: 'false'}.get(c, c) if isinstance(c, bool) else c)
                    if name in VAL_PRIMS and VAL_PRIMS[name] == n:
                        return 'p_%s(%s)' % (san(name), self.args(x[1:], env))
                    if name in VAR_PRIMS:
                        return 'p_%s(&[%s])' % (san(name), self.args(x[1:], env))
        return 'call(%s, &[%s])' % (self.ref(h, env), self.args(x[1:], env))
    def x_quote(self, x, env, tail): return self.lit(x[1])[0]
    def x_if(self, x, env, tail):
        c = self.boolex(x[1], env)
        alt = lambda: self.ex(x[3], env, tail) if len(x) > 3 else 'V::Void'
        if c is True: return self.ex(x[2], env, tail)
        if c is False: return alt()
        return 'if %s { %s } else { %s }' % (c, self.ex(x[2], env, tail), alt())
    def x_and(self, x, env, tail):
        if len(x) == 1: return 'V::Bool(true)'
        if len(x) == 2: return self.ex(x[1], env, tail)
        c = self.boolex(x[1], env); rest = self.x_and([x[0]] + x[2:], env, tail)
        if c is True: return rest
        if c is False: return 'V::Bool(false)'
        return 'if %s { %s } else { V::Bool(false) }' % (c, rest)
    def x_or(self, x, env, tail):
        if len(x) == 1: return 'V::Bool(false)'
        if len(x) == 2: return self.ex(x[1], env, tail)
        t = self.fresh('o')
        return '{ let %s = %s; if truthy(&%s) { %s } else { %s } }' % (
            t, self.ex(x[1], env, False), t, t, self.x_or([x[0]] + x[2:], env, tail))
    def x_begin(self, x, env, tail): return '{ ' + self.body(x[1:], env, tail) + ' }' if len(x) > 1 else 'V::Void'
    def x_set(self, x, env, tail):
        b = env.get(x[1])
        if b is not None:
            if b[0] != 'box': raise Exception('set! of unboxed local %s' % x[1])
            return '{ %s.set(%s); V::Void }' % (b[1], self.ex(x[2], env, False))
        return '{ gset(%d, %s); V::Void }' % (self.gidx(x[1]), self.ex(x[2], env, False))
    def x_define(self, x, env, tail): raise Exception('nested define outside a body')
    def alias(self, name, init, env):
        """A let binding of one name to a loop or a known global function binds no variable."""
        if isinstance(init, Sym):
            b = env.get(init)
            if b is not None and b[0] in ('loop', 'gfn'): return b
            if b is not None and b[0] in ('val', 'ref') and SHARE: return b
            if b is None and init in self.gfn: return ('gfn', init)
        return None
    def x_let(self, x, env, tail):
        if isinstance(x[1], Sym): return self.named_let(x, env, tail)
        binds = x[1]; boxed = self.set_targets(x[2:])
        if len(binds) <= 1 or not any(self.mentions(b[1], {c[0] for c in binds}) for b in binds):
            return self.x_letstar(x, env, tail)
        ts = [self.fresh('p') for _ in binds]; out = []
        for t, b in zip(ts, binds): out.append('let %s = %s;' % (t, self.ex(b[1], env, False)))
        e = env
        for t, b in zip(ts, binds):
            s, e = self.bind(e, b[0], t, boxed); out.append(s)
        return '{ %s %s }' % (' '.join(out), self.body(x[2:], e, tail))
    def mentions(self, x, names):
        out = set(); self.fv(x, frozenset(), out); return bool(out & names)
    def x_letstar(self, x, env, tail):
        boxed = self.set_targets(x[2:]) | self.set_targets([b[1] for b in x[1]]); out = []; e = env
        for b in x[1]:
            a = self.alias(b[0], b[1], e) if b[0] not in boxed else None
            if a is not None: e = dict(e); e[b[0]] = a; continue
            s, e = self.bind(e, b[0], self.ex(b[1], e, False), boxed); out.append(s)
        return '{ %s %s }' % (' '.join(out), self.body(x[2:], e, tail))
    def named_let(self, x, env, tail):
        name = x[1]; binds = x[2]; body = x[3:]
        boxed = self.set_targets(body)
        if name not in boxed:
            saved = self.uid
            try:
                label = "'" + self.fresh('L'); curs = [self.fresh('c') for _ in binds]; st = {}
                e = dict(env); e[name] = ('loop', label, curs, st); top = []
                for c, b in zip(curs, binds):
                    s, e = self.bind(e, b[0], c + '.clone()', boxed); top.append(s)
                inner = self.body(body, e, True)
                inits = ' '.join('let mut %s = %s;' % (c, self.ex(b[1], env, False)) for c, b in zip(curs, binds))
                return '{ %s %s: loop { %s break %s ({ %s }); } }' % (inits, label, ' '.join(top), label, inner)
            except NotLoop:
                self.uid = saved
        lam = [Sym('lambda'), [b[0] for b in binds]] + body
        return self.ex([Sym('letrec'), [[name, lam]], [name] + [b[1] for b in binds]], env, tail)
    def x_letrec(self, x, env, tail):
        binds = x[1]; body = x[2:]
        boxed = self.set_targets(body) | self.set_targets([b[1] for b in binds])
        if len(binds) == 1 and binds[0][0] not in boxed and isinstance(binds[0][1], list) and binds[0][1] and binds[0][1][0] in ('lambda', 'case-lambda'):
            name = binds[0][0]; r = self.lname(name)
            e = dict(env); e[name] = ('val', r)
            return '{ let %s: V = %s; %s }' % (r, self.lam(binds[0][1], env, name), self.body(body, e, tail))
        e = dict(env); out = []
        for b in binds:
            r = self.lname(b[0]); e[b[0]] = ('box', r); out.append('let %s = bx(V::Void);' % r)
        for b in binds: out.append('%s.set(%s);' % (e[b[0]][1], self.ex(b[1], e, False)))
        return '{ %s %s }' % (' '.join(out), self.body(body, e, tail))
    def x_cond(self, x, env, tail):
        if len(x) == 1: return 'V::Void'
        cl = x[1]; rest = [x[0]] + x[2:]
        if cl[0] == 'else': return '{ ' + self.body(cl[1:], env, tail) + ' }'
        if len(cl) == 1: return self.x_or([Sym('or'), cl[0], rest], env, tail)
        if cl[1] == '=>':
            t = self.fresh('o')
            return '{ let %s = %s; if truthy(&%s) { call(%s, &[&%s]) } else { %s } }' % (
                t, self.ex(cl[0], env, False), t, self.ref(cl[2], env), t, self.x_cond(rest, env, tail))
        c = self.boolex(cl[0], env)
        if c is True: return '{ ' + self.body(cl[1:], env, tail) + ' }'
        if c is False: return self.x_cond(rest, env, tail)
        return 'if %s { %s } else { %s }' % (c, self.body(cl[1:], env, tail), self.x_cond(rest, env, tail))
    def x_case(self, x, env, tail):
        t = self.fresh('k'); out = []
        for cl in x[2:]:
            if cl[0] == 'else': out.append('{ %s }' % self.body(cl[1:], env, tail)); break
            test = ' || '.join('pb_eqv_p(&%s, %s)' % (t, self.lit(d)[1]) for d in cl[0])
            out.append('if %s { %s } else ' % (test, self.body(cl[1:], env, tail)))
        else: out.append('{ V::Void }')
        return '{ let %s = %s; %s }' % (t, self.ex(x[1], env, False), ''.join(out))
    def x_lambda(self, x, env, tail): return self.lam(x, env, None)
    def x_caselambda(self, x, env, tail): return self.lam(x, env, None)
    def clause(self, formals, body, env):
        """(arity test on `n`, statements + tail) for one lambda clause over args `a`."""
        req, opt, rest = formals_of(formals)
        boxed = self.set_targets(body); e = dict(env); out = []
        for i, p in enumerate(req):
            r = self.lname(p)
            if p in boxed: e[p] = ('box', r); out.append('let %s = bx(a[%d].clone());' % (r, i))
            else: e[p] = ('ref', r); out.append('let %s: &V = a[%d];' % (r, i))
        for j, (p, d) in enumerate(opt):
            i = len(req) + j
            s, e = self.bind(e, p, 'if a.len() > %d { a[%d].clone() } else { %s }' % (i, i, self.ex(d, e, False)), boxed)
            out.append(s)
        if rest is not None:
            s, e = self.bind(e, rest, 'list_from(&a[%d.min(a.len())..])' % (len(req) + len(opt)), boxed); out.append(s)
        lo = len(req); hi = None if rest is not None else lo + len(opt)
        test = ('n == %d' % lo) if hi == lo else ('n >= %d' % lo if hi is None else '(n >= %d && n <= %d)' % (lo, hi))
        return test, ' '.join(out) + ' ' + self.body(body, e, False)
    def lam(self, x, env, selfname):
        free = set(); self.fv(x, frozenset([selfname] if selfname else []), free)
        caps = []; inner = {}
        for v in sorted(free):
            b = env.get(v)
            if b is None: continue
            if b[0] == 'loop': raise NotLoop()
            if b[0] == 'gfn': inner[v] = b; continue
            caps.append('let %s = %s.clone();' % (b[1], b[1]))
            inner[v] = ('box', b[1]) if b[0] == 'box' else ('val', b[1])
        if selfname: inner[selfname] = ('ref', self.lname(selfname))
        if x[0] == 'lambda':
            test, code = self.clause(x[1], x[2:], inner)
            fn = '{ let n = a.len(); if !(%s) { return arity_error(n); } %s }' % (test, code)
        else:
            arms = []
            for cl in x[1:]:
                test, code = self.clause(cl[0], cl[1:], inner)
                arms.append('if %s { %s } else ' % (test, code))
            fn = '{ let n = a.len(); %s{ arity_error(n) } }' % ''.join(arms)
        if selfname: mk = 'mkrec(move |%s: &V, a: &[&V]| -> V %s)' % (inner[selfname][1], fn)
        else: mk = 'mk(move |a: &[&V]| -> V %s)' % fn
        return '{ %s %s }' % (' '.join(caps), mk) if caps else mk
    CT = {'UTF-8-string': 'str', 'char-string': 'str', 'unsigned-long-long': 'u64', 'long-long': 'i64',
          'int': 'i32', 'unsigned-int': 'u32', 'long': 'i64', 'double': 'f64', 'void': 'void'}
    def ctype(self, t): return 'ptr' if isinstance(t, list) else self.CT[t]
    def x_clambda(self, x, env, tail):
        ats = [self.ctype(t) for t in x[1]]; rt = self.ctype(x[2]); cname = x[3].s
        RT = {'str': '*const c_char', 'u64': 'u64', 'i64': 'i64', 'i32': 'i32', 'u32': 'u32', 'f64': 'f64', 'ptr': '*mut c_void'}
        self.externs[cname] = 'fn %s(%s)%s;' % (cname, ', '.join('a%d: %s' % (i, RT[t]) for i, t in enumerate(ats)),
                                                '' if rt == 'void' else ' -> ' + RT[rt])
        pre = []; args = []
        for i, t in enumerate(ats):
            if t == 'str': pre.append('let s%d = c_string(a[%d]);' % (i, i)); args.append('s%d.as_ptr()' % i)
            elif t == 'ptr': args.append('c_ptr(a[%d])' % i)
            elif t == 'f64': args.append('c_f64(a[%d])' % i)
            else: args.append('c_int(a[%d]) as %s' % (i, t))
        callx = 'unsafe { %s(%s) }' % (cname, ', '.join(args))
        ret = {'void': '{ %s; V::Void }', 'ptr': 'from_ptr(%s)', 'f64': 'V::Flo(%s)'}.get(rt, 'V::Fix(%s as i64)') % callx
        return 'mk(move |a: &[&V]| -> V { if a.len() != %d { return arity_error(a.len()); } %s %s })' % (len(ats), ' '.join(pre), ret)
    def x_cdeclare(self, x, env, tail):
        self.cdecl.append(x[1].text if isinstance(x[1], CDecl) else x[1].s); return 'V::Void'
    # ---- top level
    def plain_params(self, req, boxed):
        env = {}; pre = []; params = []
        for p in req:
            r = self.lname(p); params.append('%s: &V' % r)
            if p in boxed: env[p] = ('box', r + '_b'); pre.append('let %s_b = bx(%s.clone());' % (r, r))
            else: env[p] = ('ref', r)
        return env, pre, params
    def toplevel(self):
        fns = []; init = []
        for f in self.forms:
            self.lnames = {}; self.lused = set()
            if isinstance(f, list) and f and f[0] == 'define':
                name, val = define_parts(f); i = self.gidx(name)
                if name in self.gfn:
                    req, _, _ = formals_of(val[1]); body = val[2:]
                    boxed = self.set_targets(body); code = None
                    if self.mentions(val, {name}):
                        saved = self.uid
                        label = "'" + self.fresh('S'); curs = [self.fresh('c') for _ in req]; st = {}
                        env = {name: ('loop', label, curs, st)}; pre = []
                        for c, p in zip(curs, req):
                            s, env = self.bind(env, p, c + '.clone()', boxed); pre.append(s)
                        try:
                            inner = self.body(body, env, True)
                            params = ['%s_in: &V' % c for c in curs]
                            code = '%s %s: loop { %s break %s ({ %s }); }' % (
                                ' '.join('let mut %s: V = %s_in.clone();' % (c, c) for c in curs), label, ' '.join(pre), label, inner)
                        except NotLoop:
                            self.uid = saved
                    if code is None:
                        env, pre, params = self.plain_params(req, boxed)
                        code = ' '.join(pre) + ' ' + self.body(body, env, False)
                    fns.append('// %s\npub fn f_%d(%s) -> V { %s }\n' % (decode_v(name).replace('\n', ' '), i, ', '.join(params), code))
                    n = len(req)
                    init.append('gset(%d, mk(|a: &[&V]| -> V { if a.len() != %d { return arity_error(a.len()); } f_%d(%s) }));' % (
                        i, n, i, ', '.join('a[%d]' % k for k in range(n))))
                else:
                    init.append('gset(%d, %s);' % (i, self.ex(val, {}, False) if val is not None else 'V::Void'))
            else:
                init.append('let _ = %s;' % self.ex(f, {}, False))
        return fns, init

def main():
    src, out = sys.argv[1], sys.argv[2]
    forms = read_all(open(src, encoding='utf-8').read())
    t = Tr(forms)
    fns, init = t.toplevel()
    os.makedirs(out, exist_ok=True)
    prims = []
    for name in sorted(t.prim_slots):
        i = t.gslots[name]
        if name in BOOL_PRIMS:
            n = BOOL_PRIMS[name]
            prims.append('gset(%d, mkn(%s, |a: &[&V]| -> V { if a.len() != %d { return arity_error(a.len()); } V::Bool(pb_%s(%s)) }));' % (
                i, rstr(name), n, san(name), ', '.join('a[%d]' % k for k in range(n))))
        elif name in VAL_PRIMS:
            n = VAL_PRIMS[name]
            prims.append('gset(%d, mkn(%s, |a: &[&V]| -> V { if a.len() != %d { return arity_error(a.len()); } p_%s(%s) }));' % (
                i, rstr(name), n, san(name), ', '.join('a[%d]' % k for k in range(n))))
        else: prims.append('gset(%d, mkn(%s, |a: &[&V]| -> V { p_%s(a) }));' % (i, rstr(name), san(name)))
    HEAD = '#![allow(warnings)]\nuse crate::rt::*;\nuse crate::generated::*;\nuse std::ffi::{c_char, c_void};\n'
    mods = []; cur = []; size = 0; LIMIT = int(os.environ.get('RS_MODULE_BYTES', '700000'))
    def flush():
        nonlocal cur, size
        if cur:
            m = 'c%02d' % len(mods); mods.append(m)
            open(os.path.join(out, m + '.rs'), 'w').write(HEAD + ''.join(cur))
        cur = []; size = 0
    for fn in fns:
        cur.append(fn); size += len(fn)
        if size > LIMIT: flush()
    flush()
    chunks = []; cur = []; size = 0; text = []
    for st in prims + init:
        cur.append(st); size += len(st)
        if size > 60000 or len(cur) >= 200:
            chunks.append(cur); cur = []; size = 0
    if cur: chunks.append(cur)
    for k, ch in enumerate(chunks):
        text.append('#[inline(never)] fn init_%d() { %s }\n' % (k, '\n'.join(ch)))
    text.append('pub fn init() { %s }\n' % ' '.join('init_%d();' % k for k in range(len(chunks))))
    ext = 'unsafe extern "C" { %s }\n' % ' '.join(t.externs[k] for k in sorted(t.externs))
    open(os.path.join(out, 'init.rs'), 'w').write(HEAD + ext + ''.join(text))
    tables = ['#![allow(warnings)]\n']
    tables.append('pub static GNAMES: &[&str] = &[%s];\n' % ', '.join(rstr(n) for n in t.gnames))
    tables.append('pub static GSTATIC: &[bool] = &[%s];\n' % ', '.join('true' if n in t.gfn else 'false' for n in t.gnames))
    tables.append('pub static SYMS: &[&str] = &[%s];\n' % ', '.join(rstr(n) for n in t.symnames))
    tables.append('pub static KSRC: &[&str] = &[%s];\n' % ', '.join(rstr(n) for n in t.constsrc))
    open(os.path.join(out, 'tables.rs'), 'w').write(''.join(tables))
    allm = mods + ['init', 'tables']
    open(os.path.join(out, 'mod.rs'), 'w').write(''.join('pub mod %s;\npub use %s::*;\n' % (m, m) for m in allm))
    open(os.path.join(out, 'host.c'), 'w').write('\n'.join(t.cdecl))
    total = sum(os.path.getsize(os.path.join(out, m + '.rs')) for m in allm)
    print('forms %d  direct fns %d  globals %d  symbols %d  constants %d  modules %d  rust bytes %d' % (
        len(forms), len(t.gfn), len(t.gnames), len(t.symnames), len(t.constsrc), len(mods), total))
    print('prims used as values or dynamically: %d' % len(t.prim_slots))
    if t.missing: print('UNDEFINED non-link globals:', dict(t.missing.most_common(60)))
    used = sorted(set(re.findall(r'\b(pb?_[A-Za-z0-9_]+)\(', ''.join(fns) + '\n'.join(init) + '\n'.join(prims))))
    open(os.path.join(out, 'prims-used.txt'), 'w').write('\n'.join(used) + '\n')

if __name__ == '__main__': main()
