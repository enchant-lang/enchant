#!/usr/bin/env python3
"""Show that every emission difference is one of N1's four rewrites.

Both sides are parsed as Scheme data and put through the same canonical
rewrites, one per N1 item, each the inverse of exactly one emitter change:

  (a) boolean junction  (let ((t E)) (if (or (eq? t #f) (eq? t bl-nil)) F T))  ->  (if E T F)
  (b) keyword dispatch  (case X ((k1 k2) R) ... (else E))  ->  (if (eq? X 'k1) R (if (eq? X 'k2) R ... E))
                        and the template test (let* ((a0 X) (a1 'k)) (eq? a0 a1))  ->  (eq? X 'k)
  (c) direct self-call  inside (let ((callee F)) ...) where F is a function scaffold's letrec
                        local:  (if (procedure? callee) (callee A..) (bl-invoke callee (list A..)))  ->  (callee A..)
  (d) keyword constant  (string->symbol ":k")  and  '|:k|  ->  one constant

A pair passes when the texts are equal, or when their canonical forms are equal;
the rewrites whose firing counts differ between the sides are the explanation.

usage: explain.py pairs OLD NEW    records "\\x1e LABEL \\n TEXT" (speed/backend3/equality.bl)
       explain.py forms OLD NEW    top-level forms, compared in order (chunks inspect, emitted rt)
"""
import collections
import re
import sys
import threading

SAFE = re.compile(r'^:[0-9A-Za-z\-_?!*+<>=/.$%&~^@:]*$')


def parse(text):
    """Iterative reader: lists, 'quote, "strings", |symbols|, atoms."""
    out, stack, i, n = [], [], 0, len(text)
    pending_quote = []  # per depth: count of quotes waiting for the next datum

    def push(datum):
        target = stack[-1] if stack else out
        target.append(datum)

    def finish(datum):
        # apply quotes registered at this depth
        depth = len(stack)
        while pending_quote and pending_quote[-1][0] == depth:
            pending_quote.pop()
            datum = ("L", [("A", "quote"), datum])
        push(datum)

    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c == ";":
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            items = stack.pop()
            i += 1
            finish(("L", items))
        elif c == "'":
            pending_quote.append((len(stack),))
            i += 1
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            finish(("T", text[i + 1:j]))
            i = j + 1
        elif c == "|":
            j = i + 1
            while text[j] != "|":
                j += 2 if text[j] == "\\" else 1
            finish(("S", text[i + 1:j]))
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()\";'|":
                j += 1
            if j == i:
                raise ValueError(f"unreadable at {i}: {text[i:i+40]!r}")
            finish(("A", text[i:j]))
            i = j
    if stack:
        raise ValueError("unbalanced input")
    return out


def A(name):
    return ("A", name)


def L(*items):
    return ("L", list(items))


def is_list(x, head=None, size=None):
    if x[0] != "L":
        return False
    if head is not None and (not x[1] or x[1][0] != A(head)):
        return False
    return size is None or len(x[1]) == size


SELF_INITS = {"case-lambda", "lambda", "bl-register-callable!"}
TRUTHY_TEST = L(A("or"), L(A("eq?"), A("t"), A("#f")), L(A("eq?"), A("t"), A("bl-nil")))


def procedure_if(x, argv):
    """(if (procedure? callee) (callee A..) (bl-invoke callee (list A..))) -> A.., else None."""
    if not is_list(x, "if", 4) or x[1][1] != L(A("procedure?"), A("callee")):
        return None
    call, invoke = x[1][2], x[1][3]
    if argv:
        if call == L(A("apply"), A("callee"), A("arguments")) and invoke == L(A("bl-invoke"), A("callee"), A("arguments")):
            return "apply"
        return None
    if is_list(call) and call[1] and call[1][0] == A("callee") and is_list(invoke, "bl-invoke", 3) \
            and invoke[1][1] == A("callee") and invoke[1][2] == ("L", [A("list")] + call[1][1:]):
        return call
    return None


def self_ref(x, selves):
    return x[0] == "A" and x in selves


def canon(x, selves, counts):
    if x[0] != "L":
        return x
    items = x[1]
    inner = selves
    if is_list(x, "letrec", 3) and is_list(items[1], size=1) and is_list(items[1][1][0], size=2):
        name, init = items[1][1][0][1]
        if items[2] == name and is_list(init) and init[1] and init[1][0][0] == "A" and init[1][0][1] in SELF_INITS:
            inner = selves | {name}
    x = ("L", [canon(y, inner, counts) for y in items])
    items = x[1]
    # (d) keyword constants
    if len(items) == 2 and items[0] == A("string->symbol") and items[1][0] == "T" and SAFE.match(items[1][1]):
        counts["d string->symbol"] += 1
        return ("Q", items[1][1])
    if len(items) == 2 and items[0] == A("quote") and items[1][0] == "S" and SAFE.match(items[1][1]):
        counts["d quoted"] += 1
        return ("Q", items[1][1])
    # (b) the keyword template test, either operand order
    if is_list(x, "let*", 3) and is_list(items[1], size=2):
        b0, b1 = items[1][1]
        if is_list(b0, size=2) and is_list(b1, size=2) and b0[1][0] == A("a0") and b1[1][0] == A("a1"):
            v0, v1 = b0[1][1], b1[1][1]
            if items[2] == L(A("eq?"), A("a0"), A("a1")) and v0[0] == "A" and v1[0] == "Q":
                counts["b template test"] += 1
                return L(A("eq?"), v0, v1)
            if items[2] == L(A("eq?"), A("a1"), A("a0")) and v1[0] == "A" and v0[0] == "Q":
                counts["b template test"] += 1
                return L(A("eq?"), v1, v0)
    # (b) keyword dispatch
    if is_list(x, "case") and len(items) >= 3 and is_list(items[-1], "else", 2):
        subject, out = items[1], items[-1][1][1]
        for clause in reversed(items[2:-1]):
            datums, body = clause[1]
            for d in reversed(datums[1]):
                out = L(A("if"), L(A("eq?"), subject, ("Q", d[1])), body, out)
        counts["b case"] += 1
        counts["b case datums"] += sum(len(c[1][0][1]) for c in items[2:-1])
        return out
    # (a) truthiness wrapper
    if is_list(x, "let", 3) and is_list(items[1], size=1) and is_list(items[1][1][0], size=2) \
            and items[1][1][0][1][0] == A("t") and is_list(items[2], "if", 4) and items[2][1][1] == TRUTHY_TEST:
        _, _, f, t = items[2][1]
        counts["a truthiness wrapper"] += 1
        return L(A("if"), items[1][1][0][1][1], t, f)
    # (c) self-call through a procedure? test
    if is_list(x) and len(items) >= 1 and items[0] == A("let") and len(items) == 3 and is_list(items[1], size=1) \
            and is_list(items[1][1][0], size=2) and items[1][1][0][1][0] == A("callee") \
            and self_ref(items[1][1][0][1][1], selves):
        counts["c self-call sites"] += 1
    if is_list(x, "let", 3) and is_list(items[1], size=1) and is_list(items[1][1][0], size=2) \
            and items[1][1][0][1][0] == A("callee") and self_ref(items[1][1][0][1][1], selves):
        body = items[2]
        hit = procedure_if(body, False)
        if hit:
            counts["c self-call test"] += 1
            return L(items[0], items[1], hit)
        if is_list(body, "let*", 3):
            hit = procedure_if(body[1][2], False)
            if hit:
                counts["c self-call test"] += 1
                return L(items[0], items[1], L(A("let*"), body[1][1], hit))
    if is_list(x, "let*", 3) and is_list(items[1], size=2) and is_list(items[1][1][0], size=2) \
            and items[1][1][0][1][0] == A("callee") and self_ref(items[1][1][0][1][1], selves):
        counts["c self-call sites"] += 1
    if is_list(x, "let*", 3) and is_list(items[1], size=2) and is_list(items[1][1][0], size=2) \
            and items[1][1][0][1][0] == A("callee") and self_ref(items[1][1][0][1][1], selves) \
            and is_list(items[1][1][1], size=2) and items[1][1][1][1][0] == A("arguments") \
            and procedure_if(items[2], True):
        counts["c self-call test"] += 1
        return L(items[0], items[1], L(A("apply"), A("callee"), A("arguments")))
    return x


def show(x, limit=400):
    def w(y):
        t = y[0]
        if t == "L":
            return "(" + " ".join(w(z) for z in y[1]) + ")"
        if t == "T":
            return '"' + y[1] + '"'
        if t == "S":
            return "|" + y[1] + "|"
        if t == "Q":
            return "'" + y[1]
        return y[1]
    s = w(x)
    return s if len(s) <= limit else s[:limit] + "…"


def first_difference(a, b):
    while a != b:
        if a[0] == "L" and b[0] == "L" and len(a[1]) == len(b[1]):
            k = next(i for i, (p, q) in enumerate(zip(a[1], b[1])) if p != q)
            a, b = a[1][k], b[1][k]
        else:
            return a, b
    return None


def compare(label, old_text, new_text, tally, kinds, failures):
    if old_text == new_text:
        tally["identical"] += 1
        return
    if old_text.startswith("REFUSED") or new_text.startswith("REFUSED"):
        failures.append((label, "refusal differs", old_text[:300], new_text[:300]))
        return
    try:
        po, pn = parse(old_text), parse(new_text)
    except (ValueError, IndexError) as e:
        failures.append((label, f"parse: {e}", old_text[:200], new_text[:200]))
        return
    compare_parsed(label, po, pn, tally, kinds, failures)


def compare_parsed(label, po, pn, tally, kinds, failures):
    if po == pn:
        tally["identical"] += 1
        return
    co, cn = collections.Counter(), collections.Counter()
    a = [canon(x, frozenset(), co) for x in po]
    b = [canon(x, frozenset(), cn) for x in pn]
    if a == b:
        tally["different, explained"] += 1
        why = []
        for k in sorted(set(co) | set(cn)):
            if co[k] != cn[k]:
                why.append(k)
                kinds[k] += abs(co[k] - cn[k])
        tally["explained by " + " + ".join(sorted({w.split(" ")[0] for w in why}))] += 1
    else:
        tally["UNEXPLAINED"] += 1
        d = first_difference(L(*a), L(*b))
        failures.append((label, "canonical forms differ", show(d[0]) if d else "", show(d[1]) if d else ""))


def records(path):
    text = open(path, encoding="utf-8").read()
    for chunk in text.split("\x1e")[1:]:
        label, _, body = chunk.partition("\n")
        yield label, body


def count(path):
    """Occurrences of each N1 shape in one emitted file (the canonical rewrites
    that fire on it, plus self-call sites and every remaining truthiness test)."""
    text = open(path, encoding="utf-8").read()
    counts = collections.Counter()
    for x in parse(text):
        canon(x, frozenset(), counts)
    counts["a truthiness tests, all (text)"] = text.count("(if (or (eq? t #f) (eq? t bl-nil))")
    counts["d string->symbol, all (text)"] = text.count("(string->symbol ")
    counts["procedure? callee tests, all (text)"] = text.count("(if (procedure? callee)")
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}")
    return 0


def main():
    if sys.argv[1] == "count":
        return count(sys.argv[2])
    mode, old, new = sys.argv[1:4]
    tally, kinds, failures = collections.Counter(), collections.Counter(), []
    if mode == "pairs":
        a, b = list(records(old)), list(records(new))
        assert [x[0] for x in a] == [x[0] for x in b], "record labels differ"
        for (label, x), (_, y) in zip(a, b):
            compare(label, x, y, tally, kinds, failures)
    else:
        a = parse(open(old, encoding="utf-8").read())
        b = parse(open(new, encoding="utf-8").read())
        assert len(a) == len(b), f"form counts differ: {len(a)} {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            compare_parsed(f"form {i}: {show(x, 120)}", [x], [y], tally, kinds, failures)
    total = sum(v for k, v in tally.items() if k in ("identical", "different, explained", "UNEXPLAINED"))
    print("compared", total)
    for k in sorted(tally):
        print(" ", k, tally[k])
    print("rewrites that differ between the sides (occurrences):")
    for k in sorted(kinds):
        print(" ", k, kinds[k])
    for f in failures[:20]:
        print("FAIL", *f, sep="\n  ")
    print("EXPLAIN_OK" if not failures else "EXPLAIN_FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.setrecursionlimit(10**6)
    threading.stack_size(1 << 29)
    result = []
    t = threading.Thread(target=lambda: result.append(main()))
    t.start()
    t.join()
    sys.exit(result[0] if result else 2)
