"""Progressive morphological ground classification of a scalar PLY point cloud.

Ground is a lower-envelope estimate, not a surveyed surface. Settings are in
the source coordinate units; interpolation of empty raster cells is internal
to the classifier and never creates new points.
"""
from pathlib import Path
import numpy as np

from .workflow import vertex_blocks, file_stamp


def classify_cloud(source, destination, cell_size=1., slope=.15, initial_height=.2,
                   max_height=2., max_radius=16, progress=None, cancel=None, rotation=None):
    from scipy.ndimage import grey_opening, distance_transform_edt
    from .plyio import read_header, is_list_property
    from .export import atomic_write
    from .memguard import require_available_bytes
    from .plycodec import _type_name
    source_stamp = file_stamp(source)
    if Path(source).resolve() == Path(destination).resolve():
        raise ValueError("Classification output must be a new product")
    values = [cell_size, slope, initial_height, max_height]
    if not np.isfinite(values).all() or cell_size <= 0 or min(slope, initial_height) < 0 or max_height < initial_height:
        raise ValueError("Invalid ground-classification thresholds")
    if not 1 <= int(max_radius) <= 128:
        raise ValueError("Maximum window radius must be 1 to 128 cells")
    with open(source, 'rb') as fh:
        header = read_header(fh)
    if not header or len(header[2]) != 1 or header[2][0][0] != 'vertex':
        raise ValueError("Classification requires a point cloud with a scalar vertex element only")
    _, count, properties = header[2][0]
    if any(p is None or is_list_property(p) for p in properties):
        raise ValueError("Point-cloud list attributes are not supported by classification")
    dtype = np.dtype(properties).newbyteorder('<')
    if 'classification' in dtype.names:
        if dtype['classification'].kind not in 'iu':
            raise ValueError("Existing classification must be an integer attribute")
    else:
        dtype = np.dtype(dtype.descr + [('classification', 'u1')])
    rotation = np.eye(3) if rotation is None else np.asarray(rotation, float)
    if rotation.shape != (3, 3) or not np.isfinite(rotation).all() or not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-8) or np.linalg.det(rotation) < 0:
        raise ValueError('Classification up-frame must be a proper rotation')
    def xyz(records):
        points = np.column_stack([records[axis] for axis in 'xyz']).astype(float)
        if not np.isfinite(points).all():
            raise ValueError('Point cloud contains nonfinite coordinates')
        return points @ rotation.T
    low, high = np.full(3, np.inf), np.full(3, -np.inf)
    for records in vertex_blocks(source):
        if cancel and cancel():
            raise InterruptedError('Classification cancelled')
        points = xyz(records)
        if len(points):
            low, high = np.minimum(low, points.min(0)), np.maximum(high, points.max(0))
    if not count or not np.isfinite([low, high]).all():
        raise ValueError('Point cloud has no finite points')
    extent = (high[:2] - low[:2]) / cell_size
    if not np.isfinite(extent).all() or np.max(extent) > 8_000_000:
        raise ValueError('Classification grid is too large; increase cell size or crop the source')
    size = np.floor(extent).astype(np.int64) + 1
    width, height = map(int, size)
    if width * height > min(8_000_000, require_available_bytes() // 128):
        raise ValueError("Classification grid is too large; increase cell size or crop the source")
    def report(done, text):
        if cancel and cancel():
            raise InterruptedError('Classification cancelled')
        if progress:
            progress(done, 100, text)
    def cells(records):
        points = xyz(records)
        ij = np.floor((points[:, :2] - low[:2]) / cell_size).astype(np.int64)
        return ij[:, 1], ij[:, 0], points[:, 2]
    surface = np.full((height, width), np.inf)
    processed = 0
    for records in vertex_blocks(source):
        row, col, z = cells(records)
        np.minimum.at(surface, (row, col), z - low[2])
        processed += len(records)
        report(30 * processed / count, 'Reading lower elevation envelope')
    occupied = np.isfinite(surface)
    nearest = distance_transform_edt(~occupied, return_distances=False, return_indices=True)
    surface = surface[tuple(nearest)]
    del nearest
    ground_cells = occupied.copy()
    radii = []
    radius = 1
    while radius < max_radius:
        radii.append(radius)
        radius *= 2
    radii.append(int(max_radius))
    last = 0
    for i, radius in enumerate(radii):
        opened = grey_opening(surface, size=(2 * radius + 1, 2 * radius + 1), mode='nearest')
        threshold = min(max_height, initial_height + slope * cell_size * (radius - last))
        # Each progressive threshold applies to this opening, not the
        # cumulative change since the original grid. Cumulative differences
        # incorrectly reject a gradual slope near a padded grid boundary.
        ground_cells &= surface - opened <= threshold
        surface = opened
        last = radius
        report(30 + 30 * (i + 1) / len(radii), 'Separating ground and above-ground objects')
    comments = [line for line in header[0].splitlines() if line.startswith((b'comment ', b'obj_info '))]
    lines = []
    lines += ['comment Lens2Mesh ground=2 non-ground=1', f'element vertex {count}']
    lines += [f'property {_type_name(dtype[name])} {name}' for name in dtype.names]
    lines += ['end_header']
    counts = {1: 0, 2: 0}
    processed = 0
    with atomic_write(destination) as out:
        out.write(b'ply\nformat binary_little_endian 1.0\n' +
                  b''.join(line + b'\n' for line in comments) + ('\n'.join(lines) + '\n').encode('ascii'))
        for records in vertex_blocks(source):
            row, col, z = cells(records)
            final_tolerance = min(max_height, initial_height + slope * cell_size * int(max_radius))
            labels = np.where(ground_cells[row, col] &
                              (z - low[2] - surface[row, col] <= final_tolerance), 2, 1)
            result = np.empty(len(records), dtype=dtype)
            for name in records.dtype.names:
                result[name] = records[name]
            result['classification'] = labels
            counts[2] += int(np.count_nonzero(labels == 2))
            counts[1] += int(np.count_nonzero(labels == 1))
            out.write(result.tobytes())
            processed += len(records)
            report(60 + 40 * processed / count, 'Writing classified cloud')
        if file_stamp(source) != source_stamp:
            raise ValueError('Source point cloud changed during classification; no product published')
    return {'path': str(destination), 'ground': counts[2], 'non_ground': counts[1],
            'cell_size': cell_size, 'slope': slope, 'initial_height': initial_height,
            'max_height': max_height, 'max_radius': max_radius, 'rotation': rotation.tolist()}


CLASS_COLORS = {1: (0.85, 0.55, 0.2, 1.), 2: (0.2, 0.75, 0.3, 1.)}


def class_colors(labels):
    colors = np.full((len(labels), 4), .65, dtype=np.float32)
    colors[:, 3] = 1.
    for key, color in CLASS_COLORS.items():
        colors[np.asarray(labels) == key] = color
    return colors
