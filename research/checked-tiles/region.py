"""Read a deliberately small, closed subset of ordinary BL definitions.

Only previously defined unary helpers can be called. No globals, effects,
implicit narrowing, division by zero, or arbitrary target-language text.
"""
import re

TOKEN = re.compile(r'\s+|;[^\n]*|[()\[\]]|[+*<]|[a-z][a-z0-9-]*|[0-9]+')
MAX = 2**32 - 1


def forms(source):
    if len(source) > 8192:
        raise ValueError("source exceeds the 8 KiB region limit")
    stack = [([], None)]
    pos = 0
    for match in TOKEN.finditer(source):
        token = match.group()
        if match.start() != pos:
            raise ValueError(f"unsupported syntax at byte {pos}")
        pos = match.end()
        if token.isspace() or token.startswith(';'):
            continue
        if token in ('(', '['):
            if len(stack) > 32:
                raise ValueError("nesting exceeds 32")
            stack.append(([], ')' if token == '(' else ']'))
        elif token in (')', ']'):
            items, closing = stack.pop()
            if closing != token:
                raise ValueError("mismatched delimiter")
            stack[-1][0].append(items if closing == ')' else tuple(items))
        else:
            stack[-1][0].append(token)
    if pos != len(source) or len(stack) != 1:
        raise ValueError("incomplete or unsupported source")
    return stack[0][0]


def compile_region(source):
    functions = {}
    output = []
    for form in forms(source):
        match form:
            case ['defn', str(name), (str(arg),), body]:
                pass
            case _:
                raise ValueError("expected (defn name [x] expression)")
        if not all(re.fullmatch('[a-z][a-z0-9-]*', s) for s in (name, arg)):
            raise ValueError("invalid binder")
        if name in functions or name in ('if', 'quot', 'defn') or arg in functions:
            raise ValueError("ambiguous binding")
        # Internal target names cannot collide with C keywords or Lean names.
        ident = f'f{len(functions)}'
        def expr(node):
            if node == arg:
                return 'x', 'x', 255
            if isinstance(node, str) and node.isdigit() and str(int(node)) == node and int(node) <= MAX:
                return node + 'u', node, int(node)
            match node:
                case ['if', ['<', a, b], yes, no]:
                    ac, al, _ = expr(a)
                    bc, bl, _ = expr(b)
                    yc, yl, yh = expr(yes)
                    nc, nl, nh = expr(no)
                    return f'({ac} < {bc} ? {yc} : {nc})', f'(if {al} < {bl} then {yl} else {nl})', max(yh, nh)
                case [op, a, b] if op in ('+', '*', 'quot'):
                    ac, al, ah = expr(a)
                    bc, bl, bh = expr(b)
                    if op == 'quot':
                        if not isinstance(b, str) or not b.isdigit() or not bh:
                            raise ValueError("quot requires a positive literal divisor")
                        op, high = '/', ah // bh
                    else:
                        high = ah + bh if op == '+' else ah * bh
                    if high > MAX:
                        raise ValueError("unproved u32 intermediate bound")
                    return f'({ac} {op} {bc})', f'({al} {op} {bl})', high
                case [str(helper), val] if helper in functions:
                    c, lean, high = expr(val)
                    if high > 255:
                        raise ValueError("helper argument exceeds byte domain")
                    h, bound = functions[helper]
                    return f'{h}({c})', f'({h} {lean})', bound
            raise ValueError(f"outside the pure channel fragment: {node!r}")
        c, lean, bound = expr(body)
        functions[name] = (ident, bound)
        output.append((ident, c, lean))
    if 'pixel' not in functions:
        raise ValueError("missing pixel definition")
    c = '\n'.join(f'static inline unsigned {k}(unsigned x) {{ return {v}; }}' for k, v, _ in output)
    lean = '\n'.join(f'def {k} (x : Nat) : Nat := {v}' for k, _, v in output)
    return c, lean, functions['pixel'][0]
