"""Prepare the pinned comparison tools in a temporary directory on this workstation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
PIN = '9c586f094f4fc88bef440dc8b4d77a2f92c257cc'
WHEELS = {
    'b8/85/e4af82cc9202023862090bfca4ea827d533329e925c758f0cde964cb54b7/nvidia_cuda_nvrtc_cu12-12.9.86-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl':
        '210cf05005a447e29214e9ce50851e83fc5f4358df8b453155d5e1918094dcb4',
    'bc/46/a92db19b8309581092a3add7e6fceb4c301a3fd233969856a8cbf042cd3c/nvidia_cuda_runtime_cu12-12.9.79-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl':
        '25bba2dfb01d48a9b59ca474a1ac43c6ebf7011f1b0b8cc44f54eb6ac48a96c3',
}


def fetch(url, path):
    with urllib.request.urlopen(url, timeout=90) as response, path.open('wb') as out:
        shutil.copyfileobj(response, out)


def bend(root):
    tar = root/'bend.tar.gz'
    fetch(f'https://codeload.github.com/bendlang/bend/tar.gz/{PIN}', tar)
    files = json.loads((HERE/'bend-blobs.json').read_text())
    with tarfile.open(tar) as archive:
        for path in files:
            target = root/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(f'bend-{PIN}/{path}').read())
    return root


def cuda(root):
    for wheel, sha in WHEELS.items():
        path = root/'download.whl'
        fetch('https://files.pythonhosted.org/packages/'+wheel, path)
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != sha:
                raise ValueError('CUDA tool digest mismatch')
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                parts = Path(name).parts
                if len(parts) >= 4 and parts[2] in ('lib', 'include') and not name.endswith('/'):
                    target = root.joinpath(*parts[2:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
    (root/'lib/libnvrtc.so').symlink_to('libnvrtc.so.12')
    (root/'lib/libcuda.so').symlink_to('/run/opengl-driver/lib/libcuda.so')
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='checked-tiles-toolchain-') as tmp:
        root = Path(tmp)
        env = os.environ.copy()
        tree = Path(env['BEND_TREE']) if 'BEND_TREE' in env else bend(root)
        toolkit = Path(env['CUDA_HOME']) if 'CUDA_HOME' in env else cuda(root)
        env.setdefault('BUN', '/nix/store/0gk371kgjyv7s0az07hxjrl8g9k0pf3m-bun-1.4.4/bin/bun')
        env.setdefault('CC', '/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang')
        env['CUDA_HOME'] = str(toolkit)
        paths = [str(toolkit/'lib'), str(toolkit/'lib64'), '/run/opengl-driver/lib',
                 '/nix/store/chqq8mpmpyfi9kgsngya71akv5xicn03-gcc-15.2.0-lib/lib']
        env['LD_LIBRARY_PATH'] = ':'.join(paths + ([env['LD_LIBRARY_PATH']] if env.get('LD_LIBRARY_PATH') else []))
        subprocess.run([sys.executable, '-B', HERE/'compare.py', args.session, tree, '--require-gpu'], env=env, check=True)
        subprocess.run([sys.executable, '-B', HERE/'scene.py', args.session], check=True)


if __name__ == '__main__':
    main()
