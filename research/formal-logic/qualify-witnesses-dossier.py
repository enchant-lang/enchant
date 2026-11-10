"""Record the checked live dossier and the observed browser audit for checkpoint 19."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

P = Path(__file__).resolve().parent
R = P.parent.parent
E = P / "evidence/witnesses"
D = P / "ATLAS.bl.org"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


text = D.read_text()
snapshot = json.loads((E / "dossier-source-pin.json").read_text())
checked_commit = snapshot["code_commit"]
require(sha(D) == snapshot["document_sha256"], "dossier source snapshot digest")
checked = subprocess.run(["git", "show", checked_commit + ":" + D.relative_to(R).as_posix()], cwd=R, check=True, stdout=subprocess.PIPE).stdout
require(checked == D.read_bytes(), "dossier changed since executable cell check")
cells = re.findall(r"^#\+begin_src beam-lisp\b", text, re.M)
require(len(cells) == 27, "twenty-seven executable examples")
require("27 cells, 0 cell errors" in (E / "dossier-cells.txt").read_text(), "successful executable cells")
require("27 cells, 0 cell errors (checked, unchanged)" in (E / "dossier-check.txt").read_text(), "current unchanged cell results")
audit = json.loads((E / "browser-audit/audit.json").read_text())
require(audit["passed"] and all(row["passed"] for row in audit["checks"]), "successful browser audit")
graphs = sorted({row["name"].split("/")[1].split(":")[0] for row in audit["checks"] if row["name"].endswith(": connected topic opens")})
require(len(graphs) == 25 and "formal-positive-witness" in graphs, "all connected graphs, including new constructive witness graph")
images = {name: sha(E / "browser-audit" / name) for name in audit["screenshots"]}
manual = ["phone-positive-witness.png", "desktop-positive-witness.png", "phone-positive-data.png", "desktop-positive-data.png"]
require(all(name in images for name in manual), "recorded manually inspected frames")
blocks = Counter(re.findall(r"^#\+begin_([\w-]+)", text, re.M | re.I))
result = {
    "schema": "enchant.formal.constructive-witness-dossier-qualification.v1",
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "review_url": "https://work.tailcb5318.ts.net:18100/", "internal_url": audit["base"],
    "host_unit": "work-enchant-formal-review.service", "implementation_qualification_sha256": sha(E / "qualification.json"),
    "document": {"path": D.relative_to(R).as_posix(), "sha256": sha(D), "executable_cells": len(cells),
                 "cells_status": "0 errors; checked unchanged", "cell_results_commit": checked_commit,
                 "document_unchanged_since_cell_check": True, "block_kinds": dict(blocks),
                 "semantic_block_kinds": len(set(blocks) - {"src"}),
                 "cell_run_log_sha256": sha(E / "dossier-cells.txt"), "cell_check_log_sha256": sha(E / "dossier-check.txt")},
    "browser": {"audit_script_sha256": sha(P / "story-audit.mjs"), "audit_report_sha256": sha(E / "browser-audit/audit.json"),
                "checks": len(audit["checks"]), "screenshots": len(images), "passed": True,
                "viewports": [{"width": 390, "height": 844, "mobile": True}, {"width": 1440, "height": 1000, "mobile": False}],
                "connected_review_graphs": len(graphs), "review_graph_ids": graphs, "manual_visual_inspection": manual,
                "scope": "Constructive positive SAT evidence, explicit typed original bindings, dual native discovery, undefined arithmetic, actual axiom dependencies, independent existence proof versus fresh full-query attribution, and pending common-format composition; all prior examples, graph navigation/map/fullscreen/focus, themes, declared source access and denied anonymous writes."},
    "screenshot_sha256": images,
    "persistent_owner": {"deliverable": "live formal-logic dossier", "unit": "work-enchant-formal-review.service",
                         "retirement": "research/formal-logic/review stop when the user retires this review"},
    "compiler_proof_authority": False,
}
(E / "dossier-qualification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"cells": len(cells), "checks": len(audit["checks"]), "screenshots": len(images), "graphs": len(graphs), "passed": True}))
