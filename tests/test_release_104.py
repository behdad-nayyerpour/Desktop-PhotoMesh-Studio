"""1.0.4: shared Plan View, GPS policy, offline license and saved UI state."""
import os
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication
from photomesh.project import Camera, Project, ProjectData


def test_plan_switching_keeps_photo_and_ortho_tools(window, image_dir):
    window.dataset.add_photos([str(next(image_dir.glob("*.jpg")))])
    window.open_photo(0)
    assert window.tabs.count() == 2
    assert window.tabs.currentWidget() is window.plan_view
    assert window.active_view() is window.photo_view
    window.photo_view.active_marker = "G1"
    emitted = []
    window.photo_view.pinMarker.connect(lambda *args: emitted.append(args))
    window.photo_view.ctrl_click(20, 30)
    assert emitted == [("G1", 20., 30.)]
    window.show_view(window.ortho_view)
    assert window.active_view() is window.ortho_view
    window.show_view(window.photo_view)
    window.reset_view()
    assert window.photo_view.active_marker == "G1"
    assert window.photo_view.path == window.dataset.cameras[0].path


def test_failed_photo_open_clears_previous_identity(window, image_dir):
    photo = str(next(image_dir.glob("*.jpg")))
    window.photo_view.open(photo)
    assert window.photo_view.path == photo
    window.photo_view.open(photo + ".missing")
    assert window.photo_view.path is None
    assert window.photo_view._pix is None


def test_gps_policy_does_not_exclude_photos_or_change_with_markers(tmp_path):
    from photomesh.photo_gps import use_photo_gps, camera_gps
    dataset = ProjectData(cameras=[
        Camera("a.jpg", lon=44., lat=40., alt=100.),
        Camera("b.jpg", lon=None, lat=None, alt=None)])
    assert use_photo_gps(dataset)
    assert camera_gps(dataset) == {"a.jpg": [44., 40., 100.]}
    dataset.markers.append({"label": "check", "enabled": False})
    assert use_photo_gps(dataset)
    dataset.reference_settings["use_photo_gps"] = False
    assert not camera_gps(dataset)
    assert all(camera.enabled for camera in dataset.cameras)
    project = Project()
    project.datasets = [dataset]
    path = str(tmp_path / "gps.pmsx")
    project.save(path)
    assert not use_photo_gps(Project.load(path).dataset)


def test_legacy_opt_out_needs_explicit_global_opt_in():
    from photomesh.photo_gps import use_photo_gps, camera_gps
    dataset = ProjectData(cameras=[Camera("a.jpg", lon=44., lat=40., alt=100., use_reference=False)])
    assert not use_photo_gps(dataset)
    dataset.reference_settings["use_photo_gps"] = True
    assert "a.jpg" in camera_gps(dataset)
    assert not dataset.cameras[0].use_reference  # serialized legacy fields are not rewritten


def test_gps_off_disables_both_alignment_gps_routes(window):
    from photomesh.dialogs import AlignPhotosDialog
    window.dataset.cameras = [Camera(str(i)+".jpg", lon=lon, lat=lat, alt=100.)
        for i, (lon, lat) in enumerate([(44., 40.), (44.001, 40.), (44., 40.001)])]
    window.dataset.reference_settings["use_photo_gps"] = False
    dialog = AlignPhotosDialog(window)
    assert not dialog.reference.isChecked() and not dialog.reference.isEnabled()
    assert not dialog.gps_frame.isChecked() and not dialog.gps_frame.isEnabled()


def test_layout_roundtrip_and_independent_plan_content(window):
    from photomesh.ui_state import save_window_state, restore_window_state, KEY
    settings = QSettings()
    try:
        window.resize(1300, 850)
        window.show_view(window.photo_view)
        window._show_dock("Jobs", True)
        save_window_state(window)
        window.show_view(window.model_view)
        window.docks["Jobs"].hide()
        restore_window_state(window)
        QApplication.processEvents()
        assert window.active_view() is window.photo_view
        assert window.docks["Jobs"].isFloating()
        assert not window.docks["Jobs"].isHidden()
    finally:
        settings.remove(KEY)


def test_picker_remembers_success_but_not_cancellation(monkeypatch, tmp_path):
    from photomesh.filedialogs import QFileDialog, NativeFileDialog, _key
    settings = QSettings()
    caption = "104 regression import"
    key = _key("open", caption)
    seen = []
    path = str(tmp_path / "photo.jpg")
    def pick(parent, title, directory, *args, **kwargs):
        seen.append(directory)
        return (path, "Images") if len(seen) == 1 else ("", "")
    monkeypatch.setattr(NativeFileDialog, "getOpenFileName", staticmethod(pick))
    try:
        assert QFileDialog.getOpenFileName(None, caption)[0] == path
        assert QFileDialog.getOpenFileName(None, caption) == ("", "")
        assert seen[1] == str(tmp_path)
        assert settings.value(key) == str(tmp_path)
    finally:
        settings.remove(key)


def test_full_license_is_bundled_readable_text():
    from photomesh.about_ui import LICENSE_PATH
    text = LICENSE_PATH.read_text(encoding="utf-8")
    assert "Personal and Educational Non-Commercial License" in text
    assert "prior written permission" in text


def test_camera_gps_uses_exact_model_aliases_for_duplicate_filenames():
    from photomesh.photo_gps import camera_gps
    dataset = ProjectData(cameras=[
        Camera("/a/photo.jpg", lon=44., lat=40., alt=100., colmap_name="photo.jpg"),
        Camera("/b/photo.jpg", lon=45., lat=41., alt=200., colmap_name="photo_1.jpg")])
    assert camera_gps(dataset) == {"photo.jpg": [44., 40., 100.], "photo_1.jpg": [45., 41., 200.]}
    for camera in dataset.cameras:
        camera.colmap_name = ""
    assert not camera_gps(dataset)  # unresolved legacy aliases must never swap GPS references
