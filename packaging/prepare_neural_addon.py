"""Authenticate every add-on DLL and preserve original NVIDIA licence texts."""
import argparse
import hashlib
import json
from pathlib import Path

from neural_runtime import runtime_files, runtime_manifest, specification


def prepare(runtime, output):
    expected = runtime_files()
    for entry in expected:
        path = runtime / Path(entry['path']).name
        if path.is_symlink() or path.is_junction() or not path.is_file():
            raise ValueError('Missing or linked GPU add-on file: ' + str(path))
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != entry['sha256']:
                raise ValueError('GPU add-on bytes differ: ' + str(path))
    if {p.name for p in runtime.iterdir()} != {Path(e['path']).name for e in expected}:
        raise ValueError('Unexpected GPU add-on file')
    source = Path(__file__).resolve().parents[1]
    names = {'NVIDIA-CUDA-12.8.1-LICENSE.txt', 'NVIDIA-cuDNN-9.8.0-LICENSE.txt'}
    texts = []
    for name in sorted(names):
        path = source / 'photomesh/resources/third-party/neural-cuda12' / name
        data = path.read_bytes()
        allowed = {asset['license_sha256'] for asset in specification()['assets']}
        if hashlib.sha256(data).hexdigest() not in allowed:
            raise ValueError('Original NVIDIA notice differs: ' + name)
        texts.append(name + '\n\n' + data.decode('utf-8'))
    output.mkdir(parents=True, exist_ok=True)
    notices = output / 'packaging'
    notices.mkdir(exist_ok=True)
    own_license = (source / 'LICENSE').read_bytes()
    (notices / 'Lens2Mesh-LICENSE.txt').write_bytes(own_license)
    for name in names:
        original = source / 'photomesh/resources/third-party/neural-cuda12' / name
        (notices / name).write_bytes(original.read_bytes())
    (output / 'addon-license.txt').write_text(own_license.decode('utf-8') + '\n\n' + '\n\n'.join(texts), encoding='utf-8-sig')
    (output / 'payload-verification.json').write_text(json.dumps(dict(files=expected), indent=2))
    assert (runtime / 'runtime.json').read_bytes() == runtime_manifest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.runtime.resolve(strict=True), args.output)
    print('Authenticated 13 optional GPU DLLs, manifest and original NVIDIA notices')
