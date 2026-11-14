"""Independent evidence harness plus real checkpoint isolation (no mocked BA)."""
from pathlib import Path

import numpy as np
import pytest

from photomesh import colmap_io as cio, georef as g
from tools.verify_survey_math import run_checks

ROOT = Path(__file__).resolve().parents[1]


def test_independent_answers_with_absolute_tolerances():
    pytest.importorskip('pyproj')
    report = run_checks(ROOT)
    assert report['passed'], [row for row in report['checks'] if row['status'] != 'PASS']


def test_audit_detects_wrong_rmse_formula(monkeypatch):
    original = g.rmse

    def wrong(rows, kind):
        result = original(rows, kind)
        if result is not None:
            result['total'] /= np.sqrt(3)
        return result

    monkeypatch.setattr(g, 'rmse', wrong)
    report = run_checks(ROOT)
    assert not report['passed']
    assert any(row['status'] == 'FAIL' and 'Control RMSE' in row['name'] for row in report['checks'])


@pytest.mark.parametrize('bundle', [False, True])
@pytest.mark.parametrize('change_kind', ['reference', 'observation'])
def test_real_adjustment_ignores_check_reference_and_observations(tmp_path, bundle, change_kind):
    from test_dense_mesh_gcp import synthetic_model
    from test_numerical_reference_104 import independent_uv

    model = synthetic_model(n_img=4, n_pts=60, two_cameras=False)
    # Pinhole fixture makes the changed check's expected displacement analytic.
    model.cameras[1].params[3] = 0
    for image in model.images.values():
        xyz = model.points.xyz[image.point3D_ids] @ image.R().T + image.tvec
        image.xys = independent_uv(2, model.cameras[1].params, xyz)
    positions = [[5, -4, 0], [15, 4, 0], [20, -4, 0], [12, 0, 1]]
    offset = np.array([500000., 4500000., 100.])
    outputs = []
    for changed in (False, True):
        markers = []
        for index, point in enumerate(np.asarray(positions, float)):
            observations = {}
            for image in model.images.values():
                uv = independent_uv(2, model.cameras[1].params, (point @ image.R().T + image.tvec)[None])[0]
                if changed and index == 3 and change_kind == 'observation':
                    uv = uv + [10, -7]
                observations[image.name] = [*uv, True]
            reference = point+offset
            if index == 3:
                reference = reference + ([100, -80, 60] if changed and change_kind == 'reference' else [4, -3, 12])
            markers.append(g.Marker(str(index), reference.tolist(), enabled=index < 3,
                                    projections=observations).to_dict())
        folder = tmp_path/str(changed)
        cio.write_model(str(folder), model)
        result = g.run_task(dict(model=str(folder), crs='LOCAL', markers=markers,
                                 use_markers=True, use_cameras=False, bundle=bundle,
                                 offset=offset.tolist(), fit_intrinsics=False), log=lambda *_: None)
        outputs.append((result, cio.read_model(str(folder))))
    first, second = outputs
    np.testing.assert_allclose(first[0]['similarity'], second[0]['similarity'], rtol=0, atol=1e-10)
    np.testing.assert_allclose(first[1].points.xyz, second[1].points.xyz, rtol=0, atol=1e-10)
    for key in model.images:
        np.testing.assert_allclose(first[1].images[key].tvec, second[1].images[key].tvec, rtol=0, atol=1e-10)
        np.testing.assert_allclose(first[1].images[key].qvec, second[1].images[key].qvec, rtol=0, atol=1e-10)
    assert first[0]['control_rmse']['n'] == second[0]['control_rmse']['n'] == 3
    assert first[0]['check_rmse']['n'] == second[0]['check_rmse']['n'] == 1
    assert first[0]['check_rmse']['total'] == pytest.approx(13, abs=1e-5, rel=0)
    # At depth 49 and focal length 500, shifting all nadir observations by
    # (+10,-7) pixels moves the triangulated point by (+.98,+.686,0) metres.
    expected = np.sqrt(100**2+80**2+60**2) if change_kind == 'reference' else np.sqrt(3.02**2+3.686**2+12**2)
    assert second[0]['check_rmse']['total'] == pytest.approx(expected, abs=1e-5, rel=0)
