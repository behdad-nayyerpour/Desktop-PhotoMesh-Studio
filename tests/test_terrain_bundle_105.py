import numpy as np
import pytest
from photomesh.plycodec import PlyDocument, PlyElement
from photomesh.workflow import vertex_blocks
from photomesh.ground import classify_cloud
from photomesh.las_export import export_las


def cloud(path):
    x, y = np.meshgrid(np.arange(21), np.arange(21))
    points = np.empty(x.size, dtype=[('x', 'f8'), ('y', 'f8'), ('z', 'f8'),
        ('red', 'u1'), ('green', 'u1'), ('blue', 'u1'), ('confidence', 'f4')])
    points['x'], points['y'] = x.ravel(), y.ravel()
    points['z'] = .03 * points['x']
    roof = (points['x'] >= 8) & (points['x'] <= 12) & (points['y'] >= 8) & (points['y'] <= 12)
    points['z'][roof] += 5
    points['red'], points['green'], points['blue'] = 255, 128, 0
    points['confidence'] = np.linspace(0, 1, len(points))
    PlyDocument([PlyElement.describe(points, 'vertex')]).write(str(path))
    return points, roof


def test_ground_labels_preserve_other_attributes_and_source(tmp_path):
    src, dst = tmp_path / 'input.ply', tmp_path / 'classified.ply'
    original, roof = cloud(src)
    before = src.read_bytes()
    result = classify_cloud(src, dst, cell_size=1, max_radius=8)
    records = np.concatenate(list(vertex_blocks(dst)))
    assert np.all(records['classification'][roof] == 1)
    assert np.mean(records['classification'][~roof] == 2) > .98
    for name in original.dtype.names:
        np.testing.assert_array_equal(records[name], original[name])
    assert src.read_bytes() == before and result['ground'] + result['non_ground'] == len(original)


@pytest.mark.parametrize('extension', ['las', 'laz'])
def test_streaming_las_laz_preserves_world_class_color_and_extra(tmp_path, extension):
    if extension == 'laz':
        import sys
        if sys.platform != 'win32':
            pytest.importorskip('lazrs')
    from photomesh.survey_deps import laspy as dependency
    laspy = dependency()
    src, classified = tmp_path / 'input.ply', tmp_path / 'classified.ply'
    original, roof = cloud(src)
    classify_cloud(src, classified, max_radius=8)
    dst = tmp_path / ('export.' + extension)
    geo = {'offset': [500000, 4500000, 100], 'crs': 'EPSG:32638', 'crs_kind': 'utm'}
    assert export_las(classified, dst, geo, precision=.001) == len(original)
    result = laspy.read(dst)
    for axis, offset in zip('xyz', geo['offset']):
        np.testing.assert_allclose(getattr(result, axis), original[axis] + offset, atol=.00051, rtol=0)
    assert result.header.parse_crs().to_epsg() == 32638
    assert np.all(result.classification[roof] == 1)
    assert np.all(result.red == 65535) and np.all(result.green == 128 * 257)
    np.testing.assert_array_equal(result.confidence, original['confidence'])


def test_cancel_never_replaces_existing_classification(tmp_path):
    src, dst = tmp_path / 'input.ply', tmp_path / 'classified.ply'
    cloud(src)
    dst.write_bytes(b'previous product')
    with pytest.raises(InterruptedError):
        classify_cloud(src, dst, cancel=lambda: True)
    assert dst.read_bytes() == b'previous product'


def test_dtm_uses_only_classified_ground_and_retains_real_coverage(tmp_path):
    from photomesh.dem_engine import build_dem
    from photomesh.geotiff import TiffReader
    src, classified = tmp_path / 'input.ply', tmp_path / 'classified.ply'
    cloud(src)
    classify_cloud(src, classified, max_radius=8)
    geo = {'offset': [500000, 4500000, 100], 'crs': 'EPSG:32638', 'crs_kind': 'utm'}
    base = dict(cloud=str(classified), georef=geo, pixel_size=1., interpolation='Disabled')
    dsm = build_dem(dict(base, out_dir=str(tmp_path / 'dsm')), log=lambda *_: None)
    dtm = build_dem(dict(base, out_dir=str(tmp_path / 'dtm'), ground_only=True), log=lambda *_: None)
    assert dsm['surface_type'] == 'DSM' and dtm['surface_type'] == 'DTM'
    assert dsm['path'] != dtm['path']
    with TiffReader(dsm['path']) as reader:
        surface = reader.read_level(0)[..., 0]
    with TiffReader(dtm['path']) as reader:
        terrain = reader.read_level(0)[..., 0]
    assert surface.max() > 104 and terrain[terrain != -32767].max() < 102
    with TiffReader(dtm['coverage_path']) as reader:
        mask = reader.read_level(0)[..., 0]
    assert dtm['filled_cells'] == 0 and np.all(mask[terrain == -32767] == 0)
