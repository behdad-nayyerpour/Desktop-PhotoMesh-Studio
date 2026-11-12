"""Exercise installed PLY processing offline without the replaced dependency."""
import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile

root = Path(os.environ["PYTHONPATH"]).resolve()
sys.path.insert(0, str(root))
import photomesh  # noqa: E402
assert Path(photomesh.__file__).resolve().is_relative_to(root)
assert importlib.util.find_spec("plyfile") is None


def deny_network(*args, **kwargs):
    raise AssertionError("Installed PLY processing must stay offline")


socket.socket.connect = deny_network
socket.create_connection = deny_network

import numpy as np  # noqa: E402
from photomesh.plyio import load_ply, save_ply  # noqa: E402
from photomesh.export import export_ply_world  # noqa: E402
from photomesh.georef import transform_ply  # noqa: E402
from photomesh.plycodec import PlyDocument  # noqa: E402

with tempfile.TemporaryDirectory(prefix="installed-lens2mesh-ply-") as folder:
    path = Path(folder) / "mesh.ply"
    vertices = np.array([[0., 0., 0.], [1.25, 0., 0.], [0., 2.5, 0.]], dtype=np.float32)
    faces = np.array([[0, 1, 2]], dtype=np.int32)
    colors = np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]])
    save_ply(str(path), vertices, colors, faces)
    loaded = load_ply(str(path))
    np.testing.assert_array_equal(loaded["points"], vertices)
    np.testing.assert_array_equal(loaded["faces"], faces)
    np.testing.assert_allclose(loaded["colors"][:, :3], colors)
    # The formerly ambiguous attribute must survive actual installed transforms
    # and export, not just a source-level reader round trip.
    custom = Path(folder) / "custom.ply"
    custom.write_bytes(b"ply\nformat ascii 1.0\nelement vertex 1\nproperty double x\n"
                       b"property double y\nproperty double z\nproperty float list\n"
                       b"end_header\n1.25 2.5 3.75 42\n")
    matrix = np.eye(4); matrix[:3, 3] = [10., 20., 30.]
    transform_ply(str(custom), matrix)
    world = Path(folder) / "world.ply"
    export_ply_world(str(custom), str(world), [1_000_000., 2_000_000., 3_000_000.])
    document = PlyDocument.read(world)
    v = document["vertex"].data
    np.testing.assert_array_equal(np.column_stack([v[n] for n in "xyz"]),
                                  [[1_000_011.25, 2_000_022.5, 3_000_033.75]])
    np.testing.assert_array_equal(v["list"], [42.])

print("Installed PLY mesh, attributes, transformation and world export verified offline.")
