"""Reconstruct checkpoint 18 from source snapshots and retained successful checks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / "evidence/obligations"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


snapshots = [read(E / name) for name in ["check-source-pin.json", "proof-source-pin.json"]]
for snapshot in snapshots:
    for name, digest in snapshot["sha256"].items():
        path = P / name
        require(sha(path) == digest, "source changed since checked snapshot: " + name)
        previous = subprocess.run(["git", "show", snapshot["code_commit"] + ":" + path.relative_to(R).as_posix()], cwd=R, check=True, stdout=subprocess.PIPE).stdout
        require(previous == path.read_bytes(), "snapshot differs from recorded commit: " + name)
log = (E / "checks.txt").read_text()
counts = dict((name, int(n)) for name, n in re.findall(r"✓\s+(formal\.[\w-]+)\s+(\d+) passed", log))
require(len(counts) == 31 and "31 file(s) passed, 0 failed, 0 incoherent" in log, "successful 31-file BL integration check")
require(counts["formal.obligation-test"] == 302, "common coverage and policy assertion count")
require("Ran 6 tests" in (E / "bridge-check.txt").read_text() and "\nOK\n" in (E / "bridge-check.txt").read_text(), "successful common manifest checks")
require("Ran 4 tests" in (E / "prior-term-regression-check.txt").read_text() and "\nOK\n" in (E / "prior-term-regression-check.txt").read_text(), "choice-free original term regressions")
for name in ["refutation-pin.json", "terms-pin.json"]:
    pin = read(P / "metatheory" / name)
    for key in ["source", "compiled"]:
        require(sha(P / pin[key]["path"]) == pin[key]["sha256"], "model/kernel pin: " + name)
tool = read(P / "metatheory/tool-pin.json")
require(sha(Path(tool["path"]) / "bin/lean") == tool["binary_sha256"], "Lean executable pin")
examples, results = read(E / "examples/summary.json")["rows"], read(E / "execution/results.json")
require(len(examples) == len(results) == 13, "thirteen exact examples")
require({r["subject-kind"] for r in examples} == {"query", "contract", "loop", "translation", "protocol", "source-protocol", "protocol-trace"}, "all seven formal subjects")
require(sum(r["status"] == "checked-required-term-evidence" for r in results) == 11, "eleven complete declared bundles")
require(sum(r["status"] == "incomplete-obligation-evidence" for r in results) == 2, "two incomplete subjects remain visible")
require(sum(r["coverage"]["required"] for r in results) == 24 and sum(r["coverage"]["ready"] for r in results) == 22, "required coverage totals")
require(sum(len(r["checked"]) for r in results) == 23 and sum(r["coverage"]["unreachable"] for r in results) == 1, "checked leaf and unreachability counts")
by_id = {r["id"]: r for r in examples}
choice = []
for result in results:
    require(result["manifest"] == by_id[result["id"]]["manifest"] and result["plan"] == by_id[result["id"]]["plan"], "manifest/plan identity")
    require(result["model_theorem"] == "not-established-by-this-runner" and result["compiler_proof_authority"] is False, "leaf/model authority distinction")
    for row in result["checked"]:
        target = E / "execution" / result["id"] / "rows" / f"{row['index']:04d}"
        receipt = read(target / "result.json")
        require(receipt["status"] == "checked-term-entailment" and receipt["packet"] == row["packet"], "actual original term proof receipt")
        require(sha(target / "Check.lean") == row["proof_source_sha256"] and sha(target / "Check.olean") == row["proof_olean_sha256"], "checked leaf artifacts")
        require("sorryAx" not in (target / "lean.txt").read_text(), "no admitted accepted theorem")
        used = set(row["axioms"]["originalQuestionEntails"])
        require(used <= {"propext", "Classical.choice", "Quot.sound"}, "standard foundation policy")
        if "Classical.choice" in used:
            choice.append({"subject": result["id"], "label": row["label"], "axioms": row["axioms"]["originalQuestionEntails"]})
require(len(choice) == 2 and all(r["subject"] == "loop" for r in choice), "actual classical loop dependencies")
policy = E / "execution/policy-comparison"
standard, strict = policy / "standard/rows/0000", policy / "choice-free/rows/0000"
require(sha(standard / "Check.lean") == sha(strict / "Check.lean"), "axiom policy compares the exact same theorem/proof source")
require((standard / "Check.olean").exists() and not (strict / "Check.olean").exists(), "strict policy does not retain accepted compiled evidence")
require("Classical.choice" in (strict / "lean.txt").read_text() and "sorryAx" not in (strict / "lean.txt").read_text(), "policy rejection is a genuine audit dependency")
policy_report = {"schema": "enchant.formal.obligation-policy-comparison.v1", "same_proof_source_sha256": sha(standard / "Check.lean"),
                 "standard": {"status": "accepted", "policy": "lean-standard-v1", "axioms": read(standard / "result.json")["axioms"]},
                 "choice_free": {"status": "rejected-by-axiom-policy", "policy": "choice-free-v1", "observed_dependency": "Classical.choice"},
                 "statement_requires_classical_choice": "not-established", "runtime_effect_inferred": False, "compiler_proof_authority": False}
(E / "policy-comparison.json").write_text(json.dumps(policy_report, indent=2) + "\n")
fresh = read(E / "fresh/obligations-fresh.json")
require(len(fresh["rows"]) == 13 and all(v > 0 for v in fresh["calibration"].values()) and all(v == 0 for v in fresh["checking-window"].values()), "positively calibrated fresh proof-data checking")
require(fresh["source-preparation"] == "phase-execution-allowed" and fresh["kernel-execution"] == "not-run", "fresh checker phase/proof scope")
require(all(r["status"] == "checked-data-connection" and r["missing-row"] == "rejected" for r in fresh["rows"]), "fresh full subject coverage")
fresh_commit = fresh["source-commit"]
fresh_code = subprocess.run(["git", "show", fresh_commit + ":research/formal-logic/obligations-recheck.bl"], cwd=R, check=True, stdout=subprocess.PIPE).stdout
require(fresh_code == (P / "obligations-recheck.bl").read_bytes(), "fresh checker source is unchanged")
corpora = []
for name in ["advanced", "features", "native"]:
    now, before = read(E / "corpora" / (name + ".json")), read(P / "evidence/term-refutation/corpora" / (name + ".json"))
    signatures = lambda d: {r["id"]: {engine: r[engine]["verdict"] for engine in ["z3", "oxiz"]} for r in d["cases"]}
    require(signatures(now) == signatures(before) and now["disagreements"] == [] and now["invalid-models"] == [], "native verdict drift: " + name)
    corpora.append({"corpus": name, "questions": len(now["cases"]), "per_case_verdicts_unchanged": True, "summary": now["summary"]})
require(sum(r["questions"] for r in corpora) == 187, "full native comparison corpus")
artifacts = {f.relative_to(P).as_posix(): sha(f) for f in sorted(E.rglob("*")) if f.is_file() and f.name not in {"qualification.json", "dossier-qualification.json"} and not any(part.startswith("browser") for part in f.parts)}
result = {"schema": "enchant.formal.obligation-qualification.v1", "checkpoint": 18, "recorded_utc": datetime.now(timezone.utc).isoformat(),
          "sdk_pin": read(P / "sdk-pin.json"), "worker_sha256": sha(R / "research/oxiz-prototype/worker/target/release/formal-worker"),
          "z3_library_sha256": sha(Path(read(P / "sdk-pin.json")["sdk"]) / "image/priv/z3/bin/libz3.so"),
          "checks": {"source_snapshot": snapshots[0], "files": counts, "total_assertions": sum(counts.values()), "failures": 0},
          "proof_source_snapshot": snapshots[1], "lean_tool": tool, "generic_lean_theorems_added": 0,
          "prior_model_theorems": {"core": 63, "normalized_checker": 17, "typed_terms": 14},
          "common_evidence": {"subjects": 13, "subject_kinds": 7, "complete": 11, "incomplete": 2, "required": 24,
                              "checked_required": 22, "required_entailments": 21, "unreachable": 1, "auxiliary_inconsistency": 1,
                              "classical_dependencies": choice, "model_composition": "reviewed-not-mechanically-proved"},
          "axiom_policy_comparison": policy_report, "fresh_reconstruction": fresh,
          "original_term_regressions": {"accepted": 17, "rejected_altered_originals": 5, "default_policy": "choice-free"},
          "native_comparison": {"questions": 187, "corpora": corpora},
          "remaining_trust": ["full model-to-question interpretation and model-rule composition", "term data/semantic encoding",
                              "Source expansion, specialization and ANF/Core correspondence", "exact primitive semantics, BL compiler and BEAM runtime",
                              "positive feasibility/witness evidence in this facet", "local tool execution and artifact custody"],
          "retained_failures": "initial focused diagnostic comparison; the initial common loop proof audit rejected its Classical.choice dependency before explicit policy was added",
          "production_default_changed": False, "compiler_proof_authority": False, "artifact_sha256": artifacts}
(E / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"files": len(counts), "assertions": sum(counts.values()), "checked_required": 22, "auxiliary_inconsistency": 1,
                  "incomplete_subjects": 2, "native_questions_unchanged": 187}))
