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
