"""Explicit WGS84 local tangent frames; no implicit geoid/height conversion."""
import numpy as np


def frame_basis(frame):
    from .georef import geodetic_to_ecef, enu_basis
    origin = np.asarray(frame.get('origin'), float)
    if frame.get('kind') != 'enu' or origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError('Invalid ENU origin')
    lon, lat, height = origin
    if abs(lon) > 180 or abs(lat) > 90:
        raise ValueError('ENU origin longitude/latitude is outside its domain')
    return geodetic_to_ecef(lat, lon, height), enu_basis(lat, lon)


def geographic_to_enu(xyz, frame):
    from .georef import geodetic_to_ecef
    xyz = np.atleast_2d(np.asarray(xyz, float))
    if xyz.shape[1] != 3 or not np.isfinite(xyz).all() or np.any(abs(xyz[:, 0]) > 180) or np.any(abs(xyz[:, 1]) > 90):
        raise ValueError('Invalid geographic reference coordinates')
    origin, basis = frame_basis(frame)
    return (geodetic_to_ecef(xyz[:, 1], xyz[:, 0], xyz[:, 2]) - origin) @ basis.T


def enu_to_geographic(xyz, frame):
    from .georef import ecef_to_geodetic
    origin, basis = frame_basis(frame)
    xyz = np.atleast_2d(np.asarray(xyz, float))
    if xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError('Invalid ENU coordinates')
    lat, lon, height = ecef_to_geodetic(xyz @ basis + origin)
    return np.column_stack([lon, lat, height])


def make_enu_frame(geographic):
    from .georef import geodetic_to_ecef, ecef_to_geodetic
    xyz = np.asarray(geographic, float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not len(xyz) or not np.isfinite(xyz).all():
        raise ValueError('ENU adjustment needs valid WGS84 references')
    center = geodetic_to_ecef(xyz[:, 1], xyz[:, 0], xyz[:, 2]).mean(0)
    if np.linalg.norm(center) < 1e6:
        raise ValueError('References do not define a usable local tangent origin')
    lat, lon, _height = ecef_to_geodetic(center)
    return {'kind': 'enu', 'origin': [float(lon[0]), float(lat[0]), float(xyz[:, 2].mean())],
            'height_reference': 'ellipsoidal', 'axes': 'East, North, Up'}


def enu_wkt(frame):
    frame_basis(frame)
    lon, lat, height = frame['origin']
    return (f'LOCAL_CS["WGS84 ENU origin {lon:.12g} {lat:.12g} {height:.12g}",'
            'LOCAL_DATUM["WGS84 tangent plane",0],UNIT["metre",1],'
            'AXIS["East",EAST],AXIS["North",NORTH],AXIS["Up",UP]]')


def gps_accuracy_in_frame(xyz, accuracy, crs, zone=None, frame=None):
    """Propagate local E/N/up sigma through the adjustment-frame Jacobian.

    Bundle adjustment accepts diagonal sigmas. Reported physical receiver axes
    are rotated/projected first; they are not mistaken for unscaled grid axes.
    """
    from .georef import geodetic_to_ecef, ecef_to_geodetic, enu_basis, CRS
    lon, lat, height = np.asarray(xyz, float)
    sigma = np.asarray(accuracy, float)
    if sigma.shape != (3,) or not np.isfinite(sigma).all() or np.any(sigma <= 0):
        raise ValueError('Photo GPS standard deviations must be finite and positive')
    center = geodetic_to_ecef(lat, lon, height)
    basis = enu_basis(lat, lon)
    earth = np.concatenate([center + basis, center - basis])
    latitude, longitude, elevation = ecef_to_geodetic(earth)
    geographic = np.column_stack([longitude, latitude, elevation])
    if frame:
        target = geographic_to_enu(geographic, frame)
    elif crs.kind == 'proj':
        from pyproj import Transformer
        target = np.column_stack(Transformer.from_crs(4326, crs.name, always_xy=True).transform(*geographic.T))
    else:
        selected_zone = (crs.zone, crs.south) if crs.kind == 'utm' else zone
        target = CRS.parse('EPSG:4326').to_metric(geographic, selected_zone)
    jacobian = ((target[:3] - target[3:]) / 2).T
    result = np.sqrt(np.square(jacobian) @ np.square(sigma))
    if not np.isfinite(result).all() or np.any(result <= 0):
        raise ValueError('Photo GPS accuracy cannot be transformed into this frame')
    return result
