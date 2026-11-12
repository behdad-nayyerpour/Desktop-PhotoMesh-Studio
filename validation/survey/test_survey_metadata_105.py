import pytest
from photomesh.exif import rational, coordinates
from photomesh.calibration import intrinsic_indices, camera_model_arguments


@pytest.mark.parametrize("value", [(1, 0), (), "bad", None, float("nan"), float("inf")])
def test_corrupt_rational_is_never_a_plausible_zero(value):
    with pytest.raises(ValueError):
        rational(value)


def test_gps_rejects_partial_corruption_and_keeps_real_zero():
    tags = {1: "N", 2: ((0, 1), (0, 1), (0, 1)),
            3: b"W", 4: (0, 0, 0), 5: b"\x01", 6: (12, 1)}
    assert coordinates(tags) == (0, 0, -12)
    tags[2] = ((1, 0), 0, 0)
    assert coordinates(tags) == (None, None, None)
    tags[2] = (91, 0, 0)
    assert coordinates(tags) == (None, None, None)


def test_intrinsic_presets_fit_only_named_coefficients():
    assert intrinsic_indices(5, "f,cx,cy,k1-k3,p1,p2") == [0, 1, 2, 3, 4, 5, 6]
    assert intrinsic_indices(6, "f,cx,cy,k1-k3,p1,p2") == [0, 1, 2, 3, 4, 5, 8, 6, 7]
    assert intrinsic_indices(4, "f,cx,cy,k1-k3,p1,p2") == list(range(8))
    assert camera_model_arguments({}) == []
    assert camera_model_arguments({"camera_model": "OPENCV"}) == ["--ImageReader.camera_model", "OPENCV"]
    with pytest.raises(ValueError):
        camera_model_arguments({"camera_model": "unknown"})
