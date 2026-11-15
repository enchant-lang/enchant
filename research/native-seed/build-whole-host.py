#!/usr/bin/env python3
"""Build one intact host with Gambit inlining-limit0 and Clang O1.

This creates a derived ELF and executes no BL/SDK/Source bodies. The complete
frozen host, including text FFI, remains one exact-byte Scheme unit. Only its
Scheme compiler declaration and C optimization level change. All original
compiler tail objects retain their filenames, ordinals, source hashes and flags.
Each tool child keeps its120-second deadline; native self-emission is separate.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

DEADLINE = 120
PARTS = (("seed", "host.scm"), ("values", "host/host-values.scm"),
         ("leaves", "host/host-leaves.scm"), ("lazy", "host/host-lazy.scm"),
         ("extra", "host/host-extra.scm"), ("compiler", "host/host-compiler.scm"),
         ("text-ffi", "host/native-text.scm"))
STANDARD_PRELUDE = "(declare (standard-bindings) (extended-bindings))"


def key(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("research/native-seed/out/compiler-closure"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--translate-only", action="store_true",
                        help="checkpoint whole-host Scheme-to-C before the bounded O1 object job")
    args = parser.parse_args()
    root, out = args.root.resolve(), (args.root / args.out).resolve()
    base, here = root / "research/native-seed", Path(__file__).resolve()
    helper = here.with_name("check-whole-host-self-emission.py")
    if not helper.is_file():
        helper = base / "check-whole-host-self-emission.py"
    spec = importlib.util.spec_from_file_location("bl_owned_native_process", helper)
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    digest, save, require, OwnedTree = common.digest, common.save, common.require, common.OwnedTree
    cache = (root / args.cache).resolve() if args.cache else out / "whole-host-cache"
    cache.mkdir(parents=True, exist_ok=True)
    progress = out / "whole-host-build.json"
    inputs, runs, parts, tails = {}, [], [], []
    report = {"schema": "bl.native.whole-host-build", "version": 1, "status": "running",
              "executed": False, "source_interpreter": False, "anf_interpreter": False,
              "fixpoint_qualified": False, "compile_deadline_seconds": DEADLINE,
              "intact_host_unit": True, "gambit_inlining_limit": 0,
              "clang_host_optimization": 1, "inputs": inputs, "runs": runs,
              "host_units": parts, "reused_tails": tails}
    started = time.monotonic()
    def terminated(signum, frame):
        raise InterruptedError("whole-host builder received signal " + str(signum))
    previous_term = signal.signal(signal.SIGTERM, terminated)

    def path_for(name):
        p = Path(name)
        return p.resolve() if p.is_absolute() else (root / p).resolve()

    def bind(path, expected=None):
        path = path.resolve()
        actual = digest(path)
        require(expected is None or actual == expected, "whole-host input changed: " + str(path))
        require(str(path) not in inputs or inputs[str(path)] == actual, "whole-host input changed during admission: " + str(path))
        inputs[str(path)] = actual
        return actual

    def unchanged():
        for name, expected in inputs.items():
            require(Path(name).is_file() and digest(Path(name)) == expected, "whole-host input changed: " + name)

    def checkpoint():
        report["seconds"] = round(time.monotonic() - started, 3)
        save(progress, report)

    def run(label, argv, directory):
        argv = [str(x) for x in argv]
        log = directory / (label + ".log")
        began, process, tree = time.monotonic(), None, None
        row = {"label": label, "argv": argv, "log": str(log), "timeout": False}
        runs.append(row)
        try:
            with log.open("w") as stream:
                process = subprocess.Popen(argv, cwd=directory, stdin=subprocess.DEVNULL,
                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                tree = OwnedTree(process)
                while process.poll() is None:
                    tree.discover()
                    remaining = DEADLINE - (time.monotonic() - began)
                    if remaining <= 0:
                        row["timeout"] = True
                        raise subprocess.TimeoutExpired(argv, DEADLINE)
                    try:
                        process.wait(timeout=min(1, remaining))
                    except subprocess.TimeoutExpired:
                        pass
            row["exit"] = process.returncode
            require(process.returncode == 0, label + ": child exit " + str(process.returncode))
        finally:
            if tree:
                row["cleanup"] = tree.cleanup()
                require(not row["cleanup"]["errors"], label + ": child cleanup failed")
            row["seconds"] = round(time.monotonic() - began, 3)
            if log.is_file():
                row["log_sha256"] = digest(log)
                row["output_tail"] = log.read_text(errors="replace")[-8000:]
            checkpoint()
        print("NATIVE_WHOLE_HOST_JOB " + label + " PASS", flush=True)

    def cached(label, argv, directory, receipt, request, outputs):
        if receipt.is_file():
            previous = json.loads(receipt.read_text())
            if (previous.get("request") == request and all(
                    p.is_file() and digest(p) == previous.get("outputs", {}).get(str(p)) for p in outputs)):
                return True
        receipt.unlink(missing_ok=True)
        run(label, argv, directory)
        save(receipt, {"request": request, "outputs": {str(p): digest(p) for p in outputs}})
        return False

    result = 1
    try:
        bind(here)
        bind(helper)
        build_path = out / "native-build.json"
        bind(build_path)
        build = json.loads(build_path.read_text())
        require(build.get("schema") == "bl.native.bounded-build" and build.get("version") == 1,
                "unsupported original native build receipt")
        require(build.get("status") in ("stage1-compiled-not-qualified", "stage1-actors-compiled-not-qualified", "failed"),
                "original native build is not complete")
        require(build.get("compile_deadline_seconds") == DEADLINE, "original compiler deadline differs")
        stages = [x for x in build["builds"] if x["stage"] == "stage1"]
        require(len(stages) == 1, "original build lacks exactly one stage1")
        original = stages[0]
        for name, expected in build["inputs"].items():
            bind(path_for(name), expected)
        bind(out / "stage1", original["executable_sha256"])
        bind(out / "stage1.scm", original["source_sha256"])
        bind(base / "fixpoint.py", build["driver_sha256"])
        bind(base / "sdk-pin.json")
        bind(base / "toolchain-pin.json")
        pin = json.loads((base / "sdk-pin.json").read_text())
        descriptor = Path(pin["sdk"]) / "artifact.json"
        bind(descriptor, pin["descriptor_sha256"])
        require(json.loads(descriptor.read_text())["source"] == pin["source"], "SDK Source pin differs")
        tools = json.loads((base / "toolchain-pin.json").read_text())
        gambit = Path(tools["gambit"])
        gsc, clang = gambit / "bin/gsc", Path(tools["clang"]) / "bin/clang"
        for path in (gsc, clang, gambit / "gambit/include/gambit.h", gambit / "gambit/lib/libgambit.so"):
            bind(path)
        gsc_original = original["scheme_compiler_flags"]
        require(bool(original.get("standard_bindings")) == bool(gsc_original), "original primitive declaration flag differs")
        require(gsc_original in ([], ["-prelude", STANDARD_PRELUDE]), "unreviewed original Scheme compiler flags")
        declarations = "(declare (separate) (safe) (interrupts-enabled) (inlining-limit 0)"
        if original.get("standard_bindings"):
            declarations += " (standard-bindings) (extended-bindings)"
        gsc_flags = ["-prelude", declarations + ")"]
        original_units = original["units"]
        require(original_units and original_units[0].get("indivisible_ffi_host") is True,
                "original ordinal0 is not the admitted whole host")
        c_base = original_units[0]["c_flags"]
        require(c_base[0] == "-O0", "whole-host optimization starts from the admitted O0 checkpoint")
        require(original["link_order"] == [x["c"] for x in original_units], "original tail link order differs")
        frozen_path = out / "host.scm"
        bind(frozen_path)
        frozen = frozen_path.read_bytes()
        raw_parts = []
        for role, name in PARTS:
            path = base / name
            bind(path)
            raw = path.read_bytes()
            if role != "text-ffi":
                require(not re.search(rb"\(\s*c-(?:declare|lambda|define|initialize|define-type)\b", raw),
                        "FFI crossed a Scheme-only host component: " + name)
            raw_parts.append(raw)
        require(b"(c-declare" in raw_parts[-1] and b"(c-lambda" in raw_parts[-1], "final host part lacks its intact text FFI")
        require(b"\n".join(raw_parts) == frozen, "host components do not concatenate to the exact frozen host")
        segments = [(common.HEADER if i == 0 else b"") + raw + b"\n" for i, raw in enumerate(raw_parts)]
        whole_host = common.HEADER + frozen + b"\n"
        require(b"".join(segments) == whole_host, "host partition changed a byte or initialization order")
        require(hashlib.sha256(whole_host).hexdigest() == original_units[0]["sha256"],
                "host parts do not match original compiled ordinal0 Source")
        require((out / "stage1.scm").read_bytes().startswith(whole_host), "original stage1 lacks this host prefix")
        report["parent_build"] = {"path": str(build_path), "sha256": digest(build_path)}
        report["original_source"] = {"path": str(out / "stage1.scm"), "sha256": original["source_sha256"]}
        report["original_image"] = {"path": str(out / "stage1"), "sha256": original["executable_sha256"]}
        report["frozen_host"] = {"path": str(frozen_path), "sha256": digest(frozen_path),
                                 "whole_unit_sha256": hashlib.sha256(whole_host).hexdigest()}
        report["exact_host_source"] = True
        report["scheme_compiler_flags"] = gsc_flags
        report["sdk_pin"] = pin
        relevant_env = {name: value for name, value in os.environ.items()
            if name.startswith(("NIX_", "GAMBIT", "LC_")) or name in (
                "HOME", "PATH", "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                "SDKROOT", "LD_LIBRARY_PATH", "LD_PRELOAD", "LANG", "SOURCE_DATE_EPOCH", "TZ")}
        tool_identity = {"driver_sha256": digest(here), "process_helper_sha256": digest(helper),
            "toolchain_sha256": digest(base / "toolchain-pin.json"), "gsc_sha256": digest(gsc),
            "clang_sha256": digest(clang), "gambit_header_sha256": digest(gambit / "gambit/include/gambit.h"),
            "gambit_runtime_sha256": digest(gambit / "gambit/lib/libgambit.so"),
            "compiler_environment_sha256": key(relevant_env), "gsc_flags": gsc_flags}
        report["tool_identity"] = tool_identity
        tail_c, tail_objects = [], []
        for ordinal, row in enumerate(original_units[1:], 1):
            require(row["ordinal"] == ordinal, "original tail ordinal changed")
            cfile, obj = path_for(row["c"]), path_for(row["object"])
            bind(cfile, row["c_sha256"])
            bind(obj, row["object_sha256"])
            bind(cfile.with_suffix(".scm"), row["sha256"])
            tails.append({"original_ordinal": ordinal, "source_sha256": row["sha256"],
                          "c": {"path": str(cfile), "sha256": row["c_sha256"]},
                          "object": {"path": str(obj), "sha256": row["object_sha256"]},
                          "c_flags": row["c_flags"], "scheme_compiler_flags": row["scheme_compiler_flags"]})
            tail_c.append(cfile)
            tail_objects.append(obj)
        c_units, objects = [], []
        for ordinal, (role, name, source) in enumerate((("whole-host", frozen_path, whole_host),)):
            request = {"role": role, "source_sha256": hashlib.sha256(source).hexdigest(), "tools": tool_identity}
            directory = cache / "whole-units" / key(request)
            directory.mkdir(parents=True, exist_ok=True)
            stem = "hostwhole_" + key(request)[:16]
            scheme, cfile = [directory / (stem + suffix) for suffix in (".scm", ".c")]
            variant = "O1"
            obj = directory / (stem + "." + variant + ".o")
            if not scheme.is_file() or scheme.read_bytes() != source:
                scheme.write_bytes(source)
            flags = ["-O1", *c_base[1:]]
            reused_c = cached(role + "-scheme-to-c", [gsc, "-c", *gsc_flags, "-o", cfile, scheme],
                              directory, directory / "scheme-c.json", request, [cfile])
            report["host_translation"] = {"source": {"path": str(scheme), "sha256": digest(scheme)},
                "c": {"path": str(cfile), "sha256": digest(cfile), "bytes": cfile.stat().st_size},
                "scheme_compiler_flags": gsc_flags, "reused_c": reused_c}
            checkpoint()
            print("NATIVE_WHOLE_HOST_C_BYTES " + str(cfile.stat().st_size), flush=True)
            if args.translate_only:
                unchanged()
                report["status"] = "translated-not-built"
                result = 0
                return result
            object_request = {"translation": request, "c_sha256": digest(cfile), "c_flags": flags}
            reused_o = cached(role + "-object", [clang, *flags, "-c", cfile, "-o", obj], directory,
                             directory / ("object-" + variant + ".json"), object_request, [obj])
            parts.append({"ordinal": ordinal, "role": role, "source": {"path": str(base / name), "sha256": digest(base / name)},
                "segment": {"path": str(scheme), "sha256": digest(scheme)}, "bytes": len(source), "indivisible_ffi_host": True,
                "c": {"path": str(cfile), "sha256": digest(cfile)}, "object": {"path": str(obj), "sha256": digest(obj)},
                "c_flags": flags, "reused_c": reused_c, "reused_object": reused_o,
                "translation_receipt": {"path": str(directory / "scheme-c.json"), "sha256": digest(directory / "scheme-c.json")},
                "object_receipt": {"path": str(directory / ("object-" + variant + ".json")), "sha256": digest(directory / ("object-" + variant + ".json"))}})
            c_units.append(cfile)
            objects.append(obj)
            checkpoint()
        c_units.extend(tail_c)
        objects.extend(tail_objects)
        link_request = {"tools": tool_identity, "ordered_c_units": [{"path": str(p), "sha256": digest(p)} for p in c_units]}
        directory = cache / "links" / key(link_request)
        directory.mkdir(parents=True, exist_ok=True)
        link_c, link_o = directory / "program_.c", directory / "program_.o"
        cached("whole-host-link-metadata", [gsc, "-link", "-o", link_c, *c_units], directory,
               directory / "link-c.json", link_request, [link_c])
        cached("whole-host-link-object", [clang, *c_base, "-c", link_c, "-o", link_o], directory,
               directory / "link-object.json", {"link": link_request, "c_sha256": digest(link_c), "c_flags": c_base}, [link_o])
        image_request = {"link": link_request, "link_object_sha256": digest(link_o),
                         "ordered_objects": [{"path": str(p), "sha256": digest(p)} for p in objects],
                         "link_flags": original["native_link_flags"]}
        image_directory = directory / "images" / key(image_request)
        image_directory.mkdir(parents=True, exist_ok=True)
        image = image_directory / "stage1-whole-host"
        cached("whole-host-native-link", [clang, *objects, link_o, *original["native_link_flags"], "-o", image],
               directory, image_directory / "native-link.json", image_request, [image])
        with image.open("rb") as stream:
            require(stream.read(4) == b"\x7fELF" and os.access(image, os.X_OK), "whole-host image is not an executable ELF")
        unchanged()
        report.update({"status": "built-not-executed", "image": {"path": str(image), "sha256": digest(image)},
            "link_order": [str(p) for p in c_units], "object_order": [str(p) for p in objects],
            "link_metadata": {"path": str(link_c), "sha256": digest(link_c)},
            "link_object": {"path": str(link_o), "sha256": digest(link_o)},
            "native_link_flags": original["native_link_flags"], "link_metadata_c_flags": c_base,
            "link_metadata_receipt": {"path": str(directory / "link-c.json"), "sha256": digest(directory / "link-c.json")},
            "link_object_receipt": {"path": str(directory / "link-object.json"), "sha256": digest(directory / "link-object.json")},
            "native_link_receipt": {"path": str(image_directory / "native-link.json"), "sha256": digest(image_directory / "native-link.json")}})
        receipt = image_directory / "whole-host-build.json"
        checkpoint()
        save(receipt, report)
        print("NATIVE_WHOLE_HOST_BUILT " + str(receipt), flush=True)
        result = 0
    except BaseException as error:
        report.update({"status": "fail", "error": str(error), "error_type": type(error).__name__})
        print("NATIVE_WHOLE_HOST_FAIL " + str(error), file=sys.stderr, flush=True)
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        checkpoint()
        signal.signal(signal.SIGTERM, previous_term)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
