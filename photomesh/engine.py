"""Offline reconstruction capabilities and conservative hardware policies.

Engine flags come from the actual executable's help, not a version guess.
Native probes and processing are separate child processes. No network calls.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

PINNED_VERSION = "4.2.1"
_PROBES = {}
_GPU = None
_MODEL_STAMPS = {}


def fingerprint(exe):
    try:
        stat = os.stat(exe)
        return (os.path.abspath(exe), stat.st_size, stat.st_mtime_ns)
    except OSError:
        return (str(exe), 0, 0)


def child_env(exe):
    """COLMAP's Qt/DLL paths must never contaminate PySide6 in the host."""
    env = dict(os.environ)
    base = Path(exe).resolve().parent
    root = base.parent if base.name.lower() == "bin" else base
    paths = [str(base), str(root / "lib")]
    env["PATH"] = os.pathsep.join(paths + [env.get("PATH", "")])
    env.pop("QT_PLUGIN_PATH", None)
    env.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
    for plugins in (root / "plugins", root / "lib" / "plugins"):
        if plugins.is_dir():
            env["QT_PLUGIN_PATH"] = str(plugins)
            break
    env["QT_QPA_PLATFORM"] = "offscreen"
    # Explicit local model paths are supplied below; no URL defaults are used.
    return env


def run_help(exe, command="help"):
    key = (fingerprint(exe), command)
    if key not in _PROBES:
        try:
            result = subprocess.run([exe, command, "-h"] if command != "help" else [exe, "help"],
                                    capture_output=True, text=True, errors="replace", timeout=20,
                                    env=child_env(exe),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            text = result.stdout + result.stderr
            _PROBES[key] = text if result.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            _PROBES[key] = ""
    return _PROBES[key]


def commands(exe):
    return set(re.findall(r"^\s+([a-z][a-z0-9_]+)\s*(?:\n|:)", run_help(exe), re.MULTILINE))


def has_global(exe):
    return "global_mapper" in run_help(exe)


def hardware():
    global _GPU
    if _GPU is None:
        from .colmap import python_exe, task_env
        try:
            result = subprocess.run([python_exe(), "-m", "photomesh.engine_probe"],
                                    capture_output=True, text=True, timeout=8, env=task_env(),
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            data = json.loads(result.stdout) if result.returncode == 0 else {}
            _GPU = data if isinstance(data, dict) else {}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            _GPU = {}
    return _GPU


def bundle_manifest(exe):
    root = Path(exe).resolve().parent
    if root.name.lower() == "bin":
        root = root.parent
    path = root / "photomesh-engine.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def gpu_device(exe, requested=True):
    if not requested or os.environ.get("PHOTOMESH_FORCE_NO_GPU"):
        return None
    banner = run_help(exe)
    if not banner or "without cuda" in banner.lower() or not re.search(r"\bCUDA\b", banner):
        return None
    manifest = bundle_manifest(exe)
    if manifest.get("cuda") is False:
        return None
    info = hardware()
    minimum = int(manifest.get("minimum_driver", 0))
    if int(info.get("driver", 0)) < minimum:
        return None
    devices = [d for d in info.get("devices", [])
               if int(d.get("cc", 0)) >= int(manifest.get("minimum_cc", 0))
               and int(d.get("memory", 0)) >= 1024**3]
    return max(devices, key=lambda d: int(d["memory"]), default=None)


def group_capability(exe, command):
    from .colmap import colmap_options
    return any(key in colmap_options(exe, command) for key in ("FeatureExtraction.type", "FeatureMatching.type"))


def matching_arguments(exe, command, settings, extraction=False):
    """Select compatible feature types and local weights; reject silent substitutions."""
    from .colmap import colmap_options, opt
    supported = colmap_options(exe, command)
    method = settings.get("feature_method", "SIFT")
    requested = method != "SIFT"
    device = gpu_device(exe, settings.get("use_gpu", False)) if requested or bundle_manifest(exe) or group_capability(exe, command) else None
    # Legacy SIFT builders retain their tested behavior. Bundled modern engines use the probe.
    use_gpu = bool(device) if bundle_manifest(exe) or requested or group_capability(exe, command) else bool(settings.get("use_gpu", False))
    group = "FeatureExtraction" if extraction else "FeatureMatching"
    args = opt(exe, command, [group + ".use_gpu",
                            "SiftExtraction.use_gpu" if extraction else "SiftMatching.use_gpu"], int(use_gpu))
    if device and group + ".gpu_index" in supported:
        args += ["--" + group + ".gpu_index", str(device["index"])]
    if method == "SIFT":
        if group + ".type" in supported:
            args += ["--" + group + ".type", "SIFT" if extraction else "SIFT_BRUTEFORCE"]
        return args
    limit = settings.get("key_point_limit", 0)
    if limit <= 0 or limit > 4096:
        raise ValueError("Neural matching requires an explicit feature limit from 1 to 4096")
    if group + ".num_threads" in supported:
        args += ["--" + group + ".num_threads", "1" if use_gpu else "2"]
    if method not in ("SIFT + LightGlue", "ALIKED + LightGlue"):
        raise ValueError("Unknown feature method: " + str(method))
    key = group + ".type"
    if key not in supported:
        raise ValueError("This engine has no neural-feature support. Select SIFT or install the complete modern engine.")
    aliked = method.startswith("ALIKED")
    kind = ("ALIKED_N16ROT" if aliked else "SIFT") if extraction else (
        "ALIKED_LIGHTGLUE" if aliked else "SIFT_LIGHTGLUE")
    args += ["--" + key, kind]
    model_name = "aliked-n16rot.onnx" if extraction and aliked else (
        ("aliked-lightglue.onnx" if aliked else "sift-lightglue.onnx") if not extraction else None)
    if model_name:
        path = verified_model(exe, model_name)
        option = ("AlikedExtraction.n16rot_model_path" if extraction else
                  ("AlikedMatching.lightglue_model_path" if aliked else "SiftMatching.lightglue_model_path"))
        if option not in supported:
            raise ValueError("Required offline-model option is unsupported: " + option)
        args += ["--" + option, path]
    if extraction and aliked and settings.get("key_point_limit", 0) > 0:
        if "AlikedExtraction.max_num_features" not in supported:
            raise ValueError("Engine cannot enforce the requested ALIKED feature limit")
        args += ["--AlikedExtraction.max_num_features", str(settings["key_point_limit"])]
    return args


def verified_model(exe, name):
    manifest = bundle_manifest(exe)
    models = manifest.get("models", {})
    root = Path(exe).resolve().parent
    root = root.parent if root.name.lower() == "bin" else root
    path = root / "models" / name
    expected = models.get(name)
    if not isinstance(expected, str) or len(expected) != 64 or not path.is_file():
        raise ValueError("Offline model missing: " + name + ". Reinstall the complete Setup; processing never downloads models.")
    stamp = (str(path), path.stat().st_size, path.stat().st_mtime_ns, path.stat().st_ctime_ns)
    if _MODEL_STAMPS.get(stamp) != expected:
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if digest != expected:
            raise ValueError("Offline model checksum mismatch: " + name)
        _MODEL_STAMPS[stamp] = expected
    return str(path)


def global_arguments(exe, settings, database, images, output):
    """Use maintained global mapping; Ceres CPU is the safe solver default.

    A CUDA-enabled executable does not prove that Ceres was built with cuDSS.
    Enable its GPU solvers only in an explicitly certified bundle.
    """
    from .colmap import colmap_options
    opts = colmap_options(exe, "global_mapper")
    if not opts or not has_global(exe):
        return None
    result = ["global_mapper", "--database_path", database, "--image_path", images, "--output_path", output]
    if "GlobalMapper.skip_retriangulation" in opts:
        result += ["--GlobalMapper.skip_retriangulation", "0"]
    if "GlobalMapper.random_seed" in opts:
        result += ["--GlobalMapper.random_seed", "0"]
    # Do not automatically activate experimental backends or unsupported camera models.
    gpu = bool(gpu_device(exe, settings.get("use_gpu", False))) and bundle_manifest(exe).get("ceres_cuda") is True
    for key in ("GlobalMapper.gp_use_gpu", "GlobalMapper.ba_ceres_use_gpu"):
        if key in opts:
            result += ["--" + key, str(int(gpu))]
    return result


def synchronize_database_frames(connection):
    """Rebuild trivial single-photo frames after calibration groups change.

    The application aligns independent photographs, not synchronized multi-camera
    rigs. Reject a real rig before mutation rather than corrupting its graph.
    """
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"rigs", "rig_sensors", "frames", "frame_data"} <= tables:
        return
    if connection.execute("SELECT COUNT(*) FROM rig_sensors").fetchone()[0]:
        raise ValueError("Multi-camera rigs require a dedicated rig workflow; calibration grouping was cancelled.")
    connection.execute("DELETE FROM frame_data")
    connection.execute("DELETE FROM frames")
    connection.execute("DELETE FROM rigs")
    ids = [r[0] for r in connection.execute("SELECT DISTINCT camera_id FROM images")]
    connection.executemany("INSERT INTO rigs(rig_id,ref_sensor_id,ref_sensor_type) VALUES(?,?,0)", [(cid,cid) for cid in ids])
    rows = list(connection.execute("SELECT image_id,camera_id FROM images"))
    connection.executemany("INSERT INTO frames(frame_id,rig_id) VALUES(?,?)", rows)
    connection.executemany("INSERT INTO frame_data(frame_id,data_id,sensor_id,sensor_type) VALUES(?,?,?,0)",
                           [(iid,iid,cid) for iid,cid in rows])


def validate_model(folder):
    """Reject a numerically invalid generation before publishing camera poses."""
    import numpy as np
    from .colmap_io import read_model
    model = read_model(folder)
    if len(model.images) < 2 or not len(model.points):
        raise ValueError("Reconstruction has insufficient registered cameras or tie points")
    for cam in model.cameras.values():
        if cam.model not in (0,1,2,3,4,5,6) or not np.isfinite(cam.params).all() or min(cam.K()[:2]) <= 0:
            raise ValueError("Reconstruction contains unsupported or invalid calibration")
    for im in model.images.values():
        R = im.R()
        if not np.isfinite(im.tvec).all() or not np.isfinite(R).all() or not np.allclose(R.T @ R, np.eye(3), atol=1e-6):
            raise ValueError("Reconstruction contains an invalid camera pose")
    if not np.isfinite(model.points.xyz).all():
        raise ValueError("Reconstruction contains non-finite 3D points")
    return model


def sibling_engine(exe, name):
    root = Path(exe).resolve().parent
    root = root.parent if root.name.lower() == "bin" else root
    for candidate in (root.parent / name / "bin" / "colmap.exe",
                      root.parent / name / "bin" / "colmap",
                      root.parent / name / "colmap"):
        if candidate.is_file():
            return str(candidate)
    return None


def select_bundled(exe):
    if not bundle_manifest(exe):
        return exe
    if gpu_device(exe):
        return exe
    cpu = sibling_engine(exe, "colmap-cpu")
    if cpu and run_help(cpu):
        return cpu
    if run_help(exe):
        return exe  # CPU feature flags remain forced off for an incompatible GPU.
    raise ValueError("The bundled reconstruction engine cannot start. Reinstall Setup or select a compatible engine.")


def dense_executable(exe):
    from .colmap import has_cuda
    if gpu_device(exe):
        return exe
    if not bundle_manifest(exe):
        return exe if has_cuda(exe) else None
    for name in ("colmap", "colmap-legacy"):
        other = sibling_engine(exe, name)
        if other and gpu_device(other):
            return other
    return None


_PREFLIGHT = {}


def execution_settings(exe, settings, workdir, log=print):
    """Small real extraction/matching probe, cached for this engine/model/device.

    A GPU failure retries only the probe on CPU. Survey databases are never
    mixed, reduced in quality, or partially reused across feature types.
    """
    import tempfile
    from PIL import Image
    import numpy as np
    from .colmap import opt
    s = dict(settings)
    method = s.get("feature_method", "SIFT")
    device = gpu_device(exe, s.get("use_gpu", False))
    s["use_gpu"] = bool(device)
    key = (fingerprint(exe), method, json.dumps(device, sort_keys=True))
    # Recheck model identity even when the native compatibility result is cached.
    if method != "SIFT":
        matching_arguments(exe, "feature_extractor", s, True)
        matching_arguments(exe, "matches_importer", s, False)
    if key in _PREFLIGHT:
        s["use_gpu"] = _PREFLIGHT[key]
        return s
    with tempfile.TemporaryDirectory(prefix="engine-probe-", dir=workdir) as folder:
        photos = Path(folder) / "photos"
        photos.mkdir()
        rng = np.random.default_rng(811)
        image = rng.integers(0, 256, (96, 128, 3), dtype=np.uint8)
        for name in ("a.png", "b.png"):
            Image.fromarray(image).save(photos / name)
        pairs = Path(folder) / "pairs.txt"
        pairs.write_text("a.png b.png\n", encoding="utf-8")
        for attempt in range(2 if device else 1):
            db = str(Path(folder) / ("probe" + str(attempt) + ".db"))
            probe_s = dict(s, key_point_limit=128)
            extract = ["feature_extractor", "--database_path", db, "--image_path", str(photos)]
            extract += matching_arguments(exe, "feature_extractor", probe_s, True)
            extract += opt(exe, "feature_extractor", ["SiftExtraction.max_num_features"], 128)
            match = ["matches_importer", "--database_path", db, "--match_list_path", str(pairs), "--match_type", "pairs"]
            match += matching_arguments(exe, "matches_importer", probe_s, False)
            failure = None
            for command in (extract, match):
                try:
                    result = subprocess.run([exe, *command], capture_output=True, text=True,
                                            errors="replace", timeout=90, env=child_env(exe),
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    if result.returncode:
                        failure = (result.stderr + result.stdout)[-2500:]
                        break
                except (OSError, subprocess.TimeoutExpired) as error:
                    failure = str(error)
                    break
            if failure is None:
                _PREFLIGHT[key] = s["use_gpu"]
                log(f"Engine check passed: {method}; {'GPU ' + device['name'] if s['use_gpu'] else 'CPU'}.")
                return s
            if attempt == 0 and device:
                s["use_gpu"] = False
                log("Native GPU compatibility probe failed; retrying the same feature method on CPU.")
            else:
                raise ValueError(f"Engine compatibility check failed for {method}. "
                                 "No survey files were changed. Select SIFT or reinstall the full Setup.\n" + failure)
    return s
