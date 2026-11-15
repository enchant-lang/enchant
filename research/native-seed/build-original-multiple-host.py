#!/usr/bin/env python3
"""Experiment: exact original GSC C, whole host O1 with multiple C functions.

No Scheme-to-C translation runs. Reuse the parent's original host Scheme/C
bytes, optimizer choices, module name and translation receipt. Only the host
C object changes O0/SINGLE_HOST to O1/MULTIPLE_HOSTS; all public/TCO flags and
all17 tail objects stay exact. Runtime/Source/actor/tail/GC parity is unqualified.
All tool children retain120 seconds; actual self-emission keeps240 separately.
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
AUDITED_GAMBIT_HEADER_SHA256 = "53c1968a28362bd6a8714c6a0e2784ce6fe80c6a10babcd14fc927b94d8926bc"
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
    parser.add_argument("--admit-only", action="store_true",
                        help="admit retained parent Scheme/C/translation proofs without compiling")
    args = parser.parse_args()
    root, out = args.root.resolve(), (args.root / args.out).resolve()
    base, here = root / "research/native-seed", Path(__file__).resolve()
    helper = here.with_name("check-original-multiple-host-self-emission.py")
    if not helper.is_file():
        helper = base / "check-original-multiple-host-self-emission.py"
    spec = importlib.util.spec_from_file_location("bl_owned_native_process", helper)
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    digest, save, require, OwnedTree = common.digest, common.save, common.require, common.OwnedTree
    cache = (root / args.cache).resolve() if args.cache else out / "original-multiple-host-cache"
    cache.mkdir(parents=True, exist_ok=True)
    progress = out / "original-multiple-host-build.json"
    inputs, runs, parts, tails = {}, [], [], []
    report = {"schema": "bl.native.original-multiple-host-build", "version": 1, "status": "running",
              "executed": False, "source_interpreter": False, "anf_interpreter": False,
              "fixpoint_qualified": False, "compile_deadline_seconds": DEADLINE,
              "intact_host_unit": True, "gambit_inlining_limit": "parent-original",
              "original_gsc_translation_reused": True, "scheme_optimizer_changed": False,
              "clang_host_optimization": 1, "c_host_layout": "multiple",
              "parent_tail_c_host_layout": "single", "experimental": True,
              "runtime_qualified": False, "inputs": inputs, "runs": runs,
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
        print("NATIVE_ORIGINAL_MULTIPLE_HOST_JOB " + label + " PASS", flush=True)

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
        require(digest(gambit / "gambit/include/gambit.h") == AUDITED_GAMBIT_HEADER_SHA256,
                "multiple-host interoperability has only been audited for the exact pinned public header")
        gsc_original = original["scheme_compiler_flags"]
        require(bool(original.get("standard_bindings")) == bool(gsc_original), "original primitive declaration flag differs")
        require(gsc_original in ([], ["-prelude", STANDARD_PRELUDE]), "unreviewed original Scheme compiler flags")
        gsc_flags = gsc_original
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
            require(row["c_flags"].count("-D___SINGLE_HOST") == 1
                    and "-D___MULTIPLE_HOSTS" not in row["c_flags"],
                    "original tail C layout is not the admitted single-host layout")
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
        # Reuse the ORIGINAL parent's exact GSC output and module name.
        # This isolates only C optimization/grouping: no Scheme-to-C job runs.
        original_host = original_units[0]
        cfile = path_for(original_host["c"])
        scheme = cfile.with_suffix(".scm")
        bind(cfile, original_host["c_sha256"])
        bind(scheme, original_host["sha256"])
        require(scheme.read_bytes() == whole_host, "original host translation changed its exact Source")
        translation_path = cfile.parent / "scheme-c.json"
        bind(translation_path)
        translation = json.loads(translation_path.read_text())
        original_request = translation["request"]
        require(original_request["source_sha256"] == original_host["sha256"]
                and original_request["ordinal"] == 0
                and original_request["tools"]["compiler_recipe"] == build["compiler_recipe"]["sha256"]
                and original_request["tools"]["flags"] == c_base
                and original_request["tools"]["scheme_compiler_flags"] == gsc_original
                and original_request["tools"]["link_flags"] == original["native_link_flags"]
                and original_request["tools"]["toolchain"] == tools
                and translation["outputs"] == {cfile.name: original_host["c_sha256"]},
                "original host translation receipt changed its compiler/Source/flags/C identity")
        for name, expected in original_request["tools"]["tools"].items():
            bind(path_for(name), expected)
        origin = {"parent_build_sha256": digest(build_path), "original_ordinal": 0,
            "source_sha256": original_host["sha256"], "c_sha256": original_host["c_sha256"],
            "translation_receipt_sha256": digest(translation_path)}
        require(c_base.count("-D___SINGLE_HOST") == 1 and "-D___MULTIPLE_HOSTS" not in c_base
                and "-D___TRUST_C_TCO" in c_base,
                "experimental layout requires the exact single-host/TCO parent flags")
        flags = ["-O1", *("-D___MULTIPLE_HOSTS" if flag == "-D___SINGLE_HOST" else flag
                           for flag in c_base[1:])]
        object_request = {"original_translation": origin, "tools": tool_identity, "c_flags": flags}
        directory = cache / "host-objects" / key(object_request)
        directory.mkdir(parents=True, exist_ok=True)
        obj = directory / (cfile.stem + ".O1-multiple.o")
        report["host_translation"] = {"source": {"path": str(scheme), "sha256": digest(scheme)},
            "c": {"path": str(cfile), "sha256": digest(cfile), "bytes": cfile.stat().st_size},
            "scheme_compiler_flags": gsc_flags, "original_translation": origin, "reused_original": True}
        checkpoint()
        print("NATIVE_ORIGINAL_MULTIPLE_HOST_C_BYTES " + str(cfile.stat().st_size), flush=True)
        if args.admit_only:
            unchanged()
            report["status"] = "admitted-translation-not-built"
            result = 0
            return result
        object_receipt = directory / "object-O1-multiple.json"
        reused_o = cached("original-whole-host-object", [clang, *flags, "-c", cfile, "-o", obj], directory,
                         object_receipt, object_request, [obj])
        parts.append({"ordinal": 0, "role": "whole-host",
            "source": {"path": str(frozen_path), "sha256": digest(frozen_path)},
            "segment": {"path": str(scheme), "sha256": digest(scheme)}, "bytes": len(whole_host),
            "indivisible_ffi_host": True, "original_translation": origin,
            "c": {"path": str(cfile), "sha256": digest(cfile)},
            "object": {"path": str(obj), "sha256": digest(obj)},
            "c_flags": flags, "reused_c": True, "reused_object": reused_o,
            "translation_receipt": {"path": str(translation_path), "sha256": digest(translation_path)},
            "object_receipt": {"path": str(object_receipt), "sha256": digest(object_receipt)}})
        c_units, objects = [cfile], [obj]
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
        image = image_directory / "stage1-original-multiple-host"
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
        receipt = image_directory / "original-multiple-host-build.json"
        checkpoint()
        save(receipt, report)
        print("NATIVE_ORIGINAL_MULTIPLE_HOST_BUILT " + str(receipt), flush=True)
        result = 0
    except BaseException as error:
        report.update({"status": "fail", "error": str(error), "error_type": type(error).__name__})
        print("NATIVE_ORIGINAL_MULTIPLE_HOST_FAIL " + str(error), file=sys.stderr, flush=True)
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        checkpoint()
        signal.signal(signal.SIGTERM, previous_term)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
