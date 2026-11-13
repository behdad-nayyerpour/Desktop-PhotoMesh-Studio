"""Exact sparse adjustment and bounded-neighbour survey operations."""
import numpy as np


def solve_camera_system(matrix, rhs, dense_limit=768):
    """Direct solve of the same damped Schur system; no iterative approximation.

    Small systems retain Cholesky. Large systems stay sparse through SuperLU.
    A failed factorization or unacceptable backward error rejects the LM step.
    """
    from scipy.linalg import cho_factor, cho_solve
    from scipy.sparse.linalg import splu
    matrix = matrix.tocsc()
    if matrix.shape[0] <= dense_limit:
        result = cho_solve(cho_factor(matrix.toarray(), check_finite=False), rhs, check_finite=False)
    else:
        try:
            result = splu(matrix).solve(np.asarray(rhs, float))
        except RuntimeError as error:
            raise np.linalg.LinAlgError(str(error)) from error
    scale = np.max(np.asarray(abs(matrix).sum(axis=1))) * np.linalg.norm(result, np.inf) + np.linalg.norm(rhs, np.inf)
    error = np.linalg.norm(matrix @ result - rhs, np.inf)
    if not np.isfinite(result).all() or not np.isfinite(error) or error > 1e-8 * max(scale, np.finfo(float).tiny):
        raise np.linalg.LinAlgError('Camera system failed the backward-error check')
    return result


def nearest_neighbours(xyz, k):
    """Yield exact Euclidean neighbours, ties ordered by source index.

    Compress duplicate coordinates before querying, so identical GPS positions
    cannot create a quadratic radius-query result. ECEF is supplied by the caller.
    """
    from scipy.spatial import cKDTree
    xyz = np.asarray(xyz, float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
        raise ValueError('Neighbour positions must be finite XYZ triples')
    k = max(0, min(int(k), len(xyz)-1))
    if not k:
        return
    unique, inverse, counts = np.unique(xyz, axis=0, return_inverse=True, return_counts=True)
    order = np.argsort(inverse, kind='stable')
    first = np.r_[0, np.cumsum(counts)]
    tree = cKDTree(unique)
    if len(unique) == len(xyz):
        # Normal surveys have distinct positions. Batch their exact queries;
        # only a tie at the selection boundary needs a radius refinement.
        original = order[first[:-1]]
        width = min(k+2, len(xyz))
        for start in range(0, len(xyz), 2048):
            points = xyz[start:start+2048]
            _, neighbours = tree.query(points, k=width, eps=0, workers=1)
            candidates = original[np.asarray(neighbours).reshape(-1, width)]
            distance = np.linalg.norm(xyz[candidates]-points[:, None], axis=2)
            distance[candidates == np.arange(start, start+len(points))[:, None]] = np.inf
            sorting = np.lexsort((candidates, distance), axis=1)
            candidates = np.take_along_axis(candidates, sorting, axis=1)
            distance = np.take_along_axis(distance, sorting, axis=1)
            for local, row in enumerate(candidates):
                index = start+local
                radius = distance[local, k-1]
                tolerance = 8*np.finfo(float).eps*max(1., radius)
                if np.isfinite(distance[local, k]) and distance[local, k]-radius <= tolerance:
                    row = original[tree.query_ball_point(points[local], radius+tolerance, eps=0)]
                    row = row[row != index]
                    exact = np.linalg.norm(xyz[row]-points[local], axis=1)
                    row = row[np.lexsort((row, exact))]
                for other in row[:k]:
                    yield index, int(other)
        return
    query_k = min(k+1, len(unique))
    for start in range(0, len(unique), 2048):
        distances, groups = tree.query(unique[start:start+2048], k=query_k, eps=0, workers=1)
        distances = np.asarray(distances).reshape(-1, query_k)
        groups = np.asarray(groups).reshape(-1, query_k)
        for local, (radii, nearby) in enumerate(zip(distances, groups)):
            group = start+local
            if counts[group] > k:
                candidates = order[first[group]:first[group]+k+1]
            else:
                # Query all groups at the boundary before deterministic tie-breaking.
                available = np.cumsum(counts[nearby]) - 1
                radius = radii[np.searchsorted(available, k)]
                radius += 8*np.finfo(float).eps*max(1., radius)
                nearby = tree.query_ball_point(unique[group], radius, eps=0)
                candidates = np.concatenate([order[first[j]:min(first[j+1], first[j]+k+1)] for j in nearby])
                delta = xyz[candidates]-unique[group]
                distance = np.linalg.norm(delta, axis=1)
                candidates = candidates[np.lexsort((candidates, distance))][:k+1]
            for index in order[first[group]:first[group+1]]:
                for other in candidates[candidates != index][:k]:
                    yield int(index), int(other)


def grouped_median(indices, heights):
    """Exact odd/even medians without a Python loop per occupied raster cell."""
    indices, heights = np.asarray(indices), np.asarray(heights, float)
    if len(indices) != len(heights):
        raise ValueError('Cell indices and heights must have equal lengths')
    if not len(indices):
        return np.empty(0, np.int64), np.empty(0, float)
    order = np.lexsort((heights, indices))
    keys = indices[order]
    first = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1])+1]
    count = np.diff(np.r_[first, len(order)])
    lower, upper = first+(count-1)//2, first+count//2
    # numpy.median averages the two middle values, including its IEEE behaviour.
    values = heights[order[lower]].copy()
    even = count % 2 == 0
    values[even] = (values[even] + heights[order[upper[even]]]) / 2
    return keys[first], values
