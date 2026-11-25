"""N4d dev SDK builder (scripts/dev-sdk.nix). Standard library only.

Reflinks every file of the qualified base SDK image (btrfs: no data copied),
replaces the files `delta/files/` names (paths relative to
`lib/beam_lisp-0.1.0`), and writes the launch scripts and artifact.json for
this product's own path.
"""
import json
import os
import shutil
from pathlib import Path

out = Path(os.environ["out"])
selection = Path(os.environ["selection"])
image = Path(os.environ["image"])
coordinator = Path(os.environ["coordinator"])
delta = Path(os.environ["delta"])
app = "lib/beam_lisp-0.1.0"

files = delta / "files"
overrides = {}
for path in files.rglob("*"):
    if path.is_file():
        overrides[path.relative_to(files).as_posix()] = path
info = json.loads((delta / "dev.json").read_text())


def clone(source, target):
    """Share `source`'s extents (btrfs reflink through copy_file_range, which
    works across the sandbox's bind mounts where FICLONE answers EXDEV), else
    copy. The image must hold real files: the runtime resolves every SDK path
    physically and refuses one that escapes its root through a symlink."""
    with open(source, "rb") as src, open(target, "wb") as dst:
        size, offset = os.fstat(src.fileno()).st_size, 0
        try:
            while offset < size:
                count = os.copy_file_range(src.fileno(), dst.fileno(), size - offset, offset, offset)
                if count == 0:
                    break
                offset += count
        except OSError:
            offset = 0
        if offset != size:
            src.seek(0)
            dst.seek(0)
            dst.truncate()
            shutil.copyfileobj(src, dst, 1 << 20)
    shutil.copymode(source, target)


payload = image / "payload"
shutil.copytree(payload, out / "payload", symlinks=True, copy_function=clone)
for relative, path in overrides.items():
    target = out / "payload" / app / relative
    if not target.is_file() or target.is_symlink():
        raise SystemExit(f"dev SDK delta names a file the base image lacks: {relative}")
    target.chmod(0o644)
    target.write_bytes(path.read_bytes())
for path in sorted((out / "payload").rglob("*"), reverse=True):
    if not path.is_symlink():
        path.chmod(path.stat().st_mode & ~0o222)
(out / "payload").chmod(0o555)
(out / "lib").symlink_to("payload/lib")
(out / "image").symlink_to(app)
(out / "unit-store").symlink_to(os.path.realpath(image / "unit-store"))
(out / "bl").symlink_to(os.path.realpath(image / "bl"))
(out / "preparation-coordinator").symlink_to(coordinator)

# The base boot.exs names its own image; this product boots its own tree.
(out / "boot.exs").write_text((image / "boot.exs").read_text().replace(str(image), str(out)))
(out / "bin").mkdir()
for name in ("bl", "bl-cold"):
    text = (selection / "bin" / name).read_text()
    (out / "bin" / name).write_text(text.replace(str(selection), str(out)))
    (out / "bin" / name).chmod(0o555)
(out / "bin").chmod(0o555)

metadata = json.loads((selection / "artifact.json").read_text())
assert metadata["kind"] == "sdk" and metadata["version"] == 1 and "dev" not in metadata
metadata["image"] = str(out)
metadata["dev"] = dict(info, version=1, base=str(selection),
                       refusal="development SDK: never a release, publication or preparation predecessor")
(out / "artifact.json").write_text(json.dumps(metadata, sort_keys=True) + "\n")
for name in ("boot.exs", "artifact.json"):
    (out / name).chmod(0o444)
out.chmod(0o555)
