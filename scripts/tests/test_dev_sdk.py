"""N4d: scripts/dev-sdk classifies edits and its builder replaces only the delta."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LOADER = importlib.machinery.SourceFileLoader("dev_sdk", str(ROOT / "scripts/dev-sdk"))
SPEC = importlib.util.spec_from_loader("dev_sdk", LOADER)
DEV = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(DEV)


class DevSdkClassifyTests(unittest.TestCase):
    def test_only_pinned_runtime_hosts_are_built(self):
        hosts, refused = DEV.classify(ROOT, ["priv/host/delay.bl", "priv/host/env.bl"])
        self.assertEqual(["delay.bl", "env.bl"], hosts)
        self.assertEqual([], refused)

    def test_everything_else_names_the_release_path(self):
        changed = ["priv/host/aot.bl", "priv/host/aot_cache.bl", "priv/host/emit.bl",
                   "priv/boot/compiler.bl", "priv/lib/scene/core.bl", "nix/bl-drop.nix",
                   "priv/host/not_a_host_unit.bl"]
        hosts, refused = DEV.classify(ROOT, changed)
        self.assertEqual([], hosts)
        self.assertEqual(len(changed), len(refused))
        for line in refused:
            self.assertIn("scripts/prepare-checkout-sdk", line)
        self.assertIn("compiler key", refused[0])
        self.assertIn("boot compiler", refused[3])
        self.assertIn("U15", refused[4])


class DevSdkBuilderTests(unittest.TestCase):
    def test_builder_reflinks_the_base_and_replaces_exactly_the_delta(self):
        with tempfile.TemporaryDirectory(prefix="dev-sdk-builder-") as temporary:
            base = Path(temporary)
            image, selection, coordinator, delta, out = (base / name for name in
                                                         ("image", "selection", "coordinator", "delta", "out"))
            app = image / "payload/lib/beam_lisp-0.1.0"
            for directory in ("ebin", "priv/host", "priv/bootstrap/seed"):
                (app / directory).mkdir(parents=True)
            (image / "payload/lib/jason-1.4.5/ebin").mkdir(parents=True)
            (image / "payload/lib/jason-1.4.5/ebin/Elixir.Jason.beam").write_bytes(b"dep")
            for name, data in (("ebin/Elixir.BeamLisp.Delay.beam", b"old"), ("ebin/Elixir.BeamLisp.Env.beam", b"env"),
                               ("priv/host/delay.bl", b"; old\n"), ("priv/bootstrap/seed/manifest.term", b"m0")):
                (app / name).write_bytes(data)
            (image / "unit-store").mkdir()
            (image / "bl").write_bytes(b"compound")
            (image / "boot.exs").write_text(f'Code.prepend_path("{image}/image/ebin")\n')
            (selection / "bin").mkdir(parents=True)
            for name in ("bl", "bl-cold"):
                (selection / "bin" / name).write_text(f'exec x "{selection}/boot.exs"\n')
            (selection / "artifact.json").write_text(json.dumps({"kind": "sdk", "version": 1, "image": str(image)}))
            coordinator.mkdir()
            files = delta / "files"
            (files / "ebin").mkdir(parents=True)
            (files / "ebin/Elixir.BeamLisp.Delay.beam").write_bytes(b"new")
            (files / "priv/host").mkdir(parents=True)
            (files / "priv/host/delay.bl").write_bytes(b"; new\n")
            (delta / "dev.json").write_text(json.dumps({"hosts": ["delay.bl"]}))
            env = dict(os.environ, out=str(out), selection=str(selection), image=str(image),
                       coordinator=str(coordinator), delta=str(delta))
            subprocess.run([sys.executable, "-I", str(ROOT / "scripts/dev-sdk-builder.py")], env=env, check=True)
            built = out / "payload/lib/beam_lisp-0.1.0"
            self.assertEqual(b"new", (built / "ebin/Elixir.BeamLisp.Delay.beam").read_bytes())
            self.assertEqual(b"; new\n", (built / "priv/host/delay.bl").read_bytes())
            self.assertEqual(b"env", (built / "ebin/Elixir.BeamLisp.Env.beam").read_bytes())
            self.assertEqual(b"m0", (built / "priv/bootstrap/seed/manifest.term").read_bytes())
            # The runtime resolves SDK paths physically: real files, never links out.
            for path in (out / "payload").rglob("*"):
                self.assertFalse(path.is_symlink(), path)
            self.assertIn(str(out), (out / "boot.exs").read_text())
            self.assertNotIn(str(image), (out / "boot.exs").read_text())
            self.assertIn(str(out), (out / "bin/bl-cold").read_text())
            metadata = json.loads((out / "artifact.json").read_text())
            self.assertEqual(str(out), metadata["image"])
            self.assertEqual(str(selection), metadata["dev"]["base"])
            self.assertEqual(["delay.bl"], metadata["dev"]["hosts"])
            self.assertEqual(str(base / "image/unit-store"), os.path.realpath(out / "unit-store"))

    def test_builder_refuses_a_delta_file_the_base_lacks(self):
        with tempfile.TemporaryDirectory(prefix="dev-sdk-builder-") as temporary:
            base = Path(temporary)
            app = base / "image/payload/lib/beam_lisp-0.1.0/ebin"
            app.mkdir(parents=True)
            (base / "selection").mkdir()
            (base / "coordinator").mkdir()
            (base / "delta/files/ebin").mkdir(parents=True)
            (base / "delta/files/ebin/Elixir.BeamLisp.New.beam").write_bytes(b"x")
            (base / "delta/dev.json").write_text("{}")
            env = dict(os.environ, out=str(base / "out"), selection=str(base / "selection"),
                       image=str(base / "image"), coordinator=str(base / "coordinator"), delta=str(base / "delta"))
            result = subprocess.run([sys.executable, "-I", str(ROOT / "scripts/dev-sdk-builder.py")], env=env,
                                    capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("lacks", result.stderr)


if __name__ == "__main__":
    unittest.main()
