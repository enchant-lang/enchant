"""Reconstruct checkpoint 16 from retained successful logs, pins and artifacts."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / "evidence/refutation-kernel"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


log = (E / "checks.txt").read_text()
counts = dict((name, int(n)) for name, n in re.findall(r"✓\s+(formal\.[\w-]+)\s+(\d+) passed", log))
require(len(counts) == 29 and "29 file(s) passed, 0 failed, 0 incoherent" in log, "successful full BL check required")
require(counts["formal.refutation-test"] == 108, "focused exporter regression count")
tested = "29446d2d5"
sources = {}
for path in sorted([*P.glob("src/**/*.bl"), *P.glob("test/*.bl")]):
    rel = path.relative_to(R).as_posix()
    prior = subprocess.run(["git", "show", tested + ":" + rel], cwd=R, check=True, stdout=subprocess.PIPE).stdout
    require(prior == path.read_bytes(), "BL source changed since full check: " + rel)
    sources[path.relative_to(P).as_posix()] = sha(path)

bridge_commit = "5901db07e"
bridge_sources = {}
for name in ["refutation_kernel.py", "refutation_kernel_test.py", "check-refutation"]:
    path = P / name
    prior = subprocess.run(["git", "show", bridge_commit + ":" + path.relative_to(R).as_posix()], cwd=R, check=True, stdout=subprocess.PIPE).stdout
    require(prior == path.read_bytes(), "bridge changed since checked commit: " + name)
    bridge_sources[name] = sha(path)
require("Ran 4 tests" in (E / "bridge-check.txt").read_text() and "\nOK\n" in (E / "bridge-check.txt").read_text(), "bridge check log")

audits = {}
for line in (E / "model-check-3.txt").read_text().splitlines():
    match = re.fullmatch(r"'([^']+)' depends on axioms: \[(.*)\]", line)
    require(match is not None, "unexpected model audit output")
    audits[match[1]] = match[2].split(", ") if match[2] else []
require(len(audits) == 17, "seventeen normalized-kernel theorem audits")
require(Counter(tuple(v) for v in audits.values()) == Counter({("propext",): 4, ("propext", "Quot.sound"): 13}), "kernel theorem dependencies")
pin = read(P / "metatheory/refutation-pin.json")
for key in ["source", "compiled"]:
    require(sha(P / pin[key]["path"]) == pin[key]["sha256"], "normalized kernel pin " + key)
tool = read(P / "metatheory/tool-pin.json")
require(sha(Path(tool["path"]) / "bin/lean") == tool["binary_sha256"], "Lean executable pin")

accepted = read(E / "execution/accepted.json")
require(len(accepted) == 11 and len({row["id"] for row in accepted}) == 11, "eleven real checked packets")
for row in accepted:
    target = E / "execution" / row["id"]
    packet = read(E / "examples" / (row["id"] + ".json"))
    require(row["status"] == "checked-normalized-refutation" and row["packet"] == packet["identity"], "accepted packet identity")
    require(row["statement"] == packet["statement"] and row["question"] == packet["question"], "accepted original identity labels")
    require(sha(target / "Check.lean") == row["proof_source_sha256"] and sha(target / "Check.olean") == row["proof_olean_sha256"], "checked packet artifacts")
    require(row["axioms"] == {"packetAccepted": ["propext"], "packetUnsatisfiable": ["propext", "Quot.sound"]}, "applied theorem audits")
    require("sorryAx" not in (target / "lean.txt").read_text(), "no admitted accepted proof")
rejected = read(E / "execution/rejected.json")
require(len(rejected) == 5 and all(row["status"] == "rejected-by-lean" for row in rejected), "five false refutations rejected in Lean")
for row in rejected:
    target = E / "execution/rejected" / row["id"]
    require((target / "lean.txt").is_file() and not (target / "Check.olean").exists(), "rejected proof cannot carry compiled success")
fresh = read(E / "fresh/refutation-fresh.json")
require(len(fresh["rows"]) == 11 and fresh["calibration-native-sessions"] > 0 and fresh["reconstruction-native-sessions"] == 0, "positively calibrated fresh recheck")
require(all(row["status"] == "checked-data-connection" and row["kernel-execution"] == "not-run" for row in fresh["rows"]), "fresh reconstruction scope")

corpora = []
for name in ["advanced", "features", "native"]:
    now, before = read(E / "corpora" / (name + ".json")), read(P / "evidence/connections/corpora" / (name + ".json"))
    signatures = lambda data: {row["id"]: {engine: row[engine]["verdict"] for engine in ["z3", "oxiz"]} for row in data["cases"]}
    require(signatures(now) == signatures(before), "backend verdict drift: " + name)
    require(now["disagreements"] == [] and now["invalid-models"] == [], "backend disagreement or invalid model")
    corpora.append({"corpus": name, "questions": len(now["cases"]), "per_case_verdicts_unchanged": True,
                    "disagreements": 0, "invalid_models": 0, "summary": now["summary"]})
require(sum(row["questions"] for row in corpora) == 187, "full comparison corpus")
artifacts = {p.relative_to(P).as_posix(): sha(p) for p in sorted(E.rglob("*"))
             if p.is_file() and p.name not in {"qualification.json", "dossier-qualification.json"} and "browser-audit" not in p.parts}
result = {
    "schema": "enchant.formal.normalized-refutation-qualification.v1", "checkpoint": 16,
    "recorded_utc": datetime.now(timezone.utc).isoformat(), "sdk_pin": read(P / "sdk-pin.json"),
    "worker_sha256": sha(R / "research/oxiz-prototype/worker/target/release/formal-worker"),
    "z3_library_sha256": sha(Path(read(P / "sdk-pin.json")["sdk"]) / "image/priv/z3/bin/libz3.so"),
    "checks": {"tested_code_commit": tested, "files": counts, "total_assertions": sum(counts.values()),
               "failures": 0, "library_and_test_files_unchanged_since_tested_commit": True, "source_sha256": sources},
    "normalized_kernel": {"pin": pin, "tool": tool, "theorem_audits": audits, "accepted_real_packets": 11,
                          "rejected_false_refutations_in_lean": 5, "axioms_of_computed_acceptance": ["propext"],
                          "axioms_of_soundness": ["propext", "Quot.sound"], "bridge_test_commit": bridge_commit,
                          "bridge_source_sha256": bridge_sources, "scope": "executable-normalized-checker-soundness"},
    "prior_core_model_theorems": 63, "fresh_reconstruction": fresh,
    "native_comparison": {"questions": 187, "baseline": "evidence/connections/corpora", "corpora": corpora},
    "remaining_trust": ["original typed-term normalization into normalized formulas/atoms",
                        "BL certificate checker correspondence", "packet encoding and source data bridge",
                        "Core/controller/state/trace interpretation into term questions", "Source extraction and unit/ANF/Core connections",
                        "BL compiler, exact primitives and BEAM runtime", "local observation and artifact custody"],
    "retained_failures": ["model-initial-check.txt", "model-check-2.txt", "initial-export-check.txt", "weighted-initial-audit/"],
    "production_default_changed": False, "compiler_proof_authority": False, "artifact_sha256": artifacts,
}
(E / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"assertions": sum(counts.values()), "files": len(counts), "normalized_kernel_theorems": 17,
                  "accepted_real_packets": 11, "rejected_false_refutations": 5, "unchanged_native_questions": 187}))
