"""Shared product transactions, input identity and bounded processing helpers."""
from __future__ import annotations
import functools
import hashlib
import json
import os
import shutil
import tempfile
import numpy as np


def file_stamp(path):
    """Metadata identity: no extra decoding/hashing of multi-GB source files."""
    st = os.stat(path)
    return [os.path.abspath(path), st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def model_stamp(folder):
    return [file_stamp(os.path.join(folder, n)) for n in ("cameras.bin", "images.bin")]


def require_points(points, title="Input"):
    if not len(points) or not np.isfinite(points).all():
        raise ValueError(f"{title} is empty or contains non-finite coordinates")


def region_checked(region):
    if region is None:
        return None
    v = np.asarray(region, float)
    if v.shape != (4,) or not np.isfinite(v).all() or v[2] <= v[0] or v[3] <= v[1]:
        raise ValueError("Region: maximum X/Y must exceed minimum X/Y")
    return v.tolist()


def remap_paths(value, old, new):
    if isinstance(value, dict):
        return {k: remap_paths(v, old, new) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [remap_paths(v, old, new) for v in value]
    if isinstance(value, str) and os.path.isabs(value):
        p, root = os.path.abspath(value), os.path.abspath(old)
        try:
            if os.path.commonpath([p, root]) == root:
                return os.path.join(new, os.path.relpath(p, root))
        except ValueError:
            pass
    return value


def publish_directory(stage, destination):
    """Same-volume rename with rollback; recover interrupted publication first."""
    previous = destination + ".previous"
    if os.path.exists(previous):
        if not os.path.exists(destination):
            os.replace(previous, destination)
        else:
            shutil.rmtree(previous)
    had_old = os.path.exists(destination)
    if had_old:
        os.replace(destination, previous)
    try:
        os.replace(stage, destination)
    except BaseException:
        if had_old:
            os.replace(previous, destination)
        raise
    if had_old:
        shutil.rmtree(previous, ignore_errors=True)


def product_transaction(function):
    """Build all dependent files together; a failed/cancelled run keeps the old set."""
    @functools.wraps(function)
    def run(cfg, *args, **kwargs):
        target = os.path.abspath(cfg["out_dir"])
        os.makedirs(os.path.dirname(target), exist_ok=True)
        previous = target + ".previous"
        if os.path.exists(previous) and not os.path.exists(target):
            os.replace(previous, target)
        stage = tempfile.mkdtemp(prefix=os.path.basename(target) + ".building-", dir=os.path.dirname(target))
        trial = dict(cfg, out_dir=stage, previous_dir=target)
        try:
            result = function(trial, *args, **kwargs)
            result = remap_paths(result, stage, target)
            if result.get("path"):
                from .geotiff import TiffReader
                with TiffReader(os.path.join(stage, os.path.relpath(result["path"], target))) as reader:
                    if not reader.levels:
                        raise ValueError("The new raster has no levels")
            if os.path.isfile(os.path.join(stage, "info.json")):
                with open(os.path.join(stage, "info.json"), "w", encoding="utf-8") as fh:
                    json.dump(result, fh, indent=1)
            publish_directory(stage, target)
            return result
        finally:
            if os.path.isdir(stage):
                shutil.rmtree(stage, ignore_errors=True)
    return run


def raster_budget(width, height, bytes_per_cell=64, folder=None):
    from .memguard import available_bytes
    cells = int(width) * int(height)
    if width < 1 or height < 1:
        raise ValueError("Empty raster region")
    memory = cells * bytes_per_cell
    disk = cells * 8
    if folder and shutil.disk_usage(folder).free < disk:
        raise ValueError(f"Raster requires about {disk / 2**30:.2f} GiB free disk space")
    return {"cells": cells, "memory": memory, "disk": disk,
            "fits_ram": memory < available_bytes() * .65}


def vertex_blocks(path, block=500_000):
    """Stream binary PLY vertex records; source files are never memory-mapped."""
    from .plyio import vertex_layout
    with open(path, "rb") as fh:
        layout = vertex_layout(fh)
        if layout is not None:
            _head, dtype, count = layout
            for start in range(0, count, block):
                records = np.fromfile(fh, dtype=dtype, count=min(block, count-start))
                if len(records) != min(block, count-start):
                    raise ValueError("Truncated PLY vertex block")
                yield records
            return
    from .pcfilter import read_cloud
    cloud = read_cloud(path)
    for start in range(0, len(cloud["xyz"]), block):
        xyz = cloud["xyz"][start:start+block]
        records = np.empty(len(xyz), dtype=[("x", "f8"), ("y", "f8"), ("z", "f8")])
        records["x"], records["y"], records["z"] = xyz.T
        yield records


def point_count(path):
    from .plyio import ply_counts
    return ply_counts(path)[0]


def bounds_from_ply(path):
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for v in vertex_blocks(path):
        xyz = np.column_stack([v["x"], v["y"], v["z"]])
        require_points(xyz)
        lo, hi = np.minimum(lo, xyz.min(0)), np.maximum(hi, xyz.max(0))
    if not np.isfinite(lo).all():
        raise ValueError("Input has no points")
    return lo, hi


def source_unit(georef):
    return "m" if georef else "model units"
