import numpy as np
import pytest
from photomesh.survey_geometry import MeshSurface, distance_components


def surface():
    # Two sloping strips, separated by a real hole from x=1 to x=2.
    vertices = np.array([[0, 0, 0], [1, 0, 1], [0, 1, 2], [1, 1, 3],
                         [2, 0, 2], [3, 0, 3], [2, 1, 4], [3, 1, 5]], dtype=float)
    faces = np.array([[0, 1, 2], [1, 3, 2], [4, 5, 6], [5, 7, 6]])
    return MeshSurface(vertices, faces)


def test_section_uses_mesh_and_preserves_real_gaps():
    mesh = surface()
    distance, z = mesh.section([0, .5], [3, .5], samples=13)
    expected = distance + 1
    expected[(distance > 1) & (distance < 2)] = np.nan
    np.testing.assert_allclose(z, expected, atol=1e-10)
    hit = mesh.pick([.5, .5, 20], [0, 0, -1])
    np.testing.assert_allclose(hit, [.5, .5, 1.5])
    assert mesh.pick([1.5, .5, 20], [0, 0, -1]) is None


def test_section_highest_intersection_and_large_origin_precision():
    base = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float)
    vertices = np.vstack([base, base + [0, 0, 3]]) + [500000, 4500000, 100]
    mesh = MeshSurface(vertices, np.array([[0, 1, 2], [3, 4, 5]]))
    _, z = mesh.section([500000.1, 4500000.1], [500000.5, 4500000.1], samples=5)
    np.testing.assert_allclose(z, 103, atol=1e-9)


def test_measurement_slope_and_degenerate_section():
    measurement = distance_components([0, 0, 0], [3, 4, 12])
    assert measurement['distance'] == 13 and measurement['horizontal'] == 5
    assert measurement['slope_percent'] == 240
    assert distance_components([0, 0, 0], [0, 0, 2])['slope_percent'] is None
    with pytest.raises(ValueError):
        surface().section([0, 0], [0, 0])


def test_gap_narrower_than_profile_sampling_is_not_bridged():
    left, right = 1.001, 1.002
    vertices = np.array([[0, 0, 0], [left, 0, 0], [0, 1, 0], [left, 1, 0],
                         [right, 0, 0], [3, 0, 0], [right, 1, 0], [3, 1, 0]])
    mesh = MeshSurface(vertices, np.array([[0, 1, 2], [1, 3, 2], [4, 5, 6], [5, 7, 6]]))
    along, heights = mesh.section([0, .5], [3, .5], samples=4)
    hole = (along > left) & (along < right)
    assert hole.any() and np.isnan(heights[hole]).all()
    assert np.isfinite(heights[~hole]).all()


def test_ascii_mesh_keeps_submillimetre_coordinates_at_large_origin(tmp_path):
    from photomesh.survey_geometry import load_surface
    path = tmp_path / 'precise.ply'
    path.write_text('ply\nformat ascii 1.0\nelement vertex 3\nproperty double x\n'
        'property double y\nproperty double z\nelement face 1\n'
        'property list uchar int vertex_indices\nend_header\n'
        '500000.001 4500000.001 100.001\n500001.001 4500000.001 100.001\n'
        '500000.001 4500001.001 100.001\n3 0 1 2\n')
    surface = load_surface(str(path))
    hit = surface.pick([500000.101, 4500000.101, 200], [0, 0, -1])
    np.testing.assert_allclose(hit, [500000.101, 4500000.101, 100.001], atol=1e-9, rtol=0)


def test_cloud_measurement_does_not_pick_a_hidden_class(tmp_path):
    from photomesh.plycodec import PlyDocument, PlyElement
    from photomesh.survey_geometry import pick_cloud
    path = tmp_path / 'classes.ply'
    records = np.array([(0., 0., 1., 2), (0., 0., 3., 1)],
        dtype=[('x', 'f8'), ('y', 'f8'), ('z', 'f8'), ('classification', 'u1')])
    PlyDocument([PlyElement.describe(records, 'vertex')]).write(path)
    np.testing.assert_allclose(pick_cloud(path, [0, 0, 10], [0, 0, -1]), [0, 0, 3])
    np.testing.assert_allclose(pick_cloud(path, [0, 0, 10], [0, 0, -1], classes=[2]), [0, 0, 1])
