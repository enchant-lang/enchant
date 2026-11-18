"""Replay a trusted, locally built region, with the same fresh-process IO as Bend."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from driver import NativeRegion, TOOLS, digest
from opencl_device import Device

revision, backend = Path(sys.argv[1]), sys.argv[2]
receipt = json.loads((revision/'receipt.json').read_text())
raw = Path('input.rgb').read_bytes()
geometry = receipt['width'] * 3, receipt['height'], receipt['tile']
if digest(raw) != receipt['input_sha256']:
    raise ValueError('input identity changed')
if backend == 'cpu':
    elf = revision/'region.so'
    if digest(elf.read_bytes()) != receipt['artifacts']['region.so']:
        raise ValueError('CPU artifact changed')
    native = NativeRegion(elf)
    out = native(raw, *geometry, 4)
else:
    shader = (revision/'region.cl').read_bytes()
    if digest(shader) != receipt['artifacts']['region.cl']:
        raise ValueError('OpenCL artifact changed')
    with Device(TOOLS['opencl'], shader.decode()) as gpu:
        out = gpu.render(raw, *geometry)
Path('prepared.rgb').write_bytes(out)
