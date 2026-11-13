"""Equivalent-workload accuracy/runtime/peak-RSS evidence, no user data."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def workload(kind, method):
    from scipy import sparse
    from photomesh.survey_capacity import grouped_median, nearest_neighbours, solve_camera_system
    import psutil
    import threading
    peak, stop = [0], threading.Event()
    process = psutil.Process()
    def measure():
        while not stop.wait(.002):
            peak[0] = max(peak[0], process.memory_info().rss)
    thread = threading.Thread(target=measure, daemon=True); thread.start()
    rng = np.random.default_rng(105)
    if kind == 'camera':
        matrix = sparse.diags([-np.ones(1799), np.full(1800, 4.), -np.ones(1799)], [-1, 0, 1], format='csc')
        rhs = rng.normal(size=1800)
        started = time.perf_counter()
        result = solve_camera_system(matrix, rhs, dense_limit=10000 if method == 'before' else 0)
        error = float(np.max(abs(matrix @ result-rhs)))
        checksum = float(result.sum())
    elif kind == 'gps':
        xyz = rng.normal(size=(2500, 3))*1000
        started = time.perf_counter()
        if method == 'before':
            distance = np.linalg.norm(xyz[:, None]-xyz[None, :], axis=2)
            np.fill_diagonal(distance, np.inf)
            pairs = [(i, int(j)) for i in range(len(xyz)) for j in np.argsort(distance[i])[:8]]
        else:
            pairs = list(nearest_neighbours(xyz, 8))
        import hashlib
        checksum = hashlib.sha256(np.asarray(sorted(pairs), dtype='<i8').tobytes()).hexdigest()
        error = 0.
    else:
        indices = rng.integers(0, 120000, 1000000)
        heights = rng.normal(size=len(indices))
        started = time.perf_counter()
        if method == 'before':
            order = np.argsort(indices, kind='stable'); keys = indices[order]
            unique, first, counts = np.unique(keys, return_index=True, return_counts=True)
            values = heights[order]
            result = np.array([np.median(values[start:start+count]) for start, count in zip(first, counts)])
        else:
            unique, result = grouped_median(indices, heights)
        import hashlib
        checksum = hashlib.sha256(unique.tobytes()+result.tobytes()).hexdigest()
        error = 0.
    elapsed = time.perf_counter()-started
    peak[0] = max(peak[0], process.memory_info().rss)
    stop.set(); thread.join()
    return dict(seconds=elapsed, checksum=checksum, max_equation_error=error, peak_rss_bytes=peak[0])


def run(output):
    import tempfile
    report = dict(scope='Controlled equal workloads; peak process RSS includes interpreter/imports', results=[])
    with tempfile.TemporaryDirectory() as temp:
        for kind in ('camera', 'gps', 'median'):
            rows = []
            for method in ('before', 'after'):
                target = Path(temp)/(kind+'-'+method+'.json')
                process = subprocess.Popen([sys.executable, __file__, '--worker', kind, '--method', method, '--output', str(target)])
                process.wait()
                if process.returncode:
                    raise RuntimeError('Capacity benchmark subprocess failed')
                row = json.loads(target.read_text()); row.update(kind=kind, method=method)
                rows.append(row)
            if kind == 'camera':
                assert abs(rows[0]['checksum']-rows[1]['checksum']) < 1e-9
                assert max(r['max_equation_error'] for r in rows) < 1e-10
            else:
                assert rows[0]['checksum'] == rows[1]['checksum'], kind
            report['results'].extend(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=['camera', 'gps', 'median'])
    parser.add_argument('--method', choices=['before', 'after'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.worker:
        args.output.write_text(json.dumps(workload(args.worker, args.method)))
    else:
        run(args.output)
