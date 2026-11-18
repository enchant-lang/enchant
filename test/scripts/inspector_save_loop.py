"""Run the ordinary project CLI, filesystem watcher and optional native browser together."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("sdk", type=Path)
parser.add_argument("--browser-out", type=Path)
args = parser.parse_args()
sdk = args.sdk.resolve(strict=True)
bl = str(sdk / "bin/bl")

with tempfile.TemporaryDirectory(prefix="enchant-save-") as tmp:
    project = Path(tmp)
    runtime = project / ".runtime"
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), XDG_STATE_HOME=str(project / ".state"),
               ERL_FLAGS="+S 2:2 +SDcpu 1:1 +SDio 1", BL_ENV="development")
    (project / "env.bl").write_text('{:name "inspector-save-loop"}')
    shutil.copy(root / "examples/tooling/work-observatory.bl", project / "app.bl")
    subject = project / "subject.bl"
    subject.write_text("(ns subject) (defn answer [] 42)")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"

    def command(*argv):
        return subprocess.run([bl, *argv], cwd=project, env=env, check=True, timeout=240)

    def rows():
        with urlopen(url + "/__enchant/snapshot.json", timeout=5) as response:
            return json.load(response)["activity"]["recent"]

    def wait(predicate):
        deadline = time.monotonic() + 200
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise RuntimeError(f"serve exited {server.returncode}")
            try:
                result = predicate(rows())
                if result:
                    return result
            except (URLError, TimeoutError):
                pass
            time.sleep(.2)
        raise TimeoutError("expected activity did not arrive")

    def match(tape, path, tool="quick-check"):
        return [r for r in tape if r["tool"] == tool and r.get("location", {}).get("path") == path]

    server = subprocess.Popen([bl, "serve", "app.bl", "--port", str(port)], cwd=project, env=env)
    try:
        wait(lambda _: True)
        command("check", "--quick", "subject.bl")
        command("codebase", "subject.bl")
        tape = rows()
        quick, outline = match(tape, "subject.bl")[0], match(tape, "subject.bl", "outline")[0]
        assert quick["origin"] == outline["origin"] == "CLI"
        assert quick["counts"]["computed"] == outline["counts"]["reused"] == 1

        subject.write_text("\n]")
        error = wait(lambda t: next((r for r in match(t, "subject.bl") if r["state"] == "failed"), None))
        assert error["location"]["line"] == 2
        subject.write_text("\n]")
        (project / "barrier.bl").write_text("(ns barrier)")
        wait(lambda t: match(t, "barrier.bl"))
        assert match(rows(), "subject.bl")[0]["id"] == error["id"]
        subject.write_text("(ns subject) (defn answer [] 42)")
        fixed = wait(lambda t: next((r for r in match(t, "subject.bl") if r["id"] > error["id"]), None))
        assert fixed["counts"]["reused"] == 1
        if args.browser_out:
            subprocess.run([root / "scripts/inspector-scenario", "--sdk", sdk, "--url", url,
                            "--out", args.browser_out.resolve(), "--save-project", project], check=True)
    finally:
        if args.browser_out and args.browser_out.is_dir():
            try:
                (args.browser_out / "final-activity.json").write_text(json.dumps(rows(), indent=2))
            except (URLError, TimeoutError):
                pass
            for log in (project / ".state").rglob("*.log"):
                shutil.copyfile(log, args.browser_out / ("server-" + log.name))
        server.terminate()
        server.wait(timeout=10)
        try:
            subprocess.run([bl, "realm", "stop"], cwd=project, env=env, timeout=40)
        finally:
            # A held listener can defer realm retirement. Only reap a BEAM
            # whose environment identifies this test's private runtime and SDK.
            identity = {os.fsencode(f"XDG_RUNTIME_DIR={runtime}"), os.fsencode(f"BL_SDK_PRODUCT={sdk}")}
            for process in Path("/proc").glob("[0-9]*"):
                try:
                    if (process / "comm").read_text().strip() != "beam.smp":
                        continue
                    with os.fdopen(os.pidfd_open(int(process.name)), "rb") as handle:
                        if identity.issubset((process / "environ").read_bytes().split(b"\0")):
                            signal.pidfd_send_signal(handle.fileno(), signal.SIGTERM)
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    pass
