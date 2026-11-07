"""1.0.4: shared Plan View, GPS policy, offline license and saved UI state."""
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
        window.model_view.set_mesh_mode("wireframe")
        window.model_view.set_solid("cloud", True)
        window._show_dock("Jobs", True)
        save_window_state(window)
        window.show_view(window.model_view)
        window.docks["Jobs"].hide()
        restore_window_state(window)
        QApplication.processEvents()
        assert window.active_view() is window.photo_view
        assert window.model_view.mesh_mode == "wireframe"
        assert window.model_view.solid["cloud"]
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


def test_photo_click_opens_plan_without_reopening_on_table_refresh(window, image_dir, qtbot):
    window.dataset.add_photos([str(next(image_dir.glob("*.jpg")))])
    window.refresh_all()
    QApplication.processEvents()
    item = window.photos.item(0)
    qtbot.mouseClick(window.photos.viewport(), Qt.LeftButton,
                     pos=window.photos.visualItemRect(item).center())
    assert window.active_view() is window.photo_view
    window.show_view(window.model_view)
    window.refresh_all()
    assert window.active_view() is window.model_view


def test_light_theme_restores_readable_base_and_text_after_dark(qapp):
    from photomesh.theme import apply_theme, viewport_color
    from PySide6.QtGui import QPalette
    for theme in ("Dark", "Light", "Dark", "Light"):
        apply_theme(qapp, theme)
    assert qapp.palette().color(QPalette.Base).lightness() > 200
    assert qapp.palette().color(QPalette.Text).lightness() < 100
    assert viewport_color().lightness() > 200
    apply_theme(qapp, "Dark")


def test_camera_table_evaluates_project_gps_policy_once(window, monkeypatch):
    from photomesh import photo_gps
    calls = []
    original = photo_gps.use_photo_gps
    monkeypatch.setattr(photo_gps, "use_photo_gps", lambda dataset: calls.append(dataset) or original(dataset))
    window.dataset.cameras = [Camera(str(i)+".jpg", lon=44., lat=40., alt=100.) for i in range(50)]
    window.reference.refresh(window.dataset)
    assert calls == [window.dataset]


def test_theme_switch_updates_existing_panels_and_photo_labels(window):
    from PySide6.QtGui import QPalette
    from photomesh.theme import apply_theme
    app = QApplication.instance()
    window.dataset.cameras = [Camera("sample.jpg")]
    window.refresh_all()
    for theme in ("Dark", "Light", "Dark", "Light"):
        apply_theme(app, theme)
        QApplication.processEvents()
    for widget in (window.photos, window.photos.viewport(), window.properties, window.reference):
        assert widget.palette().color(QPalette.Base).lightness() > 200
        assert widget.palette().color(QPalette.Text).lightness() < 100
    assert window.main_toolbar.palette().color(QPalette.Button).lightness() > 200
    apply_theme(app, "Dark")


def test_saved_layout_prevents_default_view_overriding_user_choice(window, monkeypatch):
    from photomesh.ui_state import save_window_state, KEY
    settings = QSettings()
    try:
        window.show_view(window.photo_view)
        save_window_state(window)
        calls = []
        monkeypatch.setattr(window, "_solo", calls.append)
        monkeypatch.setattr(window.model_view, "has_layer", lambda key: True)
        window._apply_default_view()
        assert calls == [] and window.active_view() is window.photo_view
    finally:
        settings.remove(KEY)


def test_gps_reference_matching_keeps_same_stem_different_extensions_distinct():
    import numpy as np
    from photomesh import georef as g
    from test_dense_mesh_gcp import synthetic_model
    model = synthetic_model()
    first, second = list(model.images)[:2]
    model.images[first].name = "photo.jpg"
    model.images[second].name = "photo.png"
    crs = g.CRS.parse("EPSG:32638")
    gps = {"photo.jpg": [44., 40., 100.], "photo.png": [44.001, 40.001, 200.]}
    result = g.camera_gps_metric(model, gps, crs)
    assert set(result) == {first, second}
    for iid, label in ((first, "photo.jpg"), (second, "photo.png")):
        lon, lat, altitude = gps[label]
        east, north = g.utm_forward(lat, lon, 38, False)
        assert np.allclose(result[iid], [east, north, altitude])
    assert not g.camera_gps_metric(model, {"photo": [44., 40., 100.]}, crs)
    assert "photo" not in g.name_index(model)  # ambiguous legacy marker names cannot pick either image


def test_each_photo_selection_resets_raster_tools_for_one_click_return(window, image_dir, monkeypatch):
    window.dataset.add_photos([str(next(image_dir.glob("*.jpg")))])
    monkeypatch.setattr(window.ortho_view, "has_raster", lambda kind=None: True)
    window.layer_action("ortho").setChecked(False)
    for _ in range(2):
        window.layer_action("ortho").setChecked(True)
        assert window.active_view() is window.ortho_view
        window.open_photo(0)
        assert window.active_view() is window.photo_view
        assert not window.layer_action("ortho").isChecked()
        window.layer_action("ortho").trigger()
        assert window.active_view() is window.ortho_view
        assert window.layer_action("ortho").isChecked()


def test_export_report_uses_project_name_instead_of_legacy_dataset(window, tmp_path, monkeypatch):
    from photomesh.filedialogs import QFileDialog
    window.project.path = str(tmp_path / "Site & Survey.pmsx")
    window.dataset.name = "Chunk 1"
    window.dataset.cameras = [Camera("a.jpg", label="<camera>")]
    window.dataset.log = ["Processing <complete>"]
    destination = tmp_path / "report.html"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(destination), "HTML")))
    window.actions["Generate Report..."].trigger()
    html = destination.read_text(encoding="utf-8")
    assert "<h2>Site &amp; Survey</h2>" in html
    assert "Chunk 1" not in html
    assert "&lt;camera&gt;" in html and "Processing &lt;complete&gt;" in html
    assert window.dataset.name == "Chunk 1"
    assert destination.with_name("report_view.png").exists()
