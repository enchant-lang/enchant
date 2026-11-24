#!/usr/bin/env python3
"""Card N0: the native front end's sources as image units, not an eval file.

N2b evaluated host/record.bl, host/aot.bl (hooked) and front-end/stage.bl on
the native image at run time (front-end/run.sh). N0 compiles them into the
image instead: this writes them as three namespaces that
`qualify.bl candidate --additions` appends to the bundle, so the native
compiler emits them into the image's prelude and Chez compiles them with it.

  compose.py SDK_PRIV FRONT_END_DIR ROOT

ROOT becomes a candidate source root:
  ROOT/priv      -> SDK_PRIV (the boot and library units, as the SDK has them)
  ROOT/research  -> this tree's research/ (the native compiler's own units)
  ROOT/n0/hook.bl     native-front.hook, unchanged
  ROOT/n0/record.bl   host.record; self-mod answers its BEAM module
  ROOT/n0/aot.bl      host.aot: aot.bl with compile_descriptor hooked, the
                      definitions stage.bl replaces removed, then loader-decls,
                      stage.bl and n0/driver.bl (which replaces two of stage's)
  ROOT/n0/additions.edn   lower-core and lower (the SDK's priv/boot; the
                          image does not carry them), then the three above

An evaluated file can define a name twice and the later one wins; a compiled
unit gets each name once, so every replaced definition is cut from its
original text by name.
"""
import os, re, subprocess, sys

def forms(text):
    """[(name, start, end)] of top-level (defn NAME ...) forms, by paren depth."""
    out, i, n = [], 0, len(text)
    head = re.compile(r"^\(defn-? (\S+)", re.M)
    while i < n:
        m = head.search(text, i)
        if not m: break
        depth, j, instr = 0, m.start(), False
        while j < n:
            c = text[j]
            if instr:
                if c == "\\": j += 1
                elif c == '"': instr = False
            elif c == '"': instr = True
            elif c == "\\": j += 1          # character literal \( \) \"
            elif c == ";":
                while j < n and text[j] != "\n": j += 1
            elif c in "([{": depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0: break
            j += 1
        out.append((m.group(1), m.start(), j + 1))
        i = j + 1
    return out

def names(text): return {name for name, _, _ in forms(text)}

def without(text, drop, label):
    """text with every top-level defn named in `drop` removed; each must occur once."""
    spans = [(s, e, name) for name, s, e in forms(text) if name in drop]
    seen = [name for _, _, name in spans]
    missing = sorted(set(drop) - set(seen))
    twice = sorted({x for x in seen if seen.count(x) > 1})
    if twice: sys.exit("compose: %s defines %s more than once" % (label, " ".join(twice)))
    out, at = [], 0
    for s, e, name in sorted(spans):
        out.append(text[at:s]); out.append(";; n0: %s replaced below\n" % name); at = e
    out.append(text[at:])
    return "".join(out), missing

def main():
    priv, fe, root = sys.argv[1], sys.argv[2], sys.argv[3]
    n0 = os.path.join(root, "n0")
    os.makedirs(n0, exist_ok=True)
    for link, target in (("priv", priv), ("research", os.path.abspath(os.path.join(fe, "../.."))) ):
        path = os.path.join(root, link)
        if not os.path.islink(path): os.symlink(target, path)
    research = os.path.join(root, "research")
    if not os.path.isdir(os.path.join(research, "native-seed/src/native")):
        sys.exit("compose: research link does not hold native-seed/src/native")
    read = lambda p: open(p).read()
    stage, driver = read(os.path.join(fe, "stage.bl")), read(os.path.join(fe, "n0/driver.bl"))
    # aot.bl, hooked exactly as front-end/run.sh does
    aot = read(os.path.join(priv, "host/aot.bl"))
    hooked = aot.replace("BeamLisp.Emit/compile_descriptor", "native-front.hook/compile-descriptor")
    # A compiled unit's global references must stay inside its require
    # closure; the evaluated copy reached these namespaces by load order.
    if hooked.count("\n(ns host.aot)\n") != 1: sys.exit("compose: aot.bl's ns form is not (ns host.aot)")
    hooked = hooked.replace("\n(ns host.aot)\n",
        "\n(ns host.aot (:require [lower :as lower] [native-front.hook :as native-front.hook] [host.record :as host.record]))\n"
        # The image's core has no compiled or seed `vector`; an evaluated
        # call found it at run time (n0/remotes.bl lists absent globals).
        ";; n0: core/vector for front-end/stage.bl and n0/driver.bl\n(defn- vector [& xs] (vec xs))\n")
    sites = aot.count("BeamLisp.Emit/compile_descriptor")
    replaced = names(stage) | names(driver)
    hooked, _ = without(hooked, replaced & names(hooked), "aot.bl")
    stage, _ = without(stage, names(driver) & names(stage), "stage.bl")
    decls = os.path.join(n0, "loader-decls.bl")
    subprocess.run([sys.executable, "-I", os.path.join(fe, "loader-decls.py"), os.path.join(priv, "host/loader.bl"), decls], check=True)
    open(os.path.join(n0, "aot.bl"), "w").write(
        hooked + "\n;; ── n0: loader declarations (front-end/loader-decls.py)\n" + read(decls)
        + "\n;; ── n0: front-end/stage.bl\n" + stage + "\n;; ── n0: front-end/n0/driver.bl\n" + driver)
    os.remove(decls)
    record = read(os.path.join(priv, "host/record.bl"))
    record, missing = without(record, {"self-mod"}, "record.bl")
    if missing: sys.exit("compose: record.bl has no self-mod")
    # The native linker answers a fun-literal self reference only for the
    # image's own modules; the BEAM names this source BeamLisp.Record.
    open(os.path.join(n0, "record.bl"), "w").write(record + "\n(defn- self-mod [] :Elixir.BeamLisp.Record)\n")
    open(os.path.join(n0, "hook.bl"), "w").write(read(os.path.join(fe, "hook.bl")))
    open(os.path.join(n0, "additions.edn"), "w").write(
        '[{:ns "lower-core" :path "priv/boot/lower-core.bl"}\n {:ns "lower" :path "priv/boot/lower.bl"}\n {:ns "native-front.hook" :path "n0/hook.bl"}\n {:ns "host.record" :path "n0/record.bl"}\n {:ns "host.aot" :path "n0/aot.bl"}]\n')
    print("compose: hooked sites %d, aot.bl definitions replaced %d, stage.bl replaced %d, aot unit %d bytes"
          % (sites, len(replaced & names(aot)), len(names(driver) & names(read(os.path.join(fe, "stage.bl")))), os.path.getsize(os.path.join(n0, "aot.bl"))))

main()
