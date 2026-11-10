"""Reconstruct checkpoint 17 from exact source snapshots and successful evidence."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / "evidence/term-refutation"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


snapshot = read(E / "check-source-pin.json")
for name, digest in snapshot["sha256"].items():
    path = P / name
    require(sha(path) == digest, "source changed since qualification run: " + name)
    recorded = subprocess.run(["git", "show", snapshot["code_commit"] + ":" + path.relative_to(R).as_posix()], cwd=R, check=True, stdout=subprocess.PIPE).stdout
    require(recorded == path.read_bytes(), "source snapshot differs from its commit: " + name)
log = (E / "checks.txt").read_text()
counts = dict((name, int(count)) for name, count in re.findall(r"✓\s+(formal\.[\w-]+)\s+(\d+) passed", log))
require(len(counts) == 30 and "30 file(s) passed, 0 failed, 0 incoherent" in log, "successful thirty-file integration run")
require(counts["formal.term-refutation-test"] == 54, "original term binding regression count")
bridge = (E / "bridge-check.txt").read_text()
require("Ran 4 tests" in bridge and "\nOK\n" in bridge, "successful real/adversarial term proof checks")
pin = read(P / "metatheory/terms-pin.json")
require(sha(P / "metatheory/refutation-pin.json") == pin["normalized_kernel_pin_sha256"], "normalized dependency pin")
for current in [pin, read(P / "metatheory/refutation-pin.json")]:
    for key in ["source", "compiled"]:
        require(sha(P / current[key]["path"]) == current[key]["sha256"], "model/kernel artifact pin")
tool = read(P / "metatheory/tool-pin.json")
require(sha(Path(tool["path"]) / "bin/lean") == tool["binary_sha256"], "Lean executable pin")
audits = {}
for line in (E / "model-check.txt").read_text().splitlines():
    match = re.fullmatch(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[(.*)\])", line)
    require(match is not None, "unexpected model audit output")
    audits[match[1]] = match[2].split(", ") if match[2] else []
require(len(audits) == 14 and Counter(tuple(v) for v in audits.values()) == Counter({(): 1, ("propext",): 12, ("propext", "Quot.sound"): 1}), "fourteen exact model theorem audits")
accepted, rejected = read(E / "execution/accepted.json"), read(E / "execution/rejected.json")
require(len(accepted) == 17 and len(rejected) == 5, "real proof and semantic rejection corpus sizes")
prior = {row["id"]: row for row in read(P / "evidence/refutation-kernel/examples/summary.json")["rows"]}
for row in accepted:
    target = E / "execution" / row["id"]
    packet = read(E / "examples" / (row["id"] + ".json"))
    require(row["status"] == "checked-term-entailment" and row["packet"] == packet["identity"], "accepted original packet identity")
    require(row["normalized_packet"] == packet["normalized"]["identity"] and row["question"] == packet["normalized"]["question"], "normalized identity labels")
    require(row["axioms"] == {"packetAccepted": ["propext"], "normalizationConnected": ["propext", "Quot.sound"], "originalQuestionEntails": ["propext", "Quot.sound"]}, "applied original term theorem audits")
    require(sha(target / "Check.lean") == row["proof_source_sha256"] and sha(target / "Check.olean") == row["proof_olean_sha256"], "checked original proof artifacts")
    require("sorryAx" not in (target / "lean.txt").read_text(), "no admitted successful theorem")
    if row["id"] in prior:
        require(packet["normalized"]["identity"] == prior[row["id"]]["packet"], "old normalized packet changed")
for row in rejected:
    target = E / "execution/rejected" / row["id"]
    require(row["status"] == "rejected-by-lean" and not (target / "Check.olean").exists() and (target / "lean.txt").exists(), "rejected original cannot carry a compiled success")
fresh = read(E / "fresh/terms-fresh.json")
require(len(fresh["rows"]) == 17 and fresh["calibration-native-sessions"] > 0 and fresh["reconstruction-native-sessions"] == 0, "calibrated fresh original reconstruction")
require(all(row["status"] == "checked-data-connection" and row["kernel-execution"] == "not-run" and row["changed-semantics"] == "rejected" for row in fresh["rows"]), "pure fresh data connection scope")
corpora = []
for name in ["advanced", "features", "native"]:
    now, before = read(E / "corpora" / (name + ".json")), read(P / "evidence/refutation-kernel/corpora" / (name + ".json"))
    signatures = lambda data: {row["id"]: {engine: row[engine]["verdict"] for engine in ["z3", "oxiz"]} for row in data["cases"]}
    require(signatures(now) == signatures(before) and now["disagreements"] == [] and now["invalid-models"] == [], "native result drift: " + name)
    corpora.append({"corpus": name, "questions": len(now["cases"]), "per_case_verdicts_unchanged": True, "disagreements": 0, "invalid_models": 0, "summary": now["summary"]})
require(sum(row["questions"] for row in corpora) == 187, "full native question corpus")
artifacts = {f.relative_to(P).as_posix(): sha(f) for f in sorted(E.rglob("*")) if f.is_file() and f.name not in {"qualification.json", "dossier-qualification.json"} and not any(part.startswith("browser") for part in f.parts)}
result = {"schema": "enchant.formal.typed-term-refutation-qualification.v1", "checkpoint": 17,
          "recorded_utc": datetime.now(timezone.utc).isoformat(), "sdk_pin": read(P / "sdk-pin.json"),
          "worker_sha256": sha(R / "research/oxiz-prototype/worker/target/release/formal-worker"),
          "z3_library_sha256": sha(Path(read(P / "sdk-pin.json")["sdk"]) / "image/priv/z3/bin/libz3.so"),
          "checks": {"source_snapshot": snapshot, "files": counts, "total_assertions": sum(counts.values()), "failures": 0},
          "term_model": {"pin": pin, "tool": tool, "audits": audits, "semantics": "bl/partial-mathematical-int-bool-v1"},
          "applied_proofs": {"accepted_original_questions": 17, "rejected_false_or_undefined_originals": 5,
                             "old_normalized_packets_unchanged": len(prior), "scope": "universal-original-typed-term-entailment-per-question",
                             "connection": "checked-countermodel-preservation-for-each-accepted-question",
                             "general_bl_normalizer_soundness": "not-established"},
          "fresh_reconstruction": fresh, "native_comparison": {"questions": 187, "corpora": corpora},
          "prior_normalized_kernel_theorems": 17, "prior_core_model_theorems": 63,
          "remaining_trust": ["BL term-data to typed partial semantics correspondence and codec",
                              "Core/controller/state/trace model interpretation into terms", "Source extraction and unit/ANF/Core relation checker correspondence",
                              "exact primitive meanings, BL compiler and BEAM runtime", "local proof-tool execution and artifact custody"],
          "retained_failed_attempts": "Model import/type setup; capped broad evaluator simplification; finite-row staging; original integer-type reflection and conditional-guard proof generation. Failed/sorryAx diagnostics are excluded from all accepted proof audits.",
          "production_default_changed": False, "compiler_proof_authority": False, "artifact_sha256": artifacts}
(E / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"assertions": sum(counts.values()), "files": len(counts), "original_term_proofs": 17, "rejected_altered_originals": 5, "unchanged_backend_questions": 187}))
