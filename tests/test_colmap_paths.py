"""Regression tests for executable capability detection and photo staging."""
import os
from types import SimpleNamespace

from photomesh import colmap
from photomesh.project import Camera, ProjectData


def test_has_cuda_requires_a_readable_banner(monkeypatch):
    monkeypatch.setattr(colmap, "nvidia_driver_present", lambda: True)
    colmap._HELP_CACHE.clear()
    monkeypatch.setattr(colmap.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="", stderr=""))
    assert not colmap.has_cuda("missing-colmap")

    colmap._HELP_CACHE.clear()
    monkeypatch.setattr(colmap.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(stdout="COLMAP build without CUDA", stderr=""))
    assert not colmap.has_cuda("cpu-colmap")

    colmap._HELP_CACHE.clear()
    monkeypatch.setattr(colmap.subprocess, "run", lambda *a, **k:
                        SimpleNamespace(stdout="COLMAP 3.8 with CUDA", stderr=""))
    assert colmap.has_cuda("gpu-colmap")
    colmap._HELP_CACHE.clear()


def test_prepare_images_refreshes_reused_name(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    other = tmp_path / "other"
    for folder in (old, new, other):
        folder.mkdir()
    (old / "same.jpg").write_bytes(b"old photo")
    (new / "same.jpg").write_bytes(b"new photo")
    (other / "other.jpg").write_bytes(b"another photo")
    dataset = ProjectData(cameras=[Camera(path=str(old / "same.jpg")),
                           Camera(path=str(other / "other.jpg"))])
    workdir = str(tmp_path / "work")
    colmap.prepare_images(dataset, workdir)
    assert (tmp_path / "work" / "images" / "same.jpg").read_bytes() == b"old photo"

    dataset.cameras[0].path = str(new / "same.jpg")
    colmap.prepare_images(dataset, workdir)
    assert (tmp_path / "work" / "images" / "same.jpg").read_bytes() == b"new photo"


def test_prepare_images_reuses_unchanged_copies(tmp_path, monkeypatch):
    # Some Windows volumes and sandboxes deny both kinds of links. Re-running
    # alignment must not copy every large aerial photo when nothing changed.
    left, right, replacement = (tmp_path / name for name in ("left", "right", "replacement"))
    for folder in (left, right, replacement):
        folder.mkdir()
    photo = left / "same.jpg"
    photo.write_bytes(b"first")
    (right / "other.jpg").write_bytes(b"other")
    (replacement / "same.jpg").write_bytes(b"newer")
    dataset = ProjectData(cameras=[Camera(path=str(photo)), Camera(path=str(right / "other.jpg"))])
    wd = str(tmp_path / "work")
    monkeypatch.setattr(colmap.os, "link", lambda *args: (_ for _ in ()).throw(OSError("no links")))
    monkeypatch.setattr(colmap.os, "symlink", lambda *args: (_ for _ in ()).throw(OSError("no symlinks")))
    real_copy = colmap.shutil.copy2
    copies = []

    def copy(src, dst):
        copies.append((src, dst))
        return real_copy(src, dst)

    monkeypatch.setattr(colmap.shutil, "copy2", copy)
    colmap.prepare_images(dataset, wd)
    assert len(copies) == 2
    colmap.prepare_images(dataset, wd)
    assert len(copies) == 2

    before = photo.stat()
    photo.write_bytes(b"fresh")
    # The cache contract observes file metadata. Rapid same-length writes can
    # share a filesystem timestamp on Windows; advance it explicitly so this
    # tests invalidation rather than the host's clock granularity.
    os.utime(photo, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
    colmap.prepare_images(dataset, wd)
    assert len(copies) == 3
    staged = tmp_path / "work" / "images" / "same.jpg"
    assert staged.read_bytes() == b"fresh"

    dataset.cameras[0].path = str(replacement / "same.jpg")
    colmap.prepare_images(dataset, wd)
    assert len(copies) == 4
    assert staged.read_bytes() == b"newer"

    before = staged.stat()
    staged.write_bytes(b"wrong")
    os.utime(staged, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
    colmap.prepare_images(dataset, wd)
    assert len(copies) == 5
    assert staged.read_bytes() == b"newer"
