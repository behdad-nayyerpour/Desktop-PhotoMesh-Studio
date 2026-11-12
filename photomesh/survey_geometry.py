"""Double-precision surface picks and upper-envelope mesh sections.

Profiles use the highest actual intersection with each vertical ray. Empty
columns remain NaN; overhangs/multiple floors are explicitly upper-envelope,
not a claim that every intersection is represented.
"""
import heapq
import math
import numpy as np
from .workflow import require_mesh, vertex_blocks


def load_surface(path, rotation=None, cancel=None):
    from .plyio import read_fast, ply_counts
    from .memguard import require_available_bytes
    vertices, faces = ply_counts(path)
    if vertices * 32 + faces * 256 > require_available_bytes() * .6:
        raise ValueError('Mesh surface and section index exceed available RAM; simplify the mesh')
    data = read_fast(path)
    if data is not None:
        records, triangles = data['vertex'], data['face']
    else:
        from .plycodec import PlyDocument
        document = PlyDocument.read(path)
        records = document['vertex'].data
        polygons = document['face'].data
        key = 'vertex_indices' if 'vertex_indices' in polygons.dtype.names else polygons.dtype.names[0]
        if any(len(face) != 3 for face in polygons[key]):
            raise ValueError('Triangulate the mesh before measurement or cross section')
        triangles = np.asarray(list(polygons[key]), dtype=np.int64)
    if triangles is None:
        raise ValueError('Surface picking requires a triangular mesh')
    points = np.column_stack([records[axis] for axis in 'xyz']).astype(float)
    if rotation is not None:
        points = points @ np.asarray(rotation).T
    return MeshSurface(points, triangles, cancel=cancel)


def distance_components(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != (3,) or b.shape != (3,) or not np.isfinite([a, b]).all():
        raise ValueError('Measurement requires two finite 3D endpoints')
    delta = b - a
    horizontal = float(np.hypot(*delta[:2]))
    return {'delta': delta, 'distance': float(np.linalg.norm(delta)),
            'horizontal': horizontal, 'height': float(delta[2]),
            'slope_percent': 100 * float(delta[2]) / horizontal if horizontal > 1e-12 else None,
            'slope_degrees': math.degrees(math.atan2(float(delta[2]), horizontal)) if horizontal > 1e-12 else None}


class MeshSurface:
    def __init__(self, vertices, faces, cancel=None):
        from .memguard import require_available_bytes
        require_mesh(vertices, faces)
        if len(faces) * 256 > require_available_bytes() * .6:
            raise ValueError('Mesh section index exceeds available RAM; simplify the mesh')
        self.triangles = np.asarray(vertices, float)[faces]
        self.low = self.triangles.min((0, 1))
        self.high = self.triangles.max((0, 1))
        centers = self.triangles.mean(1)
        self.nodes = []
        def build(indices):
            if cancel and cancel():
                raise InterruptedError('Surface indexing cancelled')
            tri = self.triangles[indices]
            low, high = tri.min((0, 1)), tri.max((0, 1))
            index = len(self.nodes)
            self.nodes.append(None)
            if len(indices) <= 48:
                self.nodes[index] = (low, high, indices, None)
            else:
                axis = int(np.argmax(np.ptp(centers[indices], axis=0)))
                split = len(indices) // 2
                order = indices[np.argpartition(centers[indices, axis], split)]
                children = build(order[:split]), build(order[split:])
                self.nodes[index] = (low, high, None, children)
            return index
        build(np.arange(len(faces)))

    @staticmethod
    def _box(origin, direction, low, high):
        near, far = 0., np.inf
        for axis in range(3):
            if abs(direction[axis]) < 1e-15:
                if origin[axis] < low[axis] or origin[axis] > high[axis]:
                    return None
            else:
                a, b = (low[axis] - origin[axis]) / direction[axis], (high[axis] - origin[axis]) / direction[axis]
                near, far = max(near, min(a, b)), min(far, max(a, b))
                if far < near:
                    return None
        return near

    def pick(self, origin, direction):
        origin, direction = np.asarray(origin, float), np.asarray(direction, float)
        if origin.shape != (3,) or direction.shape != (3,) or not np.isfinite([origin, direction]).all() or np.linalg.norm(direction) == 0:
            raise ValueError('Invalid picking ray')
        direction = direction / np.linalg.norm(direction)
        queue = [(0., 0)]
        closest = np.inf
        while queue:
            near, index = heapq.heappop(queue)
            if near > closest:
                continue
            low, high, indices, children = self.nodes[index]
            if children is not None:
                for child in children:
                    node = self.nodes[child]
                    distance = self._box(origin, direction, node[0], node[1])
                    if distance is not None and distance <= closest:
                        heapq.heappush(queue, (distance, child))
                continue
            triangles = self.triangles[indices]
            e1, e2 = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
            h = np.cross(direction, e2)
            determinant = np.einsum('ij,ij->i', e1, h)
            valid = abs(determinant) > 1e-12 * np.maximum(np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1), 1e-30)
            inv = np.divide(1., determinant, out=np.zeros_like(determinant), where=valid)
            s = origin - triangles[:, 0]
            u = np.einsum('ij,ij->i', s, h) * inv
            q = np.cross(s, e1)
            v = q @ direction * inv
            t = np.einsum('ij,ij->i', e2, q) * inv
            valid &= (u >= -1e-10) & (v >= -1e-10) & (u + v <= 1 + 1e-10) & (t >= 0)
            if np.any(valid):
                closest = min(closest, float(t[valid].min()))
        return None if not np.isfinite(closest) else origin + closest * direction

    def section(self, start, end, samples=512, cancel=None):
        start, end = np.asarray(start, float), np.asarray(end, float)
        if start.shape != (2,) or end.shape != (2,) or not np.isfinite([start, end]).all():
            raise ValueError('Section endpoints must have finite X and Y')
        length = float(np.linalg.norm(end - start))
        if length <= 1e-12 or not 2 <= int(samples) <= 4096:
            raise ValueError('Section needs a positive horizontal length and 2..4096 samples')
        # Find coverage intervals in the vertical section plane independently
        # of sampling density. Even a hole narrower than one sample gets NaN.
        direction = (end - start) / length
        normal = np.array([-direction[1], direction[0]])
        intervals = []
        pending = [0]
        epsilon = max(1., length) * 1e-10
        while pending:
            if cancel and cancel():
                raise InterruptedError('Section cancelled')
            low, high, indices, children = self.nodes[pending.pop()]
            nlow = np.minimum((low[:2] - start) * normal, (high[:2] - start) * normal).sum()
            nhigh = np.maximum((low[:2] - start) * normal, (high[:2] - start) * normal).sum()
            ulow = np.minimum((low[:2] - start) * direction, (high[:2] - start) * direction).sum()
            uhigh = np.maximum((low[:2] - start) * direction, (high[:2] - start) * direction).sum()
            if nlow > epsilon or nhigh < -epsilon or uhigh < 0 or ulow > length:
                continue
            if children is not None:
                pending.extend(children)
                continue
            for triangle in self.triangles[indices]:
                xy = triangle[:, :2] - start
                signed = xy @ normal
                projected = xy @ direction
                hits = list(projected[abs(signed) <= epsilon])
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    if signed[a] * signed[b] < 0:
                        fraction = signed[a] / (signed[a] - signed[b])
                        hits.append(projected[a] + fraction * (projected[b] - projected[a]))
                if hits:
                    lo, hi = max(0., min(hits)), min(length, max(hits))
                    if hi >= lo:
                        intervals.append((lo, hi))
        merged = []
        for lo, hi in sorted(intervals):
            if merged and lo <= merged[-1][1] + epsilon:
                merged[-1] = merged[-1][0], max(merged[-1][1], hi)
            else:
                merged.append((lo, hi))
        breaks = [value for interval in merged for value in interval]
        gaps = [(a[1] + b[0]) / 2 for a, b in zip(merged, merged[1:]) if b[0] > a[1] + epsilon]
        along = np.unique(np.r_[np.linspace(0, length, int(samples)), breaks, gaps])
        if len(along) > 10000:
            raise ValueError('Section has too many disconnected surfaces; shorten the line or simplify the mesh')
        xy = start + (along / length)[:, None] * (end - start)
        z = np.full(len(xy), np.nan)
        top = self.high[2] + max(1., self.high[2] - self.low[2])
        for i, (x, y) in enumerate(xy):
            if cancel and cancel():
                raise InterruptedError('Section cancelled')
            hit = self.pick([x, y, top], [0, 0, -1])
            if hit is not None:
                z[i] = hit[2]
        return along, z


def pick_cloud(source, origin, direction, tolerance=.005, cancel=None, classes=None):
    origin, direction = np.asarray(origin, float), np.asarray(direction, float)
    direction = direction / np.linalg.norm(direction)
    best, depth = None, np.inf
    for records in vertex_blocks(source):
        if cancel and cancel():
            raise InterruptedError('Point picking cancelled')
        if classes is not None and 'classification' in records.dtype.names:
            records = records[np.isin(records['classification'], classes)]
        points = np.column_stack([records[a] for a in 'xyz']).astype(float)
        vectors = points - origin
        distances = vectors @ direction
        perpendicular = np.linalg.norm(np.cross(vectors, direction), axis=1)
        valid = (distances > 0) & (distances < depth) & (perpendicular <= tolerance * distances)
        if np.any(valid):
            indices = np.flatnonzero(valid)
            selected = indices[np.argmin(distances[indices])]
            best, depth = points[selected], distances[selected]
    return best
