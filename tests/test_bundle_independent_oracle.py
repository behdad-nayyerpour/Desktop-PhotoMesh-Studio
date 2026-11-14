"""Compare the adjustment with an independently parameterized SciPy solver."""
import copy

import numpy as np
import pytest
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from photomesh import colmap_io as cio, georef


@pytest.mark.parametrize('outlier', [False, True])
def test_noisy_control_bundle_matches_independent_least_squares(outlier):
    rng = np.random.default_rng(417)
    centers = np.array([[-8., -6., 30.], [8., -6., 31.],
                        [-7., 7., 29.], [8., 8., 30.]])
    rotation = np.diag([1., -1., -1.])
    points = rng.uniform([-8., -6., -.5], [8., 6., .5], (12, 3))
    controls = np.array([[-9., -7., 0.], [9., -7., .3], [0., 8., -.2]])
    all_points = np.vstack([points, controls])

    def uv(rotations, camera_centers, xyz):
        camera_xyz = np.einsum('ijk,ipk->ipj', rotations, xyz[None]-camera_centers[:, None])
        return 500*camera_xyz[..., :2]/camera_xyz[..., 2, None] + [300., 225.]

    measured = uv(np.repeat(rotation[None], 4, axis=0), centers, all_points)
    measured += rng.normal(0., .15, measured.shape)
    if outlier:
        measured[0, 0] += [15., -11.]
    initial_centers = centers + rng.normal(0., .03, centers.shape)
    initial_points = points + rng.normal(0., .02, points.shape)
    images = {}
    for i in range(4):
        images[i+1] = cio.Image(f'image{i}.jpg', 1, cio.rot_to_qvec(rotation),
                                -rotation@initial_centers[i], measured[i, :12].copy(),
                                np.arange(12, dtype=np.int64))
    model = cio.Model({1: cio.Camera(0, 600, 450, np.array([500., 300., 225.]))}, images,
                      cio.Points(np.arange(12, dtype=np.uint64), initial_points,
                                 np.zeros((12, 3), np.uint8), np.full(12, .5),
                                 np.arange(0, 49, 4, dtype=np.int64),
                                 np.tile(np.arange(1, 5), 12).astype(np.uint32),
                                 np.repeat(np.arange(12), 4).astype(np.uint32)))
    marker_observations = {
        str(k): (point.copy(), [(i+1, *measured[i, 12+k]) for i in range(4)])
        for k, point in enumerate(controls)}
    references = {str(k): (point.copy(), np.full(3, .01)) for k, point in enumerate(controls)}
    adjusted = copy.deepcopy(model)
    result = georef.gcp_bundle_adjust(adjusted, marker_observations, references,
                                      {'fit_intrinsics': False, 'huber': 4.,
                                       'max_iterations': 100, 'projection_accuracy': .5},
                                      log=lambda *_: None)

    def pack(rotations, camera_centers, xyz):
        return np.r_[Rotation.from_matrix(rotations).as_rotvec().ravel(),
                     camera_centers.ravel(), xyz.ravel()]

    def residual(parameters):
        rotations = Rotation.from_rotvec(parameters[:12].reshape(4, 3)).as_matrix()
        camera_centers = parameters[12:24].reshape(4, 3)
        xyz = parameters[24:].reshape(15, 3)
        error = uv(rotations, camera_centers, xyz)-measured
        error[:, 12:] /= .5
        # Express the vector-norm Huber objective as least-squares residuals.
        # SciPy differentiates this independently; marker/reference terms retain
        # their full weights, including when automatic tie observations are bad.
        lengths = np.linalg.norm(error[:, :12], axis=2)
        rho = np.where(lengths <= 4, lengths**2, 8*lengths-16)
        error[:, :12] *= np.sqrt(rho/np.maximum(lengths**2, 1e-30))[..., None]
        return np.r_[error.ravel(), ((xyz[12:]-controls)/.01).ravel()]

    initial = pack(np.repeat(rotation[None], 4, axis=0), initial_centers,
                   np.vstack([initial_points, controls]))
    oracle = least_squares(residual, initial, x_scale='jac', ftol=1e-12,
                           xtol=1e-12, gtol=1e-10, max_nfev=100)
    app_parameters = pack(np.array([adjusted.images[i].R() for i in range(1, 5)]),
                          np.array([adjusted.images[i].center() for i in range(1, 5)]),
                          np.vstack([adjusted.points.xyz,
                                     [result['markers'][str(k)] for k in range(3)]]))
    oracle_cost = np.sum(residual(oracle.x)**2)
    app_cost = np.sum(residual(app_parameters)**2)
    assert oracle.success
    assert app_cost < np.sum(residual(initial)**2)
    assert abs(app_cost-oracle_cost) < 1e-5, (app_cost, oracle_cost)
    np.testing.assert_allclose(app_parameters[12:24], oracle.x[12:24], rtol=0, atol=2e-4)
