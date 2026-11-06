"""Release-review regressions for memory preflight and reference-safe cleanup."""
import os
import pytest


@pytest.mark.parametrize("amount", [None, 0, -1])
def test_unreadable_memory_is_rejected_without_guessing(monkeypatch, amount):
    from photomesh import memguard, workflow
    monkeypatch.setattr(memguard, "available_bytes", lambda: amount)
    with pytest.raises(ValueError, match="Available RAM could not be read"):
        workflow.raster_budget(10, 10)
    # Worker-count estimates retain their existing CPU fallback.
    assert memguard.cap_workers(2, 1024) == (1 if amount == -1 else 2)


def test_dem_memory_preflight_keeps_previous_output(tmp_path, monkeypatch):
    from photomesh import dem_engine, memguard, plyio
    out = tmp_path / "dem"
    out.mkdir()
    existing = out / "previous.tif"
    existing.write_bytes(b"previous successful product")
    monkeypatch.setattr(memguard, "available_bytes", lambda: None)
    monkeypatch.setattr(plyio, "ply_counts", lambda _: (4, 0))
    monkeypatch.setattr(plyio, "read_fast", lambda _: pytest.fail("RAM must be checked before decoding"))
    with pytest.raises(ValueError, match="Available RAM could not be read"):
        dem_engine.build_dem({"cloud": str(tmp_path / "cloud.ply"), "out_dir": str(out)})
    assert existing.read_bytes() == b"previous successful product"
    assert not list(tmp_path.glob("dem.building-*"))


def test_stale_cleanup_skips_referenced_workdir(window, tmp_path, monkeypatch):
    from photomesh.project import data_folder
    from PySide6.QtWidgets import QMessageBox
    path = str(tmp_path / "project.pmsx")
    work = os.path.join(data_folder(path), "processing.partial")
    os.makedirs(os.path.join(work, "dense"))
    keep = os.path.join(work, "dense", "result.ply")
    with open(keep, "wb") as fh:
        fh.write(b"referenced result")
    window.project.path = path
    window.dataset.workdir = work
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: pytest.fail("Referenced data must not be offered"))
    window._offer_stale_cleanup(path)
    assert os.path.exists(keep)


def test_stale_cleanup_rechecks_references_after_confirmation(window, tmp_path, monkeypatch):
    from photomesh.project import data_folder, Camera
    from PySide6.QtWidgets import QMessageBox
    path = str(tmp_path / "project.pmsx")
    work = os.path.join(data_folder(path), "processing.partial")
    os.makedirs(os.path.join(work, "dense"))
    keep = os.path.join(work, "dense", "photo.jpg")
    with open(keep, "wb") as fh:
        fh.write(b"source photo")
    window.project.path = path
    def confirm(*args, **kwargs):
        window.dataset.cameras.append(Camera(keep))
        return QMessageBox.Yes
    monkeypatch.setattr(QMessageBox, "question", confirm)
    window._offer_stale_cleanup(path)
    assert os.path.exists(keep)


@pytest.mark.parametrize("contents", [b"bad file", b"II", b"II\x2a\x00\x08\x00\x00\x00"])
def test_invalid_tiff_closes_its_handle(tmp_path, monkeypatch, contents):
    import builtins
    from photomesh.geotiff import TiffReader
    path = tmp_path / "broken.tif"
    path.write_bytes(contents)
    original = builtins.open
    handles = []
    def tracked(name, *args, **kwargs):
        handle = original(name, *args, **kwargs)
        if isinstance(name, (str, os.PathLike)) and os.fspath(name) == os.fspath(path):
            handles.append(handle)
        return handle
    monkeypatch.setattr(builtins, "open", tracked)
    with pytest.raises(ValueError):
        TiffReader(str(path))
    assert handles and all(handle.closed for handle in handles)


def test_invalid_dem_sidecar_closes_raster_reader(tmp_path, monkeypatch):
    from photomesh import raster_surface
    path = tmp_path / "dem.tif"
    (tmp_path / "info.json").write_text("{broken")
    class Reader:
        geo = (0, 1, 1, 1)
        width = height = 2
        closed = False
        def close(self):
            self.closed = True
    reader = Reader()
    monkeypatch.setattr(raster_surface.gt, "TiffReader", lambda _: reader)
    with pytest.raises(ValueError):
        raster_surface.RasterSurface(str(path))
    assert reader.closed


@pytest.mark.parametrize("reference, expected", [(0, 25.0), (1, -25.0),
                                                (bytes([0]), 25.0), (bytes([1]), -25.0), (b"", 25.0)])
def test_exif_altitude_agrees_between_photo_import_paths(monkeypatch, reference, expected):
    from PIL import Image
    from photomesh import fastpipe, project
    gps = {1: "N", 2: (1, 0, 0), 3: "E", 4: (2, 0, 0), 5: reference, 6: (25, 1)}
    class Exif:
        def get_ifd(self, tag):
            return gps
    class Photo:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def getexif(self):
            return Exif()
    monkeypatch.setattr(Image, "open", lambda _: Photo())
    camera = project.Camera("photo.jpg")
    project.read_exif_gps(camera)
    assert (camera.lon, camera.lat, camera.alt) == (2.0, 1.0, expected)
    assert fastpipe._gps(Exif()) == (camera.lon, camera.lat, camera.alt)


def test_running_pipeline_keeps_project_context_and_save_paths(window, tmp_path):
    from types import SimpleNamespace
    from PySide6.QtGui import QCloseEvent
    original_project, original_runner = window.project, window.runner
    path = tmp_path / "unchanged.pmsx"
    path.write_bytes(b"existing project")
    try:
        window.runner = SimpleNamespace(busy=True)
        window.new_project()
        assert window.project is original_project
        assert window._save_to(str(path)) is False
        assert path.read_bytes() == b"existing project"
        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        assert "processing" in window.statusBar().currentMessage()
    finally:
        window.runner = original_runner


def test_project_preparation_blocks_switching(window):
    original = window.project
    try:
        window._opening = True
        window.new_project()
        assert window.project is original
        assert window.save_project_as() is False
    finally:
        window._opening = False


def test_failed_metadata_save_retains_migrated_temporary_source(window, tmp_path, monkeypatch):
    from photomesh import datafolder
    root = tmp_path / "legacy-temp"
    source = root / "processing"
    source.mkdir(parents=True)
    (source / "result.ply").write_bytes(b"original result")
    destination = tmp_path / "copy.files" / "processing"
    destination.mkdir(parents=True)
    (destination / "result.ply").write_bytes(b"original result")
    monkeypatch.setattr(datafolder, "legacy_temp_root", lambda: str(root))
    window.dataset.workdir = str(destination)
    window._temporary_data_copies = [(window.project, str(source), str(destination))]
    monkeypatch.setattr(window, "_bring_data", lambda *a, **k: True)
    path = tmp_path / "copy.pmsx"
    path.write_bytes(b"old project metadata")
    original_save = window.project.save
    def fail(_):
        raise OSError("simulated disk write failure")
    monkeypatch.setattr(window.project, "save", fail)
    assert window._save_to(str(path)) is False
    assert path.read_bytes() == b"old project metadata"
    assert (source / "result.ply").read_bytes() == b"original result"
    monkeypatch.setattr(window.project, "save", original_save)
    assert window._save_to(str(path)) is True
    assert not source.exists()
    assert (destination / "result.ply").read_bytes() == b"original result"


def test_migration_keeps_source_photos_in_temporary_folder(window, tmp_path, monkeypatch):
    from photomesh import datafolder
    from photomesh.project import Camera
    root = tmp_path / "legacy-temp"
    source = root / "processing"
    source.mkdir(parents=True)
    photo = source / "source.jpg"
    photo.write_bytes(b"original photograph")
    destination = tmp_path / "copy.files" / "processing"
    destination.mkdir(parents=True)
    monkeypatch.setattr(datafolder, "legacy_temp_root", lambda: str(root))
    window.dataset.workdir = str(destination)
    window.dataset.cameras = [Camera(str(photo))]
    window._temporary_data_copies = [(window.project, str(source), str(destination))]
    monkeypatch.setattr(window, "_bring_data", lambda *a, **k: True)
    assert window._save_to(str(tmp_path / "copy.pmsx")) is True
    assert photo.read_bytes() == b"original photograph"


def test_cleanup_protection_follows_linked_photo_targets(tmp_path):
    from photomesh import datafolder
    folder = tmp_path / "processing.partial"
    folder.mkdir()
    photo = folder / "source.jpg"
    photo.write_bytes(b"source")
    alias = tmp_path / "photo-link.jpg"
    try:
        alias.symlink_to(photo)
    except OSError:
        pytest.skip("Creating symlinks is unavailable for this account")
    assert datafolder.contains_referenced_data(str(folder), [str(alias)])
    assert photo.read_bytes() == b"source"
