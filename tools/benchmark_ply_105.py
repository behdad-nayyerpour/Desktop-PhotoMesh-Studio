"""Development-only interoperability/performance comparison on equal PLY data."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from photomesh.plycodec import PlyDocument, PlyElement  # noqa: E402


def benchmark(points=1_000_000):
    from plyfile import PlyData as OracleDocument, PlyElement as OracleElement
    rng = np.random.default_rng(105)
    data = np.zeros(points, dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"),
                                  ("red", "u1"), ("green", "u1"), ("blue", "u1"), ("confidence", "u2")])
    for field in ("x", "y", "z"):
        data[field] = rng.normal(size=points)
    data["red"], data["green"], data["blue"], data["confidence"] = 55, 128, 240, 8
    result = {"points": points, "timings": {}, "semantic_match": False}
    with tempfile.TemporaryDirectory(prefix="lens2mesh-ply-") as folder:
        for label, doc in (("reference", OracleDocument([OracleElement.describe(data, "vertex")], text=False, byte_order="<")),
                           ("independent", PlyDocument([PlyElement.describe(data, "vertex")]))):
            durations = []
            path = Path(folder) / (label + ".ply")
            for _ in range(3):
                start = time.perf_counter(); doc.write(path); durations.append(time.perf_counter() - start)
            result["timings"][label + "_write_median_s"] = float(np.median(durations))
            recovered = OracleDocument.read(path, mmap=False)["vertex"].data
            for field in data.dtype.names:
                np.testing.assert_array_equal(recovered[field], data[field])
        result["semantic_match"] = True
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = benchmark()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
