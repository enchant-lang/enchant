#!/usr/bin/env python3
"""Count emitter work on a private Source overlay, with the qualified BEAM SDK."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from probe import ATTRIB, NATIVE, ROOT, SIZES, fixtures, sha

SCHEME = NATIVE / "src/native/scheme.bl"
PIN = ATTRIB / "raw/checkout-sdk-qualification.json"
REPLACEMENTS = {
    "(ns native.scheme ": "(ns native.speed-counted ",
    '(defn- glue [& parts] (Enum/join parts ""))': '''(defn- record! [metric work]
 (let [key :native-speed/emission-counts
       counts (erlang/get key)]
  (erlang/put key (assoc counts metric (+ (get counts metric 0) work)))))
(defn- glue [& parts]
 (record! "glue_calls" 1)
 (record! "glue_input_bytes"
          (Enum/reduce parts 0 (fn [part total]
            (+ total (erlang/byte_size (if (erlang/is_binary part) part (String.Chars/to_string part)))))))
 (Enum/join parts ""))''',
    "[value tail active state]\n (cond": '[value tail active state]\n (record! "loop_walk_visits" 1)\n (cond',
    "(defn- body-calls? [n ctx]\n (cond": '(defn- body-calls? [n ctx]\n (record! "body_call_visits" 1)\n (cond',
    "(defn- integer-operand? [n options]\n (or": '(defn- integer-operand? [n options]\n (record! "integer_queries" 1)\n (or',
    "(defn- integer-binding [options name value]\n (let": '(defn- integer-binding [options name value]\n (record! "integer_bindings" 1)\n (let',
    "(defn- fixed-function [formals body fallback site tick?]\n": (
        '(defn- fixed-function [formals body fallback site tick?]\n'
        ' (record! "fixed_function_body_bytes" (erlang/byte_size body))\n'
    ),
}


def instrument(source):
    for old, new in REPLACEMENTS.items():
        if source.count(old) != 1:
            raise ValueError(f"Expected one instrumentation site: {old}")
        source = source.replace(old, new)
    return source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, choices=SIZES,
                        help="select one pair of generated fixtures")
    args = parser.parse_args()
    pin = json.loads(PIN.read_text())
    sdk = Path(pin["sdk"])
    descriptor_sha = sha(sdk / "artifact.json")
    expected_sha = pin.get("descriptor_sha256") or pin.get("sdk_descriptor_sha256")
    if expected_sha is None or descriptor_sha != expected_sha:
        raise SystemExit("SDK descriptor does not match the qualification receipt.")
    with tempfile.TemporaryDirectory(prefix="native-emission-count-") as temporary:
        work = Path(temporary)
        module = work / "native/speed-counted.bl"
        module.parent.mkdir()
        module.write_text(instrument(SCHEME.read_text()), encoding="utf-8")
        runtime = work / "runtime"
        runtime.mkdir(mode=0o700)
        selected = [(family, size, path) for family, size, path in fixtures(work)
                    if args.size is None or (family != "reader" and size == args.size)]
        result = subprocess.run(
            ["systemd-run", "--user", "--quiet", "--collect", "--wait", "--pipe",
             "--property=MemoryMax=2G", "--property=MemorySwapMax=0",
             "--property=RuntimeMaxSec=120", "--property=KillMode=control-group",
             "--working-directory=" + str(ROOT),
             "--setenv=XDG_RUNTIME_DIR=" + str(runtime),
             str(sdk / "bin/bl"), "--cold", "-p", str(work), "-p", str(NATIVE / "src"),
             "run", str(ATTRIB / "emission-count.bl"), "--",
             *(str(path) for _, _, path in selected)],
            cwd=ROOT, env=dict(os.environ, LC_ALL="C"), capture_output=True, text=True,
        )
        if result.returncode:
            raise SystemExit(result.stdout + result.stderr)
        counts = [json.loads(line[len("EMISSION_COUNT "):])
                  for line in result.stdout.splitlines() if line.startswith("EMISSION_COUNT ")]
        rows = [dict(count, family=family, size=size, source_sha256=sha(path))
                for (family, size, path), count in zip(selected, counts, strict=True)]
        print(json.dumps({
            "schema": "bl.native.emission-count",
            "version": 1,
            "sdk_descriptor_sha256": descriptor_sha,
            "emitter_sha256": sha(SCHEME),
            "overlay_sha256": sha(module),
            "scope": "Source-level counts on BEAM. Both emitters received the same ANF and produced identical text.",
            "fixtures": rows,
        }, indent=2))


if __name__ == "__main__":
    main()
