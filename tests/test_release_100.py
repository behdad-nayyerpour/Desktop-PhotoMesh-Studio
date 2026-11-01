"""1.0: observable task lifecycle, references, single-project UI, and stable photos."""
import threading
import time

import numpy as np
import pytest

from PySide6.QtCore import QSettings, QTimer, Qt, QItemSelectionModel
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QProgressBar, QCheckBox
from photomesh.project import Project, Camera, Chunk


def test_theme_switch_is_immediate_and_persistent(qapp):
    from photomesh.dialogs import PreferencesDialog
    from photomesh.theme import apply_theme
    settings = QSettings()
    previous = settings.value("ui/theme", "Dark")
    try:
        dialog = PreferencesDialog()
        dialog.theme.setCurrentText("Light"); dialog._save()
        light = qapp.palette().color(QPalette.Window).lightness()
        assert settings.value("ui/theme") == "Light"
        dialog.theme.setCurrentText("Dark"); dialog._save()
        assert light > qapp.palette().color(QPalette.Window).lightness()
        assert settings.value("ui/theme") == "Dark"
        dialog.deleteLater()
    finally:
        settings.setValue("ui/theme", previous)
        apply_theme(qapp)


def test_reference_selection_does_not_change_usage_and_flags_persist(window, tmp_path):
    window.chunk.cameras = [Camera("a.jpg", lon=44., lat=40., alt=100.),
                            Camera("b.jpg", lon=44.1, lat=40.1, alt=101.)]
    window.refresh_all()
    window.reference.selectRow(1)
    assert all(c.use_reference for c in window.chunk.cameras)
    window.reference.item(1, 0).setCheckState(Qt.Unchecked)
    assert not window.chunk.cameras[1].use_reference
    assert window.chunk.cameras[1].enabled
    path = str(tmp_path / "references.pmsx")
    window.project.save(path)
    assert not Project.load(path).chunk.cameras[1].use_reference


def test_photo_refresh_keeps_identity_selection_and_scroll(window, qtbot):
    window.chunk.cameras = [Camera(f"/survey/photo_{i}.jpg") for i in range(150)]
    window.refresh_all()
    window.photos.resize(500, 200)
    window.photos.show()
    qtbot.wait(30)
    photo = window.photos.item(80)
    window.photos.setCurrentItem(photo, QItemSelectionModel.ClearAndSelect)
    window.photos.scrollToItem(photo)
    qtbot.wait(30)
    before = window.photos.verticalScrollBar().value()
    window.chunk.markers = [{"label": "G1", "enabled": True, "projections": {}}]
    for _ in range(3):
        window.set_modified()
        QApplication.processEvents()
    assert window.photos.item(80) is photo and photo.isSelected()
    assert window.photos.verticalScrollBar().value() == before


def test_status_has_no_progress_widgets_and_only_ready_busy(window):
    assert not window.statusBar().findChildren(QProgressBar)
    assert window.statusBar().currentMessage() == "Ready"
    window.busy_indicator.background("tiles", "Reading 7 of 99 tiles", 7, 99)
    window.statusBar().showMessage("a diagnostic detail")
    assert window.statusBar().currentMessage() == "Busy"
    window.busy_indicator.background("tiles")
    assert window.statusBar().currentMessage() == "Ready"
    window._show_resources({"cpu": 20, "gpu": None})
    assert window.gpu_label.text() == "GPU unavailable"


def test_task_panel_has_two_bars_and_unknown_totals(qtbot):
    from photomesh.activity import ProgressPanel
    panel = ProgressPanel(); qtbot.addWidget(panel)
    panel.update_progress(0, 0, "Reading")
    assert len(panel.findChildren(QProgressBar)) == 2
    assert panel.overall.maximum() == panel.subtask.maximum() == 0
    panel.update_progress(2, 5, "Reading")
    assert panel.overall.value() == panel.subtask.value() == 2


def test_run_modal_uses_two_bars_and_keeps_event_loop_alive(window):
    from photomesh.bgjob import run_modal
    ticks = []
    timer = QTimer(); timer.setInterval(5); timer.timeout.connect(lambda: ticks.append(1)); timer.start()
    worker_threads = []
    main = threading.get_ident()
    def work(report, stop):
        worker_threads.append(threading.get_ident())
        for i in range(5):
            time.sleep(.01); report(i + 1, 5, "Working")
        return 42
    try:
        result, cancelled, error = run_modal(window, "Test", "Working", work, 5)
    finally:
        timer.stop()
    assert (result, cancelled, error) == (42, False, None)
    assert ticks and worker_threads[0] != main
    assert not window.busy_indicator.active


def test_open_project_is_transactional_and_load_runs_off_gui(window, tmp_path, monkeypatch):
    from photomesh import project_loader
    path = str(tmp_path / "new.pmsx")
    Project().save(path)
    original = Project.load
    seen = []
    main = threading.get_ident()
    def load(p):
        seen.append(threading.get_ident())
        time.sleep(.03)
        return original(p)
    monkeypatch.setattr(project_loader.Project, "load", load)
    window.open_project(path)
    assert seen and seen[0] != main
    assert window.project.path == path and not window._opening
    current = window.project
    bad = tmp_path / "broken.pmsx"; bad.write_text("{broken")
    window.open_project(str(bad))
    assert window.project is current and not window._opening


def test_cancelled_project_open_keeps_current_project(window, tmp_path, monkeypatch):
    import photomesh.mainwindow as mw
    current = window.project
    monkeypatch.setattr(mw, "run_modal", lambda *a, **k: (None, True, None))
    window.open_project(str(tmp_path / "cancelled.pmsx"))
    assert window.project is current and not window._opening


def test_legacy_multi_dataset_open_never_drops_data(tmp_path):
    from photomesh.project_loader import prepare_project
    project = Project(); project.chunks.append(Chunk(name="Second"))
    path = str(tmp_path / "legacy.pmsx"); project.save(path)
    before = open(path, "rb").read()
    with pytest.raises(ValueError, match="multiple chunks"):
        prepare_project(path, lambda *args: None, lambda: False)
    assert open(path, "rb").read() == before
    assert len(Project.load(path).chunks) == 2


def test_workspace_root_is_project_and_markers_share_flag_icons(window):
    from photomesh import georef as g
    window.chunk.markers = [g.Marker("G1", locked=True).to_dict()]
    window.refresh_all()
    root = window.workspace.topLevelItem(0)
    assert root.data(0, Qt.UserRole)[0] == "project"
    assert not any("chunk" == (item.data(0, Qt.UserRole) or [None])[0]
                   for item in window.workspace._iter())
    assert not window.markers_pane.item(0, 0).icon().isNull()
    assert window.reference_panel.count() == 2


def test_native_dialogs_default_and_explicit_fallback(monkeypatch, qapp):
    from photomesh.mainwindow import apply_dialog_setting
    settings = QSettings(); old = settings.value("ui/qt_file_dialogs", False, bool)
    monkeypatch.delenv("PHOTOMESH_QT_DIALOGS", raising=False)
    try:
        settings.setValue("ui/qt_file_dialogs", False)
        assert not apply_dialog_setting()
        assert not qapp.testAttribute(Qt.AA_DontUseNativeDialogs)
        settings.setValue("ui/qt_file_dialogs", True)
        assert apply_dialog_setting()
        assert qapp.testAttribute(Qt.AA_DontUseNativeDialogs)
    finally:
        settings.setValue("ui/qt_file_dialogs", old); apply_dialog_setting()


def test_alignment_settings_only_expose_functional_options(qtbot):
    from photomesh.dialogs import AlignPhotosDialog, BuildModelDialog
    dialog = AlignPhotosDialog(); qtbot.addWidget(dialog)
    assert not hasattr(dialog, "tie_limit") and not hasattr(dialog, "adaptive")
    dialog.reference.setChecked(False)
    assert not dialog.settings()["reference"]
    dialog.mode.setCurrentText("Sequential")
    assert dialog.settings()["sequential"] and not dialog.reference.isEnabled()
    mesh = BuildModelDialog(); qtbot.addWidget(mesh)
    assert not hasattr(mesh, "surface") and not hasattr(mesh, "vcolors")
    mesh.face_count.setCurrentText("Custom")
    assert mesh.custom.isEnabled()


def test_flag_has_an_exact_coloured_ground_point(qapp):
    from PySide6.QtGui import QImage, QPainter
    from photomesh.marker_style import draw_flag, color
    image = QImage(50, 50, QImage.Format_ARGB32); image.fill(Qt.transparent)
    painter = QPainter(image)
    draw_flag(painter, 10, 35, color("pinned")); painter.end()
    assert image.pixelColor(10, 35).green() > image.pixelColor(10, 35).red()
    assert image.pixelColor(15, 16).alpha() > 0


def test_default_view_setting_selects_loaded_product(window):
    setting = QSettings(); old = setting.value("ui/default_view", "Point cloud")
    try:
        window.model_view.set_points("tie", np.array([[1., 2., 3.]], np.float32))
        setting.setValue("ui/default_view", "Tie points")
        window._apply_default_view()
        assert window.layer_states()["tie"]
    finally:
        setting.setValue("ui/default_view", old)
