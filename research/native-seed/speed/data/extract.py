#!/usr/bin/env python3
"""Extract from the reference prelude only the compiled closure definitions
that the emitted DATA modules reach, so the interpreted gsi check loads a few
hundred KB instead of the 4.9 MB prelude (whose host part also carries C FFI
that gsi cannot interpret).

Usage: extract.py PRELUDE EMITTED.scm OUT.scm
Writes OUT.scm = native-install-bundle! form + every top-level form owned by
a reached binding (definition, registration, meta, arities, link cells,
seed links), in prelude order. Prints the counts.
"""
import re
import sys
from pathlib import Path

TOKEN = re.compile(r"v(?:_\d+)+")


def forms(text):
    """Top-level s-expressions of TEXT (strings, chars, comments, #<< heredocs)."""
    out, i, n, depth, start = [], 0, len(text), 0, None
    while i < n:
        c = text[i]
        if c == ";" and depth >= 0:
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if c == '"':
            i += 1
            while text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == "#" and text.startswith("#\\", i):
            i += 3
            while i < n and text[i].isalnum():
                i += 1
            continue
        if c == "(":
            if depth == 0:
                start = i
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                out.append(text[start:i + 1])
        i += 1
    return out


def ident(s):
    return "v" + "".join("_" + str(ord(c)) for c in s)


OWNER = re.compile(r'^\((?:native-register!|native-put-meta|native-register-arities!|native-link!|native-link-global!) "([^"]*)" "([^"]*)"')
DEFINE = re.compile(r"^\(define (v(?:_\d+)+)")


def owner(form):
    m = DEFINE.match(form)
    if m:
        return m.group(1)
    m = OWNER.match(form)
    if m:
        return ident(m.group(1) + "/" + m.group(2))
    return None


def main():
    prelude, emitted, out = (Path(a) for a in sys.argv[1:4])
    text = prelude.read_text()
    at = text.index("\n(native-install-bundle! ") + 1
    body = forms(text[at:])
    bundle, rest = body[0], body[1:]
    by_owner, loose = {}, []
    for f in rest:
        o = owner(f)
        if o:
            by_owner.setdefault(o, []).append(f)
        else:
            loose.append(f)
    seen, todo = set(), {t for t in TOKEN.findall(Path(emitted).read_text())}
    while todo:
        t = todo.pop()
        if t in seen:
            continue
        seen.add(t)
        for f in by_owner.get(t, []):
            todo.update(TOKEN.findall(f))
    keep = [f for f in rest if owner(f) in seen]
    out.write_text(bundle + "\n" + "\n".join(keep) + "\n")
    print(f"forms {len(rest)} owners {len(by_owner)} loose {len(loose)} reached {len(seen & set(by_owner))} "
          f"kept {len(keep)} bytes {sum(map(len, keep))}")
    for f in loose:
        print("LOOSE", f[:160])


if __name__ == "__main__":
    main()
