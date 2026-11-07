"""Model-preserving calibration for bundle adjustment; projection uses COLMAP I/O's canonical model."""
import numpy as np
from . import colmap_io as cio


def intrinsic_indices(model, preset):
    if preset == "none":
        return []
    if preset not in ("f", "f,cx,cy,k1", "f,cx,cy,k1-k3", "f,cx,cy,k1-k3,p1,p2"):
        raise ValueError(f"Unsupported intrinsic fit preset: {preset}")
    simple = model in (0, 2, 3)
    result = [0] if simple else [0, 1]
    if preset == "f":
        return result
    result += [1, 2] if simple else [2, 3]
    radial = {0: [], 1: [], 2: [3], 3: [3,4], 4: [4,5],
              5: [4,5,6,7], 6: [4,5,8]}[model]
    if preset == "f,cx,cy,k1":
        return result + radial[:1]
    result += radial[:3]
    if preset == "f,cx,cy,k1-k3,p1,p2":
        if model in (4,6):
            result += [6,7]
        if model == 5:
            result += [7]
        if model == 6:
            result += [9,10,11]
    return result


def pack_calibrations(cameras, preset="none"):
    params = np.zeros((len(cameras), 12), float)
    model_ids = np.array([camera.model for camera in cameras], int)
    selections = []
    for row, camera in enumerate(cameras):
        if camera.model not in cio.CAMERA_MODELS:
            raise ValueError(f"Unsupported camera model: {camera.model}")
        size = cio.CAMERA_MODELS[camera.model][1]
        values = np.asarray(camera.params, float)
        if values.shape != (size,) or not np.isfinite(values).all():
            raise ValueError(f"Invalid calibration for {camera.name}")
        fx, fy, _cx, _cy = camera.K()
        if min(fx, fy) <= 0:
            raise ValueError("Camera focal lengths must be positive")
        params[row, :size] = values
        selections.append(intrinsic_indices(camera.model, preset))
    width = max(map(len, selections), default=0)
    indices = np.zeros((len(cameras), width), int)
    active = np.zeros_like(indices, bool)
    for row, selected in enumerate(selections):
        indices[row, :len(selected)] = selected
        active[row, :len(selected)] = True
    return params, model_ids, indices, active


def project_calibrations(params, model_ids, xyz_camera):
    result = np.empty((len(xyz_camera), 2), float)
    for kind in np.unique(model_ids):
        mask = model_ids == kind
        size = cio.CAMERA_MODELS[int(kind)][1]
        # Camera accessors and distortion support row arrays, avoiding a
        # second simplified Brown/fisheye implementation in the optimizer.
        camera = cio.Camera(int(kind), 0, 0, params[mask, :size].T)
        result[mask] = cio.project(camera, np.eye(3), np.zeros(3), xyz_camera[mask])[0]
    return result


def apply_increment(params, indices, active, increment):
    result = params.copy()
    for row in range(len(params)):
        result[row, indices[row, active[row]]] += increment[row, active[row]]
    return result
