"""Compare ordered photo processing against the previous preview implementation."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from photomesh import fastpipe


def main():
    baseline = "16ae559c8d17c3004eae282fedc21839863f6dbe"
    url = ("https://raw.githubusercontent.com/behdad-nayyerpour/"
           f"Desktop-PhotoMesh-Studio/{baseline}/photomesh/fastpipe.py")
    with urlopen(url, timeout=30) as response:
        source = response.read().decode("utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "pool_map")
    namespace = dict(vars(fastpipe))
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<baseline pool_map>", "exec"), namespace)
    previous = namespace["pool_map"]
    from PIL import Image
    import numpy as np
    timings = {"previous": [], "current": []}
    expected = None
    with tempfile.TemporaryDirectory(prefix="photomesh-pool-comparison-") as folder:
        root = Path(folder)
        rng = np.random.default_rng(51)
        photos = []
        for index in range(24):
            path = root / f"photo-{index}.jpg"
            Image.fromarray(rng.integers(0, 256, (1200, 1600, 3), dtype=np.uint8)).save(path, quality=90)
            photos.append(path)
        for repeat in range(2):
            for name in (("previous", "current") if repeat == 0 else ("current", "previous")):
                out = root / f"{name}-{repeat}"
                out.mkdir()
                jobs = [(str(photo), [(str(out / photo.name), 1024)]) for photo in photos]
                start = time.perf_counter()
                results = list((previous if name == "previous" else fastpipe.pool_map)(
                    fastpipe._shrink_job, jobs, workers=2))
                timings[name].append(time.perf_counter() - start)
                assert [item[0] for item in results] == [str(photo) for photo in photos]
                assert all(error is None and dimensions[:2] == (1600, 1200)
                           for _, dimensions, error in results)
                digests = [hashlib.sha256((out / photo.name).read_bytes()).hexdigest() for photo in photos]
                if expected is None:
                    expected = digests
                assert digests == expected, "Photo outputs changed between equivalent workloads"
    medians = {name: statistics.median(values) for name, values in timings.items()}
    print(json.dumps({"baseline": baseline, "photos": 24, "workers": 2, "batch_size": 4,
                      "seconds": timings, "median_seconds": medians,
                      "current_over_previous": medians["current"] / medians["previous"],
                      "ordered_outputs_and_jpeg_hashes_equal": True}, indent=2), flush=True)


if __name__ == "__main__":
    main()
