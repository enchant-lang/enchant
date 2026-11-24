"""Refuse inconsistent compiler copies before launching a producer VM.

These filesystem-only negative controls use inert placeholder bytes. They never
start code or claim that a placeholder is a valid compiler artifact.
"""
import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/qualify-artifact-generation"


class ArtifactGenerationInputsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for folder in ("scripts", "test/scripts", "priv/boot", "priv/bootstrap/seed", "priv/native"):
            (self.root / folder).mkdir(parents=True)
        shutil.copy2(SCRIPT, self.root / "scripts/qualify-artifact-generation")
        (self.root / "scripts/demo-artifact-production").write_text("BOOT = ''\n")
        (self.root / "scripts/check-source-floor").write_text("")
        (self.root / "test/scripts/artifact-generation.bl").write_text("nil\n")
        (self.root / "priv/boot/example.bl").write_text("(ns example)\n")
        (self.root / "priv/native/inert.so").write_bytes(b"inert native input, never loaded")
        (self.root / "env.bl").write_text("{}\n")
        self.seed = self.root / "priv/bootstrap/seed"
        (self.seed / "manifest.term").write_text("inert manifest placeholder\n")
        (self.seed / "Elixir.Probe.beam").write_bytes(b"inert artifact placeholder")
        self.output = self.root / "result"
        self.module = runpy.run_path(str(self.root / "scripts/qualify-artifact-generation"))
        self.arguments = [str(SCRIPT), "--root", str(self.root), "--seed", str(self.seed),
                          "--out", str(self.output)]
        self.native_started = False
        self.real_run = subprocess.run

    def run_without_native(self, command, *args, **kwargs):
        if command[0] == "cp":
            return self.real_run(command, *args, **kwargs)
        self.native_started = True
        raise AssertionError("a producer VM must not start for inconsistent inputs")

    def assert_copy_refused(self, damage):
        real_copytree = shutil.copytree
        diagnostic = io.StringIO()

        def copytree(source, destination, *args, **kwargs):
            result = real_copytree(source, destination, *args, **kwargs)
            damage(Path(destination))
            return result

        with contextlib.redirect_stderr(diagnostic), \
                patch.object(sys, "argv", self.arguments), \
                patch.object(shutil, "copytree", side_effect=copytree), \
                patch.object(subprocess, "run", side_effect=self.run_without_native):
            self.assertEqual(1, self.module["main"]())
        self.assertFalse(self.native_started)
        report = (self.output / "result.json").read_text()
        self.assertIn("copied", report)
        self.assertIn('"self_reproduction_qualified": false', report)
        self.assertIn("ARTIFACT-GENERATION FAILED:", diagnostic.getvalue())
        self.assertIn("copied", diagnostic.getvalue())

    def test_compiler_copy_corruption_refuses_even_when_original_is_unchanged(self):
        before = (self.seed / "Elixir.Probe.beam").read_bytes()

        def damage(destination):
            if destination.parts[-3:] == ("priv", "bootstrap", "seed"):
                (destination / "Elixir.Probe.beam").write_bytes(b"changed copy")

        self.assert_copy_refused(damage)
        self.assertEqual(before, (self.seed / "Elixir.Probe.beam").read_bytes())

    def test_application_code_copy_is_checked_independently(self):
        def damage(destination):
            if destination.name == "ebin":
                (destination / "Elixir.Probe.beam").write_bytes(b"changed code path")

        self.assert_copy_refused(damage)

    def test_copied_source_is_checked_before_code_starts(self):
        def damage(destination):
            if destination.name == "ebin":
                image = destination.parents[3]
                (image / "priv/boot/example.bl").write_text("(ns changed)\n")

        self.assert_copy_refused(damage)

    def test_copied_native_product_is_checked_before_code_starts(self):
        def damage(destination):
            if destination.name == "ebin":
                image = destination.parents[3]
                (image / "priv/native/inert.so").write_bytes(b"changed native copy")

        self.assert_copy_refused(damage)

    def run_staged_fixture(self, *, mismatch=False, fail_preparation=False):
        """Inert artifacts test orchestration only; no BEAM validity is claimed."""
        calls = []
        previous = (self.seed / "Elixir.Probe.beam").read_bytes()

        def run(command, *args, **kwargs):
            nonlocal previous
            if command[0] == "cp":
                return self.real_run(command, *args, **kwargs)
            if command[0] == "elixir":
                env = kwargs["env"]
                target = Path(env["BL_GENERATION_OUTPUT"])
                label = target.name
                image = Path(kwargs["cwd"])
                self.assertEqual(previous, (image / "priv/bootstrap/seed/Elixir.Probe.beam").read_bytes())
                calls.append(("produce", label))
                target.mkdir()
                payload = b"preparation" if label == "P" else b"current"
                if mismatch and label == "C":
                    payload = b"different"
                (target / "Elixir.Probe.beam").write_bytes(payload)
                (target / "manifest.term").write_bytes(b"inert manifest")
                Path(env["BL_GENERATION_BOOTSTRAP_RECEIPT"]).write_text("{}")
                previous = payload
                return subprocess.CompletedProcess(command, 0, "")
            self.assertEqual("python3", command[0])
            label = Path(command[command.index("--seed") + 1]).name
            calls.append(("boot", label))
            return subprocess.CompletedProcess(command, int(fail_preparation and label == "P"), "")

        diagnostic = io.StringIO()
        with patch.object(sys, "argv", self.arguments), \
                patch.object(subprocess, "run", side_effect=run), \
                contextlib.redirect_stderr(diagnostic), contextlib.redirect_stdout(io.StringIO()):
            result = self.module["main"]()
        return result, json.loads((self.output / "result.json").read_text()), calls, diagnostic.getvalue()

    def test_preparation_is_separate_from_exact_two_generation_reproduction(self):
        result, report, calls, _ = self.run_staged_fixture()
        self.assertEqual(0, result)
        self.assertEqual([(kind, stage) for stage in ("P", "B", "C")
                          for kind in ("produce", "boot")], calls)
        self.assertTrue(report["preparation"]["fresh_boot_qualified"])
        self.assertEqual(["B", "C"], [stage["generation"] for stage in report["stages"]])
        self.assertNotEqual(report["preparation"]["files"], report["stages"][0]["files"])
        self.assertTrue(report["self_reproduction_qualified"])

    def test_one_retained_generation_stops_before_other_generations(self):
        self.arguments += ['--generation', 'P']
        result, report, calls, _ = self.run_staged_fixture()
        self.assertEqual(0, result)
        self.assertEqual([('produce', 'P'), ('boot', 'P')], calls)
        self.assertEqual('artifact-generation-stage', report['kind'])
        self.assertTrue(report['generation']['fresh_boot_qualified'])
        self.assertFalse(report['self_reproduction_qualified'])
        self.assertEqual([], report['stages'])

    def test_preparation_does_not_excuse_a_b_c_difference(self):
        result, report, _, diagnostic = self.run_staged_fixture(mismatch=True)
        self.assertEqual(1, result)
        self.assertFalse(report["self_reproduction_qualified"])
        self.assertEqual(["Elixir.Probe.beam"], report["changed_files"])
        self.assertIn("B and C differ", diagnostic)

    def test_preparation_boot_failure_stops_before_reproduction(self):
        result, report, calls, diagnostic = self.run_staged_fixture(fail_preparation=True)
        self.assertEqual(1, result)
        self.assertEqual([("produce", "P"), ("boot", "P")], calls)
        self.assertFalse(report["preparation"]["fresh_boot_qualified"])
        self.assertEqual([], report["stages"])
        self.assertFalse(report["self_reproduction_qualified"])
        self.assertIn("generation P fresh boot failed", diagnostic)

    def run_generation(self, label, out, *extra, preparation=b"preparation", probe_accepts=True):
        """One retained stage through the same inert fixture; answers its calls."""
        calls = []

        def run(command, *args, **kwargs):
            if command[0] == "cp":
                return self.real_run(command, *args, **kwargs)
            if command[0] == "elixir":
                env = kwargs["env"]
                image = Path(kwargs["cwd"])
                seed = (image / "priv/bootstrap/seed/Elixir.Probe.beam").read_bytes()
                if "BL_GENERATION_OUTPUT" not in env:
                    calls.append(("probe", seed))
                    if not probe_accepts:
                        return subprocess.CompletedProcess(command, 1, "sdk_preinit_producer_unproved")
                    Path(env["BL_GENERATION_BOOTSTRAP_RECEIPT"]).write_text('{"installation": "current"}')
                    return subprocess.CompletedProcess(command, 0, "")
                target = Path(env["BL_GENERATION_OUTPUT"])
                calls.append(("produce", label, seed))
                target.mkdir()
                (target / "Elixir.Probe.beam").write_bytes(preparation if label == "P" else b"current")
                (target / "manifest.term").write_bytes(b"inert manifest")
                Path(env["BL_GENERATION_UNIT_STORE"]).mkdir(exist_ok=True)
                Path(env["BL_GENERATION_BOOTSTRAP_RECEIPT"]).write_text("{}")
                return subprocess.CompletedProcess(command, 0, "")
            calls.append(("boot", label))
            return subprocess.CompletedProcess(command, 0, "")

        arguments = [str(SCRIPT), "--root", str(self.root), "--out", str(out), "--generation", label, *extra]
        with patch.object(sys, "argv", arguments), patch.object(subprocess, "run", side_effect=run), \
                contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            result = self.module["main"]()
        return result, json.loads((out / "result.json").read_text()), calls

    def candidate(self):
        candidate = self.root / "previous-compiler"
        candidate.mkdir()
        (candidate / "manifest.term").write_text("previous qualified manifest\n")
        (candidate / "Elixir.Probe.beam").write_bytes(b"previous qualified compiler")
        return candidate

    def test_p_boots_the_previous_compiler_when_its_startup_accepts_this_source(self):
        candidate = self.candidate()
        result, report, calls = self.run_generation("P", self.output, "--bootstrap-candidate", str(candidate))
        self.assertEqual(0, result)
        self.assertEqual([("probe", b"previous qualified compiler"),
                          ("produce", "P", b"previous qualified compiler"), ("boot", "P")], calls)
        self.assertEqual(str(candidate), report["initial_seed"])
        self.assertTrue(report["bootstrap_choice"]["accepted"])
        inputs = json.loads((self.output / "inputs.json").read_text())
        self.assertIn("priv/bootstrap/seed/Elixir.Probe.beam", inputs)

    def test_a_refused_previous_compiler_falls_back_to_the_committed_floor(self):
        candidate = self.candidate()
        result, report, calls = self.run_generation("P", self.output, "--bootstrap-candidate", str(candidate),
                                                    probe_accepts=False)
        self.assertEqual(0, result)
        self.assertEqual([("probe", b"previous qualified compiler"),
                          ("produce", "P", b"inert artifact placeholder"), ("boot", "P")], calls)
        self.assertEqual(str(self.seed.resolve()), report["initial_seed"])
        self.assertFalse(report["bootstrap_choice"]["accepted"])
        self.assertIn("sdk_preinit_producer_unproved", report["bootstrap_choice"]["refusal"])

    def test_a_bootstrap_candidate_selects_only_preparation(self):
        with patch.object(sys, "argv", self.arguments + ["--generation", "B", "--bootstrap-candidate",
                                                         str(self.candidate())]), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.module["main"]()

    def staged_products(self, preparation):
        p, b = self.root / "product-P", self.root / "product-B"
        self.assertEqual(0, self.run_generation("P", p, preparation=preparation)[0])
        self.assertEqual(0, self.run_generation("B", b, "--seed", str(p / "P"), preparation=preparation)[0])
        return p, b

    def test_c_is_elided_when_b_booted_a_byte_identical_p(self):
        p, b = self.staged_products(b"current")
        out = self.root / "product-C"
        result, report, calls = self.run_generation("C", out, "--seed", str(b / "B"),
                                                    "--elide-when-equal", str(p), str(b))
        self.assertEqual(0, result)
        self.assertEqual([], calls)
        stage = report["generation"]
        self.assertTrue(stage["elided"])
        self.assertFalse(stage["produced"])
        self.assertEqual("byte-identical-predecessor", stage["fixpoint"]["kind"])
        self.assertEqual(json.loads((b / "result.json").read_text())["generation"]["files"], stage["files"])
        self.assertEqual(b"current", (out / "C/Elixir.Probe.beam").read_bytes())
        self.assertTrue((out / "unit-store").is_dir())

    def test_c_runs_when_p_and_b_differ(self):
        p, b = self.staged_products(b"preparation")
        out = self.root / "product-C"
        result, report, calls = self.run_generation("C", out, "--seed", str(b / "B"),
                                                    "--elide-when-equal", str(p), str(b))
        self.assertEqual(0, result)
        self.assertEqual([("produce", "C", b"current"), ("boot", "C")], calls)
        self.assertTrue(report["generation"]["fresh_boot_qualified"])
        self.assertNotIn("elided", report["generation"])

    def test_c_elision_refuses_a_changed_retained_b(self):
        p, b = self.staged_products(b"current")
        (b / "B/Elixir.Probe.beam").write_bytes(b"tampered")
        out = self.root / "product-C"
        result, report, _ = self.run_generation("C", out, "--seed", str(b / "B"),
                                                "--elide-when-equal", str(p), str(b))
        self.assertEqual(1, result)
        self.assertIn("incomplete for C's elision check", report["error"])

    def assert_seed_rejected(self):
        with patch.object(sys, "argv", self.arguments), \
                patch.object(subprocess, "run", side_effect=self.run_without_native), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                self.module["main"]()
        self.assertEqual(2, error.exception.code)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.native_started)

    def test_untracked_recording_is_not_a_compiler_input(self):
        (self.seed / "recording.webm").write_bytes(b"recording")
        self.assert_seed_rejected()

    def test_symlink_is_not_a_regular_compiler_input(self):
        (self.seed / "linked.beam").symlink_to(self.seed / "Elixir.Probe.beam")
        self.assert_seed_rejected()


if __name__ == "__main__":
    unittest.main()
