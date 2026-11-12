"""Cross-reader PLY interoperability and malformed-file safety."""
import io

import numpy as np
import pytest
from plyfile import PlyData, PlyElement

from photomesh.plycodec import PlyDocument


@pytest.mark.parametrize("text,endian", [(True, "<"), (False, "<"), (False, ">")])
def test_roundtrip_custom_elements_and_variable_lists(text, endian):
    vertices = np.zeros(4, dtype=[("x", "f8"), ("y", "f8"), ("z", "f8"),
                                  ("red", "u1"), ("confidence", "u2"), ("class", "u1")])
    vertices["x"] = [4678123.123456789, 1, 2, 3]
    vertices["red"] = [0, 128, 250, 255]
    vertices["confidence"] = [0, 256, 50000, 65535]
    vertices["class"] = [2, 6, 2, 1]
    faces = np.empty(2, dtype=[("vertex_indices", object), ("material", "u1")])
    faces["vertex_indices"] = [np.array([0, 1, 2]), np.array([0, 1, 2, 3])]
    faces["material"] = [5, 9]
    edges = np.array([(0, 1), (1, 2)], dtype=[("a", "i4"), ("b", "i4")])
    original = PlyData([PlyElement.describe(edges, "edge"), PlyElement.describe(vertices, "vertex"),
                        PlyElement.describe(faces, "face", len_types={"vertex_indices": "u2"})],
                       text=text, byte_order=endian, comments=["fixture"], obj_info=["original metadata"])
    source = io.BytesIO(); original.write(source); source.seek(0)
    ours = PlyDocument.read(source)
    assert [e.name for e in ours.elements] == ["edge", "vertex", "face"]
    output = io.BytesIO(); ours.write(output); output.seek(0)
    recovered = PlyData.read(output, mmap=False)
    assert recovered.comments == ["fixture"]
    assert recovered.obj_info == ["original metadata"]
    for field in vertices.dtype.names:
        np.testing.assert_array_equal(recovered["vertex"].data[field], vertices[field])
    for i in range(2):
        np.testing.assert_array_equal(recovered["face"].data["vertex_indices"][i], faces["vertex_indices"][i])
    assert recovered["face"].properties[0].len_dtype == "u2"
    np.testing.assert_array_equal(recovered["edge"].data["a"], edges["a"])


def test_world_export_retains_list_valued_vertex_properties(tmp_path):
    from photomesh.export import export_ply_world
    vertices = np.empty(1, dtype=[("x", "f8"), ("y", "f8"), ("z", "f8"), ("tags", object)])
    vertices["x"], vertices["y"], vertices["z"] = 1.25, 2.5, 3.75
    vertices["tags"][0] = np.array([10, 20], dtype="u2")
    source, output = tmp_path / "custom.ply", tmp_path / "world.ply"
    PlyData([PlyElement.describe(vertices, "vertex", val_types={"tags": "u2"})], text=True).write(source)
    export_ply_world(str(source), str(output), [1e6, 2e6, 3e6])
    recovered = PlyData.read(output, mmap=False)["vertex"].data
    assert recovered["x"][0] == 1000001.25
    assert recovered["y"][0] == 2000002.5
    assert recovered["z"][0] == 3000003.75
    np.testing.assert_array_equal(recovered["tags"][0], [10, 20])


@pytest.mark.parametrize("content", [
    b"ply\nformat ascii 1.0\nelement vertex 999999999999\nproperty float x\nend_header\n",
    b"ply\nformat ascii 1.0\nelement vertex 1\nproperty uchar x\nend_header\n256\n",
    b"ply\nformat ascii 1.0\nelement face 1\nproperty list uchar int vertex_indices\nend_header\n3 0 1\n",
    b"ply\nformat binary_little_endian 1.0\nelement face 1\nproperty list float int vertex_indices\nend_header\n\0\0\0\0",
    b"ply\nformat ascii 9.0\nelement vertex 0\nproperty float x\nend_header\n",
])
def test_malformed_inputs_fail_explicitly(content):
    with pytest.raises(ValueError):
        PlyDocument.read(io.BytesIO(content))


def test_standard_large_cloud_still_uses_fast_path(tmp_path, monkeypatch):
    from photomesh.pcfilter import read_cloud, write_cloud
    xyz = np.arange(3000, dtype=float).reshape(-1, 3)
    path = tmp_path / "cloud.ply"
    write_cloud(str(path), xyz)
    def not_general(*args, **kwargs):
        raise AssertionError("Standard clouds must use the streaming/NumPy fast reader")
    monkeypatch.setattr(PlyDocument, "read", not_general)
    np.testing.assert_array_equal(read_cloud(str(path))["xyz"], xyz)


@pytest.mark.parametrize("text,endian", [(True, "<"), (False, "<"), (False, ">")])
def test_scalar_named_list_is_not_a_list_declaration(tmp_path, text, endian):
    from photomesh.plyio import load_ply
    from photomesh.export import export_ply_world
    from photomesh.georef import transform_ply
    vertices = np.array([(1., 2., 3., 4.)],
                        dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"), ("list", "f4")])
    source, rewritten, world = (tmp_path / name for name in ("input.ply", "rewrite.ply", "world.ply"))
    PlyData([PlyElement.describe(vertices, "vertex")], text=text, byte_order=endian).write(source)
    document = PlyDocument.read(source)
    document.write(rewritten)
    np.testing.assert_array_equal(PlyData.read(rewritten, mmap=False)["vertex"].data["list"], [4.])
    np.testing.assert_array_equal(load_ply(str(source))["points"], [[1., 2., 3.]])
    transform = np.eye(4); transform[:3, 3] = [10., 20., 30.]
    transform_ply(str(source), transform)
    export_ply_world(str(source), str(world), [1000., 2000., 3000.])
    recovered = PlyData.read(world, mmap=False)["vertex"].data
    np.testing.assert_array_equal(recovered["list"], [4.])
    np.testing.assert_array_equal(np.column_stack([recovered[n] for n in "xyz"]), [[1011., 2022., 3033.]])
