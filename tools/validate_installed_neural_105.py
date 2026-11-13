"""Read-only installed native runtime/notice validation, no GPU or network needed."""
import hashlib
import json
import os
from pathlib import Path
import sys

app = Path(os.environ['PYTHONPATH'].split(os.pathsep)[0]).resolve(strict=True)
sys.path.insert(0,str(app))
from photomesh import engine  # noqa: E402

assert Path(engine.__file__).resolve().is_relative_to(app), engine.__file__
runtime = app/'photomesh/resources/neural-cuda12'
record = json.loads((runtime/'runtime.json').read_text(encoding='utf-8'))
for asset in record['assets']:
    for item in asset['files']:
        file=runtime/item['name']
        with file.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256'],file
    name = 'NVIDIA-cuDNN-9.8.0-LICENSE.txt' if asset['component']=='cudnn' else 'NVIDIA-CUDA-12.8.1-LICENSE.txt'
    notice=app/'photomesh/resources/third-party/neural-cuda12'/name
    assert hashlib.sha256(notice.read_bytes()).hexdigest()==asset['license_sha256'],notice
expected={item['name'] for asset in record['assets'] for item in asset['files']} | {'runtime.json'}
assert {p.name for p in runtime.iterdir() if p.is_file()} == expected
modern=app.parent/'tools/colmap/bin/colmap.exe'
legacy=app.parent/'tools/colmap-legacy/bin/colmap.exe'
original=os.environ['PATH']
assert str(runtime) in engine.child_env(str(modern))['PATH'].split(os.pathsep)
assert str(runtime) not in engine.child_env(str(legacy))['PATH'].split(os.pathsep)
assert os.environ['PATH']==original
html=(app/'photomesh/resources/third-party/index.html').read_text(encoding='utf-8')
assert 'neural-cuda12/NVIDIA-cuDNN-9.8.0-LICENSE.txt' in html
print(f'Installed private neural runtime: exact {len(expected)-1} DLLs, original licenses and child environment verified')
