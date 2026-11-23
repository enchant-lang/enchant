#!/usr/bin/env python3
"""Card N2b: extract priv/host/loader.bl's source-declaration scan and source reader for the
native front end. The pinned host Loader is not in the native image; these
functions are pure reader-data walks. Each is renamed nfl-NAME and evaluated
in host.aot (front-end/stage.bl routes BeamLisp.Loader/source_decls* here).

  loader-decls.py LOADER.bl OUT.bl
"""
import re, sys

NAMES = ["read_forms", "form-unmeta", "form-head-args", "form-name", "private-name?",
         "decl-line", "protocol-decl-lines", "class-decl-lines", "native-decl-lines",
         "source_decls_from",
         # read_source: literate .bl.md / .bl.org documents load their code cells
         "read_source", "doc_content", "strip_shebang", "doc_source", "collect_doc_cells",
         "take_until", "plain-ext-list", "list-member?",
         # declared_ns: the byte-level ns-head scanner
         "declared_ns", "skip_leading", "drop-to-newline", "ws?", "token-end?", "take_token",
         "split_token", "skip_metadata", "skip_one_form", "skip_nested", "drop_char"]

def forms(text):
    """Top-level (defn ...) forms with their names, by paren depth."""
    out, i, n = [], 0, len(text)
    while i < n:
        m = re.compile(r"^\(defn-? (\S+)", re.M).search(text, i)
        if not m: break
        start, depth, j, instr = m.start(), 0, m.start(), False
        while j < n:
            c = text[j]
            if instr:
                if c == "\\": j += 1
                elif c == '"': instr = False
            elif c == '"': instr = True
            elif c == ";":
                while j < n and text[j] != "\n": j += 1
            elif c in "([{": depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0: break
            j += 1
        out.append((m.group(1), text[start:j + 1]))
        i = j + 1
    return out

text = open(sys.argv[1]).read()
found = {name: body for name, body in forms(text) if name in NAMES}
missing = [n for n in NAMES if n not in found]
if missing: sys.exit("loader-decls: missing " + " ".join(missing))
pattern = re.compile(r"(?<![\w!?*<>=/.-])(" + "|".join(re.escape(n) for n in NAMES) + r")(?![\w!?*<>=/-])")
body = "\n\n".join(pattern.sub(lambda m: "nfl-" + m.group(1), found[n]) for n in NAMES)
# The SDK constructor reader cache is host.aot's own constructor_read_forms.
body = body.replace("BeamLisp.AOT/constructor_read_forms", "constructor_read_forms")
open(sys.argv[2], "w").write(";; Extracted from " + sys.argv[1] + " by front-end/loader-decls.py\n" + body + "\n")
print("loader-decls: %d functions" % len(found))
