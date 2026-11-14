"""Equivalent-camera workload comparison for the 1.0.4 reference audit."""
import copy
import gc
import json
import statistics
import subprocess
import sys
import time
import types
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"tests"))
from photomesh import georef, colmap_io as cio
from test_dense_mesh_gcp import synthetic_model

BASE = "653bb2b0d2f05df3397b70cc87b32f6d5f871717"


def main():
    source = subprocess.check_output(["git","show",BASE+":photomesh/georef.py"],cwd=ROOT).decode("utf-8")
    baseline = types.ModuleType("photomesh._reference_baseline")
    baseline.__package__ = "photomesh"; sys.modules[baseline.__name__] = baseline
    exec(compile(source,"baseline/georef.py","exec"),baseline.__dict__)
    scene = synthetic_model(n_img=10,n_pts=400,two_cameras=False)
    rng = np.random.default_rng(104)
    for image in scene.images.values():
        image.tvec += rng.normal(0,.05,3)
    results = {}
    models = {}
    for label,module in (("baseline",baseline),("current",georef)):
        timings = []
        for repeat in range(4):
            model = copy.deepcopy(scene)
            gc.collect(); start = time.perf_counter()
            module.gcp_bundle_adjust(model,{}, {},{"fit_intrinsics":False,"max_iterations":5},log=lambda *_:None)
            elapsed = time.perf_counter()-start
            if repeat: timings.append(elapsed)
        results[label] = {"seconds":statistics.median(timings),
                          "rms_px":float(np.sqrt(np.mean(cio.observation_errors(model)[0]**2)))}
        models[label] = model
    results["baseline_commit"] = BASE
    results["runtime_ratio"] = results["current"]["seconds"]/results["baseline"]["seconds"]
    text = json.dumps(results,indent=2)
    Path("reference-performance-104.json").write_text(text)
    print(text,flush=True)
    # Keeping accepted bundle-adjusted tie coordinates can improve reprojection
    # RMS relative to the baseline's unconditional retriangulation. Reject any
    # regression or non-finite result, but allow that intentional improvement.
    assert np.isfinite(results["baseline"]["rms_px"])
    assert np.isfinite(results["current"]["rms_px"])
    assert results["current"]["rms_px"] <= results["baseline"]["rms_px"] + 1e-6
    for iid in models["current"].images:
        np.testing.assert_allclose(models["current"].images[iid].center(),
                                   models["baseline"].images[iid].center(),atol=1e-5,rtol=0)
    if results["runtime_ratio"] > 1.5:
        raise SystemExit("Reference optimization runtime increased over 50%; investigate")


if __name__ == "__main__":
    main()
