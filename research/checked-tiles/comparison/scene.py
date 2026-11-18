"""Run the white-wash pass through the existing scene worker's EGL executor."""
import argparse
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import statistics
import time

HERE = Path(__file__).resolve().parent
WORKER = HERE.parents[2]/'examples/scene-renderer'
spec = importlib.util.spec_from_file_location('scene_executor', WORKER/'showcase_worker.py')
scene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scene)

FRAGMENT = """#version 300 es
precision highp float;
precision highp int;
uniform highp sampler2D image;
out vec4 color;
void main() {
  uvec3 rgb = uvec3(round(texelFetch(image, ivec2(gl_FragCoord.xy), 0).rgb * 255.0));
  color = vec4(vec3((rgb + 255u) / 2u) / 255.0, 1.0);
}
"""


def compare(directory, width, height, expected):
    raw = (directory/'input.rgb').read_bytes()
    rgba = bytearray(b'\xff' * (4*width*height))
    for channel in range(3):
        rgba[channel::4] = raw[channel::3]
    upload = C.create_string_buffer(bytes(rgba))
    libs = Path('/nix/store/1jzc6hzknfm9hx0676dqwqq82x55z47c-libglvnd-1.7.0/lib')
    gpu = scene.GPU.__new__(scene.GPU)
    try:
        gpu.__init__(os.getenv('SCENE_EGL', str(libs/'libEGL.so.1')),
                     os.getenv('SCENE_GLES', str(libs/'libGLESv2.so.2')), width, height)
        prog = gpu.program((WORKER/'showcase/flat.vert').read_text(), FRAGMENT)
        gpu.use(prog)
        gpu.geometry(gpu.quad, 2)
        gpu.bindf(0x8d40, gpu.final)
        gpu.disable(0x0bd0)  # GL_DITHER would change byte rounding.
        gpu.active(0x84c0)
        gpu.texture(width, height, upload, 0x8058, 0x1401)
        finish = gpu.gb('glFinish', None)
        # The input texture is already resident as it would be between film passes.
        times = []
        for _ in range(5):
            start = time.perf_counter_ns()
            gpu.draw(5, 0, 4)
            finish()
            times.append((time.perf_counter_ns() - start)/1e6)
        gpu.read(0, 0, width, height, 0x1908, 0x1401, gpu.pixels)
        gpu.check()
        result = bytes(gpu.pixels)
        for channel in range(3):
            if result[channel::4] != expected[channel::3]:
                raise ValueError(f'scene worker differs on channel {channel}')
        return {'renderer': gpu.info, 'resident_draw_finish_ms': times, 'median_ms': statistics.median(times),
                'scope': 'compiled existing EGL worker with an independent wash shader, texture resident; readback checked separately'}
    finally:
        gpu.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('session', type=Path)
    a = p.parse_args()
    d = next(r for r in a.session.glob('revision-*') if (r/'receipt.json').exists()
             and (r/'source.bl').read_bytes() == (HERE.parent/'examples/wash.bl').read_bytes())
    receipt = json.loads((d/'receipt.json').read_text())
    result = compare(a.session, receipt['width'], receipt['height'], (d/'beam.rgb').read_bytes())
    (a.session/'scene-comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
