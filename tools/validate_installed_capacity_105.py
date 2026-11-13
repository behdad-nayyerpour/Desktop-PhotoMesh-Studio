"""Offline installed Qt-cleanup, native mesh DEM and document identity check."""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile

app_root = Path(os.environ['PYTHONPATH']).resolve()
sys.path.insert(0, str(app_root))
import photomesh  # noqa: E402
assert Path(photomesh.__file__).resolve().is_relative_to(app_root)
install = app_root.parent
plan = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
assert len(plan['files']) == 881
for entry in plan['files']:
    assert not (install/entry['path']).exists(), entry['path']
assert (install/'python/Lib/site-packages/PySide6/Qt6Core.dll').is_file()


def blocked(*_args, **_kwargs):
    raise AssertionError('Installed capacity and native processing must remain offline')


socket.socket.connect = socket.create_connection = socket.getaddrinfo = blocked
from photomesh import documentation, survey_capacity  # noqa: E402
for module in (documentation, survey_capacity):
    assert Path(module.__file__).resolve().is_relative_to(app_root)
manual = documentation.RESOURCES/'manual/PhotoMeshStudio_1.0.4_Complete_User_Manual.pdf'
assert hashlib.sha256(manual.read_bytes()).hexdigest() == '632dde8b0392787d735610dcf805ade49f10068f6086d4e01137f5a5e31610a4'
assert (documentation.RESOURCES/'third-party/index.html').is_file()

import numpy as np  # noqa: E402
from photomesh.plyio import save_ply  # noqa: E402
from photomesh.dem_engine import build_dem  # noqa: E402
from photomesh.geotiff import TiffReader  # noqa: E402
with tempfile.TemporaryDirectory(prefix='installed-capacity-') as directory:
    folder = Path(directory)
    vertices = np.array([[0, 0, 0], [10, 0, 10], [0, 10, 20], [10, 10, 30]], float)
    path = folder/'mesh.ply'
    save_ply(str(path), vertices, faces=np.array([[0, 1, 2], [1, 3, 2]], np.int32))
    result = build_dem(dict(source='Mesh', mesh=str(path), out_dir=str(folder/'dem'),
        pixel_size=1., interpolation='Disabled'), log=lambda *_: None)
    with TiffReader(result['path']) as reader:
        grid = reader.read_level(0)[..., 0]
    y, x = np.mgrid[:10, :10]
    np.testing.assert_allclose(grid, x+.5 + 2*(9.5-y), atol=1e-6)
print('Installed Qt cleanup, unchanged approved manual, notices and native mesh DEM passed offline')
