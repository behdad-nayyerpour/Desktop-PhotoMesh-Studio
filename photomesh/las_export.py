"""Bounded-memory LAS 1.4 / LAZ export with explicit precision and CRS."""
import json
import os
import tempfile
import numpy as np

from .workflow import vertex_blocks, bounds_from_ply, processing_crs, source_unit


def export_las(source, destination, georef=None, precision=.001, progress=None, cancel=None):
    from .survey_deps import laspy as dependency
    laspy = dependency()
    if os.path.normcase(os.path.abspath(source)) == os.path.normcase(os.path.abspath(destination)):
        raise ValueError('LAS export destination must differ from the source point cloud')
    georef = georef or {}
    from .workflow import file_stamp
    source_stamp = file_stamp(source)
    if not np.isfinite(precision) or precision <= 0:
        raise ValueError('LAS coordinate precision must be positive and finite')
    offset = np.asarray(georef.get('offset') or [0, 0, 0], dtype=float)
    if offset.shape != (3,) or not np.isfinite(offset).all():
        raise ValueError('Invalid model coordinate offset')
    low, high = bounds_from_ply(source)
    middle = low + (high - low) / 2 + offset
    origin = np.round(middle / precision) * precision
    if np.max(np.maximum(abs(low + offset - origin), abs(high + offset - origin)) / precision) >= 2**31 - 1:
        raise ValueError('Cloud extent exceeds LAS integer range at this precision; choose a larger precision value')
    first = next(iter(vertex_blocks(source)))
    names = first.dtype.names
    has_rgb = all(name in names for name in ('red', 'green', 'blue'))
    header = laspy.LasHeader(point_format=7 if has_rgb else 6, version='1.4')
    header.scales = [precision] * 3
    header.offsets = origin
    crs = processing_crs(georef)
    if crs and not crs.upper().startswith('LOCAL'):
        from pyproj import CRS
        header.add_crs(CRS.from_user_input(crs))
    header.vlrs.append(laspy.VLR(user_id='Lens2Mesh', record_id=1,
        description='Coordinate provenance', record_data=json.dumps({
            'units': source_unit(georef), 'crs': crs, 'precision': precision,
            'coordinate_frame': georef.get('coordinate_frame'),
            'height_axis': 'ENU Up relative to tangent origin' if georef.get('coordinate_frame') else georef.get('height_reference', 'unknown'),
            'height_reference': georef.get('height_reference', 'unknown')}).encode('utf-8')))
    reserved = set(header.point_format.dimension_names)
    extras = [name for name in names if name not in {'x', 'y', 'z', 'red', 'green', 'blue', 'classification'}]
    for name in extras:
        target = name if name not in reserved else 'source_' + name
        if len(target.encode('utf-8')) > 32:
            raise ValueError(f'LAS attribute name exceeds 32 bytes: {target}')
        header.add_extra_dim(laspy.ExtraBytesParams(name=target, type=first.dtype[name].newbyteorder('=')))
    folder = os.path.dirname(os.path.abspath(destination))
    fd, temporary = tempfile.mkstemp(prefix='.lens2mesh-las-', suffix=os.path.splitext(destination)[1], dir=folder)
    os.close(fd)
    total = 0
    try:
        with laspy.open(temporary, mode='w', header=header,
                        do_compress=str(destination).lower().endswith('.laz')) as writer:
            for records in vertex_blocks(source):
                if cancel and cancel():
                    raise InterruptedError('LAS export cancelled')
                points = laspy.ScaleAwarePointRecord.zeros(len(records), header=header)
                for i, axis in enumerate('xyz'):
                    values = records[axis].astype(float) + offset[i]
                    if not np.isfinite(values).all():
                        raise ValueError('LAS export requires finite coordinates')
                    setattr(points, axis, values)
                if has_rgb:
                    for name in ('red', 'green', 'blue'):
                        values = records[name]
                        if not np.isfinite(values).all() or values.min() < 0 or values.max() > 65535:
                            raise ValueError('RGB values must be in 0..65535')
                        points[name] = values.astype(np.uint16) * (257 if values.dtype.itemsize == 1 else 1)
                if 'classification' in names:
                    labels = records['classification']
                    if not np.isfinite(labels).all() or labels.min() < 0 or labels.max() > 255 or np.any(labels != np.floor(labels)):
                        raise ValueError('LAS class labels must be integer values in 0..255')
                    points.classification = labels.astype(np.uint8)
                for name in extras:
                    target = name if name not in reserved else 'source_' + name
                    points[target] = records[name]
                writer.write_points(points)
                total += len(records)
                if progress:
                    progress(total, 0, f'Exported {total:,} points')
        if cancel and cancel():
            raise InterruptedError('LAS export cancelled')
        if file_stamp(source) != source_stamp:
            raise ValueError('Source point cloud changed during export; previous destination retained')
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return total
