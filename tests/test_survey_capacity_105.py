import copy
import numpy as np
import pytest
from scipy import sparse
from photomesh.survey_capacity import grouped_median, nearest_neighbours, solve_camera_system


@pytest.mark.parametrize('k', [0, 1, 3, 40])
def test_neighbours_match_independent_all_pair_distances_and_ties(k):
    rng = np.random.default_rng(92)
    xyz = rng.normal(size=(37, 3))
    xyz[6:10] = xyz[0]
    xyz[14:18] = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]]
    actual = list(nearest_neighbours(xyz, k))
    expected = []
    for i, point in enumerate(xyz):
        candidates = np.flatnonzero(np.arange(len(xyz)) != i)
        distances = np.linalg.norm(xyz[candidates]-point, axis=1)
        candidates = candidates[np.lexsort((candidates, distances))]
        expected.extend((i, int(j)) for j in candidates[:k])
    assert sorted(actual) == sorted(expected)


def test_duplicate_neighbours_do_not_expand_quadratically():
    xyz = np.zeros((20000, 3))
    pairs = list(nearest_neighbours(xyz, 2))
    assert len(pairs) == 40000
    assert all(i != j and j <= 2 for i, j in pairs)


@pytest.mark.parametrize('k', [1, 2, 4])
def test_distinct_equidistant_neighbours_are_deterministic(k):
    xyz = np.array([[0, 0, 0], [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0]], float)
    actual = list(nearest_neighbours(xyz, k))
    for i in range(len(xyz)):
        other = np.flatnonzero(np.arange(len(xyz)) != i)
        distance = np.linalg.norm(xyz[other]-xyz[i], axis=1)
        expected = other[np.lexsort((other, distance))][:k].tolist()
        assert [j for a, j in actual if a == i] == expected


@pytest.mark.parametrize('size', [1, 2, 3, 20000])
def test_vectorized_median_matches_independent_per_cell_numpy(size):
    rng = np.random.default_rng(4)
    idx = rng.integers(0, 501, size)
    z = rng.normal(size=size)
    keys, actual = grouped_median(idx, z)
    np.testing.assert_array_equal(keys, np.unique(idx))
    expected = [np.median(z[idx == key]) for key in keys]
    np.testing.assert_array_equal(actual, expected)


def test_singleton_large_height_does_not_overflow():
    keys, heights = grouped_median([3], np.array([1e308]))
    np.testing.assert_array_equal(heights, [1e308])
    assert keys.tolist() == [3]


def test_median_preserves_automatic_resolution_population(tmp_path, monkeypatch):
    import math
    from photomesh import memguard, ortho
    from photomesh.dem_engine import build_dem
    from photomesh.plyio import save_ply
    rng = np.random.default_rng(72)
    xyz = rng.uniform([0, 0, 0], [100, 100, 3], size=(120001, 3)).astype(np.float32).astype(float)
    path = tmp_path/'cloud.ply'; save_ply(str(path), xyz)
    # Legacy fast-read path estimates occupancy using every point when it fits;
    # streaming the median must not silently substitute a smaller sample here.
    lo, hi = xyz.min(0), xyz.max(0)
    grid = max(float(np.ptp(hi[:2]-lo[:2])), float(np.max(hi[:2]-lo[:2])))/512 or 1.
    cells = np.floor((xyz[:, :2]-lo[:2])/grid).astype(np.int64)
    occupied = len(np.unique(cells[:, 0]*100000+cells[:, 1]))
    expected = ortho.nice(2*math.sqrt(occupied*grid*grid/len(xyz)))
    monkeypatch.setattr(memguard, 'require_available_bytes', lambda: 8*1024**3)
    result = build_dem(dict(cloud=str(path), out_dir=str(tmp_path/'dem'), aggregation='median',
        interpolation='Disabled', tile=256), log=lambda *_: None)
    assert result['pixel_size'] == expected


def test_sparse_direct_solution_preserves_dense_normal_equations(monkeypatch):
    rng = np.random.default_rng(11)
    a = sparse.random(180, 180, density=.03, random_state=rng, format='csr')
    matrix = a.T @ a + sparse.eye(180)*.2
    rhs = rng.normal(size=180)
    expected = solve_camera_system(matrix, rhs, dense_limit=1000)
    # Large path must never materialize a dense camera matrix.
    monkeypatch.setattr(sparse.csc_matrix, 'toarray', lambda *a, **kw: pytest.fail('dense camera allocation'))
    actual = solve_camera_system(matrix, rhs, dense_limit=0)
    np.testing.assert_allclose(actual, expected, rtol=1e-11, atol=1e-11)
    np.testing.assert_allclose(matrix @ actual, rhs, atol=1e-12)


def test_sparse_bundle_matches_dense_reference_poses_calibration_and_points(monkeypatch):
    from test_dense_mesh_gcp import synthetic_model
    from photomesh import georef, survey_capacity, colmap_io
    rng = np.random.default_rng(731)
    original = synthetic_model(n_img=8, n_pts=120, two_cameras=True)
    for image in original.images.values():
        image.xys += rng.normal(0, .1, image.xys.shape)
    dense, sparse_model = copy.deepcopy(original), copy.deepcopy(original)
    solve = survey_capacity.solve_camera_system
    options = dict(fit_intrinsics=True, max_iterations=8)
    georef.gcp_bundle_adjust(dense, {}, {}, options, log=lambda *_: None)
    monkeypatch.setattr(survey_capacity, 'solve_camera_system', lambda m, r: solve(m, r, dense_limit=0))
    georef.gcp_bundle_adjust(sparse_model, {}, {}, options, log=lambda *_: None)
    # Unconstrained similarity gauge permits tiny pose differences; compare the
    # complete reconstruction, not only the solver's own residual report.
    for i in dense.images:
        np.testing.assert_allclose(sparse_model.images[i].center(), dense.images[i].center(), atol=2e-6)
    for c in dense.cameras:
        np.testing.assert_allclose(sparse_model.cameras[c].params, dense.cameras[c].params, rtol=2e-6, atol=2e-6)
    np.testing.assert_allclose(colmap_io.observation_errors(sparse_model)[0],
                               colmap_io.observation_errors(dense)[0], atol=2e-6)
