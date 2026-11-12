"""One project-wide photo GPS policy, separate from photo alignment inclusion."""
from .georef import valid_gps


def use_photo_gps(dataset):
    settings = dataset.reference_settings or {}
    if "use_photo_gps" in settings:
        return bool(settings["use_photo_gps"])
    # Preserve legacy opt-outs conservatively until the user selects the new policy.
    if settings.get("use_cameras") is False:
        return False
    return not any(not camera.use_reference and
                   valid_gps((camera.lon, camera.lat, camera.alt)) is not None
                   for camera in dataset.cameras)


def camera_gps(dataset, names=None):
    if not use_photo_gps(dataset):
        return {}
    if names is None:
        from .photonames import photo_map
        mapping, _ambiguous = photo_map(dataset)
        names = {path: name for name, path in mapping.items()}
    result = {}
    for camera in dataset.cameras:
        if not camera.enabled:
            continue
        xyz = valid_gps((camera.lon, camera.lat, camera.alt))
        name = names.get(camera.path)
        if xyz is not None and name:
            result[name] = xyz.tolist()
    return result


def camera_accuracies(dataset, names=None):
    """Explicit opt-in reported E/N/up sigmas; never infer accuracy from RTK flag alone."""
    if not use_photo_gps(dataset) or not dataset.reference_settings.get('reported_gps_accuracy', False):
        return {}
    if names is None:
        from .photonames import photo_map
        mapping, _ambiguous = photo_map(dataset)
        names = {path: name for name, path in mapping.items()}
    result = {}
    for camera in dataset.cameras:
        values = reported_accuracy(camera)
        if not camera.enabled or not names.get(camera.path) or values is None:
            continue
        result[names[camera.path]] = values
    return result


def reported_accuracy(camera):
    import math
    values = camera.gps_accuracy
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return None
    if all(isinstance(value, (int, float)) and math.isfinite(value) and .0001 <= value <= 10000 for value in values):
        return list(values)
    return None
