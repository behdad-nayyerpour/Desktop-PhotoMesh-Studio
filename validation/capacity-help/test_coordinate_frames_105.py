import numpy as np
import pytest
from photomesh.coordinates import geographic_to_enu, enu_to_geographic, make_enu_frame, frame_basis
from photomesh import georef as g
from photomesh.workflow import processing_crs


def test_enu_roundtrip_and_independent_ecef_reference():
    pyproj = pytest.importorskip('pyproj')
    frame = {'kind': 'enu', 'origin': [44.5, 40.2, 1200.]}
    xyz = np.array([[44.5, 40.2, 1200.], [44.501, 40.201, 1203.]])
    transform = pyproj.Transformer.from_crs(4979, 4978, always_xy=True)
    independent = np.column_stack(transform.transform(*xyz.T))
    origin, basis = frame_basis(frame)
    local = geographic_to_enu(xyz, frame)
    np.testing.assert_allclose(local, (independent - origin) @ basis.T, atol=2e-8)
    np.testing.assert_allclose(enu_to_geographic(local, frame), xyz, atol=1e-8)
    np.testing.assert_allclose(local[0], 0, atol=1e-9)
    assert processing_crs({'crs': 'EPSG:4326', 'coordinate_frame': frame}).startswith('LOCAL_CS[')
    assert processing_crs({'crs': 'WGS 84 / UTM zone 38N'}) == 'EPSG:32638'


def test_ecef_inverse_at_poles_and_dateline_origin():
    lat = np.array([90., -90., 0., 80.])
    lon = np.array([20., -10., 179.999, -170.])
    height = np.array([10., 100., 200., 300.])
    decoded = g.ecef_to_geodetic(g.geodetic_to_ecef(lat, lon, height))
    np.testing.assert_allclose(decoded[0], lat, atol=1e-10)
    np.testing.assert_allclose(decoded[2], height, atol=1e-7)
    frame = make_enu_frame([[179.999, 30, 100], [-179.999, 30, 100]])
    assert abs(frame['origin'][0]) > 179.9


def test_enu_frame_preserved_in_shapes_and_tiles():
    from photomesh.project import ProjectData
    from photomesh.shapes import Frame, SrcCRS
    from photomesh.tiles import _root_transform
    frame = {'kind': 'enu', 'origin': [44.5, 40.2, 1200.]}
    ch = ProjectData(crs='EPSG:4326', georef={'crs': 'EPSG:4326', 'crs_kind': 'wgs84',
        'coordinate_frame': frame, 'offset': [10, 20, 30]})
    project = Frame.from_dataset(ch)
    src = SrcCRS('wgs84')
    xyz = np.array([[44.501, 40.201, 1203.]])
    local = project.from_src(xyz, src)
    np.testing.assert_allclose(project.to_dst(local, src), xyz, atol=1e-8)
    matrix, _center = _root_transform(ch.georef, [0, 0, 0])
    matrix = np.array(matrix).reshape(4, 4).T
    origin, basis = frame_basis(frame)
    np.testing.assert_allclose(matrix[:3, 3], origin + basis.T @ [10, 20, 30])


def test_actual_enu_adjustment_preserves_reference_frame_and_independent_errors(tmp_path):
    from test_dense_mesh_gcp import synthetic_model
    from photomesh import colmap_io as cio
    model = synthetic_model(n_img=5, n_pts=100, two_cameras=False)
    frame = {'kind': 'enu', 'origin': [44.5, 40.2, 1200.]}
    points = np.array([[0, 0, 0], [3, 0, 0], [0, 3, 0], [3, 3, 1]], float)
    references = enu_to_geographic(points, frame)
    markers = []
    for i, (point, reference) in enumerate(zip(points, references)):
        projections = {}
        for image in model.images.values():
            uv, _ = cio.project(model.cameras[image.camera_id], image.R(), image.tvec, point[None])
            camera = model.cameras[image.camera_id]
            if 0 <= uv[0, 0] < camera.width and 0 <= uv[0, 1] < camera.height:
                projections[image.name] = [*uv[0], True]
        markers.append(g.Marker(str(i), reference.tolist(), projections=projections).to_dict())
    folder = str(tmp_path / 'model')
    cio.write_model(folder, model)
    result = g.run_task(dict(model=folder, markers=markers, crs='EPSG:4326',
        adjustment_frame='enu', coordinate_frame=frame, marker_height_reference='ellipsoidal',
        use_markers=True, use_cameras=False, bundle=False), log=lambda *_: None)
    assert result['coordinate_frame'] == frame
    assert result['control_rmse']['total'] < 1e-5
    np.testing.assert_allclose(result['similarity'], np.eye(4), atol=1e-5)
    before = (tmp_path / 'model/images.bin').read_bytes()
    gps = {image.name: enu_to_geographic(image.center()[None], frame)[0].tolist()
           for image in model.images.values()}
    with pytest.raises(ValueError, match='height references'):
        g.run_task(dict(model=folder, markers=markers, crs='EPSG:4326',
            use_markers=True, use_cameras=True, camera_gps=gps, strict_heights=True), log=lambda *_: None)
    assert (tmp_path / 'model/images.bin').read_bytes() == before


def test_projected_crs_and_gps_do_not_assume_utm_or_feet():
    projected = g.CRS.parse('EPSG:3857')
    assert projected.kind == 'proj'
    with pytest.raises(ValueError, match='metre'):
        g.CRS.parse('EPSG:2263')
    with pytest.raises(ValueError, match='Compound'):
        g.CRS.parse('COMPOUNDCRS["WGS 84 + EGM96 height",GEOGCRS["WGS 84"],VERTCRS["EGM96 height"]]')


def test_incompatible_height_diagnostic_keeps_pixels_without_inventing_xyz_rmse():
    from test_dense_mesh_gcp import synthetic_model
    from photomesh import colmap_io as cio
    model = synthetic_model(n_img=5, n_pts=80, two_cameras=False)
    point = np.array([1., 1., 0.])
    projections = {}
    for image in model.images.values():
        camera = model.cameras[image.camera_id]
        uv, depth = cio.project(camera, image.R(), image.tvec, point[None])
        if depth[0] > 0 and 0 <= uv[0, 0] < camera.width and 0 <= uv[0, 1] < camera.height:
            projections[image.name] = [*uv[0], True]
    marker = g.Marker('check', [1., 1., 100.], enabled=False, projections=projections)
    estimates, pixels, counts, rows = g.marker_diagnostics(model, [marker], g.CRS.parse('Local'), compare_heights=False)
    assert counts['check'] >= 2 and pixels['check'] < 1e-6
    np.testing.assert_allclose(estimates['check'], point, atol=1e-6)
    assert rows == [] and g.rmse(rows, 'check') is None
