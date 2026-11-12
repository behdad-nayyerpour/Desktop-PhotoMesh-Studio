import numpy as np
from photomesh.exif import photo_metadata
from photomesh.photo_gps import camera_accuracies
from photomesh.project import ProjectData, Camera
from photomesh.coordinates import gps_accuracy_in_frame
from photomesh.georef import CRS


def test_xmp_fallback_and_opt_in_accuracy_are_explicit():
    class Photo:
        def getexif(self):
            return {}
        info = {'xmp': b'''<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:d="http://www.dji.com/drone-dji/1.0/">
        <d:photo d:GpsLongitude="44.5" d:GpsLatitude="40.2" d:AbsoluteAltitude="1200"
        d:RtkFlag="50" d:RtkStdLon="0.01" d:RtkStdLat="0.02" d:RtkStdHgt="0.03"/></x:xmpmeta>'''}
    result = photo_metadata(Photo())
    assert result['gps_accuracy'] == [.01, .02, .03]
    assert result['gps_metadata']['height_reference'] == 'unknown'
    camera = Camera('a.jpg', lon=result['lon'], lat=result['lat'], alt=result['alt'],
                    gps_accuracy=result['gps_accuracy'])
    dataset = ProjectData(cameras=[camera])
    assert camera_accuracies(dataset, {'a.jpg': 'a.jpg'}) == {}
    dataset.reference_settings['reported_gps_accuracy'] = True
    assert camera_accuracies(dataset, {'a.jpg': 'a.jpg'}) == {'a.jpg': [.01, .02, .03]}
    dataset.reference_settings['use_photo_gps'] = False
    assert camera_accuracies(dataset, {'a.jpg': 'a.jpg'}) == {}


def test_accuracy_rotates_and_scales_to_the_adjustment_frame():
    xyz = [44.5, 40.2, 1200]
    sigma = [.01, .02, .03]
    frame = {'kind': 'enu', 'origin': xyz}
    transformed = gps_accuracy_in_frame(xyz, sigma, CRS.parse('EPSG:4326'), frame=frame)
    np.testing.assert_allclose(transformed, sigma, atol=1e-9)
    grid = gps_accuracy_in_frame(xyz, sigma, CRS.parse('EPSG:3857'))
    assert grid[0] > sigma[0] and grid[1] > sigma[1]
    assert abs(grid[2] - sigma[2]) < 1e-8


def test_failed_dji_position_does_not_become_zero_or_precise_gps():
    class Photo:
        def getexif(self):
            return {}
        info = {'xmp': b'''<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:d="http://www.dji.com/drone-dji/1.0/">
        <d:photo d:GpsLongitude="44.5" d:GpsLatitude="40.2" d:AbsoluteAltitude="1200"
        d:RtkFlag="0" d:RtkStdLon="0.01" d:RtkStdLat="0.02" d:RtkStdHgt="0.03"/></x:xmpmeta>'''}
    result = photo_metadata(Photo())
    assert result['lon'] is None and result['lat'] is None and result['alt'] is None
    assert result['gps_accuracy'] is None
