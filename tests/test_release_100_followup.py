"""1.0.0 follow-up: readable GL text, inline errors, owned Properties and input cursors."""
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtWidgets import QApplication
from photomesh import georef as g
from photomesh.project import Camera


@pytest.mark.parametrize("dpr", [1., 2.])
def test_gl_target_never_receives_font_glyph_draws(qapp, dpr):
    from photomesh.overlay3d import Overlay
    class ImageOnlyTextPainter(QPainter):
        image_calls = 0
        def drawText(self, *args):
            raise AssertionError("Text must be rasterized before reaching the GL target")
        def drawImage(self, *args):
            self.image_calls += 1
            return super().drawImage(*args)
    image = QImage(int(320*dpr), int(240*dpr), QImage.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(dpr); image.fill(QColor(150, 130, 100))
    overlay = Overlay()
    target = ImageOnlyTextPainter(image)
    try:
        rectangles = overlay.paint(target, [("marker", (120., 100.), "GCP65",
                                           QColor(40, 220, 60), False, None)], 320, 240)
    finally:
        target.end()
    assert len(rectangles) == 1 and target.image_calls >= 2
    assert overlay._text_cache
    assert overlay._legend_cache[1].devicePixelRatio() == dpr
    assert "hollow" not in str(overlay._legend_cache[0])
    assert all(p.width() > 0 for p in overlay._text_cache.values())


def test_marker_errors_are_exactly_two_inline_nonentity_rows(window):
    ch = window.dataset
    ch.markers = [g.Marker("A").to_dict(), g.Marker("B").to_dict(),
                  g.Marker("C", enabled=False).to_dict(), g.Marker("D", disabled=True).to_dict()]
    ch.georef = {"rows": [{"label": "A", "total": 3., "pix": 2., "n": 1},
                         {"label": "B", "total": 4., "pix": 4., "n": 3},
                         {"label": "C", "total": 12., "pix": 6., "n": 1},
                         {"label": "D", "total": 1000., "pix": 1000., "n": 1}]}
    window.refresh_all()
    table = window.markers_pane
    assert table.data_row_count == 4 and table.rowCount() == 6
    assert table.summary_rows == {"Control points": 4, "Check points": 5}
    assert table.item(4, 5).text() == "3.536" and table.item(4, 7).text() == "3.606"
    assert table.item(5, 5).text() == "12.000" and table.item(5, 7).text() == "6.000"
    assert not hasattr(table, "_summary_label")
    activated = []
    table.markerActivated.connect(activated.append)
    for row in (4, 5):
        assert table.item(row, 0).data(Qt.UserRole) is None
        assert not table.item(row, 0).flags() & Qt.ItemIsEditable
        assert not table.item(row, 0).flags() & Qt.ItemIsSelectable
        table.setCurrentCell(row, 0)
        assert table.current_label() is None and table.selected_labels() == []
        table._dbl(row, 7)
    assert activated == []
    for group in (1, 2, 0):
        table.filter_group(group)
        assert not table.isRowHidden(4) and not table.isRowHidden(5)


def test_camera_error_footer_is_under_error_column_and_not_a_camera(window):
    east, north = g.utm_forward(np.array([40.]), np.array([44.]), 38, False)
    E, N = float(east[0]), float(north[0])
    ch = window.dataset
    ch.crs = "EPSG:32638"
    ch.georef = {"crs": ch.crs, "offset": [0., 0., 0.]}
    ch.cameras = [Camera("A.jpg", lon=44., lat=40., alt=100., est=[E+3, N+4, 100.]),
                  Camera("B.jpg", lon=44., lat=40., alt=100., est=[E+1000, N, 100.],
                         use_reference=False)]
    window.refresh_all()
    table = window.reference
    assert table.data_row_count == 2 and table.rowCount() == 3
    assert table.summary_row == 2
    assert table.item(2, 0).text() == "Total Error"
    assert table.item(2, 5).text() == "5.000"
    assert all(table.item(2, column).text() == "" for column in (1, 2, 3, 4, 6, 7, 8))
    assert not hasattr(table, "_summary_label")
    activated = []
    table.cameraActivated.connect(activated.append)
    table._activate_camera(2, 0)
    assert activated == []


def test_properties_belongs_to_workspace_only_and_uses_compact_rows(window):
    assert "Properties" not in window.docks
    assert "View/Properties" not in window.actions
    workspace = window.docks["Workspace"].widget()
    assert workspace is window.workspace_splitter
    assert workspace.isAncestorOf(window.properties)
    assert not window.reference_panel.isAncestorOf(window.properties)
    assert window.reference_panel.widget(0) is window.reference
    window.properties.show_props({f"Property {i}": f"Value {i}" for i in range(30)})
    assert window.properties.rowCount() == 30
    assert window.properties.rowHeight(0) <= max(18, window.properties.fontMetrics().height()+2)
    assert not window.properties.wordWrap()


@pytest.mark.parametrize("kind", ["PreferencesDialog", "AlignPhotosDialog"])
def test_interactive_settings_release_wait_cursor_and_restore_remaining_work(window, qtbot, kind):
    from photomesh import dialogs
    busy = window.busy_indicator
    dialog = getattr(dialogs, kind)(window); qtbot.addWidget(dialog)
    busy.begin("Preparing settings")
    try:
        assert QApplication.overrideCursor() is not None
        dialog.show(); QApplication.processEvents()
        assert QApplication.overrideCursor() is None
        assert busy.active
        dialog.hide(); QApplication.processEvents()
        assert QApplication.overrideCursor() is not None
    finally:
        dialog.hide()
        busy.end()
    assert QApplication.overrideCursor() is None


def test_finishing_background_work_during_settings_does_not_revive_cursor(window, qtbot):
    from photomesh.dialogs import PreferencesDialog
    busy = window.busy_indicator
    dialog = PreferencesDialog(window); qtbot.addWidget(dialog)
    busy.background("preview", "Preparing preview")
    try:
        dialog.show(); QApplication.processEvents()
        assert QApplication.overrideCursor() is None
        busy.background("preview")
        dialog.hide(); QApplication.processEvents()
        assert not busy.active and QApplication.overrideCursor() is None
    finally:
        dialog.hide()
        busy.background("preview")


def test_processing_dialog_keeps_wait_cursor(window, qtbot):
    from photomesh.dialogs import ProgressDialog
    dialog = ProgressDialog("Processing", window); qtbot.addWidget(dialog)
    busy = window.busy_indicator
    busy.begin("Processing")
    try:
        dialog.show(); QApplication.processEvents()
        assert QApplication.overrideCursor() is not None
    finally:
        dialog.running = False; dialog.close()
        busy.end()
    assert QApplication.overrideCursor() is None


def test_theme_reuses_native_style_when_stylesheet_wraps_it(qapp, monkeypatch):
    from photomesh.theme import apply_theme
    apply_theme(qapp, "Dark")
    calls = []
    original = qapp.setStyle
    def record(*args):
        calls.append(args)
        return original(*args)
    monkeypatch.setattr(qapp, "setStyle", record)
    for name in ("Dark", "Light", "Dark"):
        apply_theme(qapp, name)
    assert calls == []


def test_left_tabs_extend_beside_all_bottom_panes(window):
    assert window.corner(Qt.BottomLeftCorner) == Qt.LeftDockWidgetArea
    window.resize(1500, 920)
    for left_name in ("Workspace", "Reference"):
        left = window.docks[left_name]
        left.show(); left.raise_()
        for bottom_name in ("Photos", "Console", "Jobs"):
            bottom = window.docks[bottom_name]
            bottom.show(); bottom.raise_()
            QApplication.processEvents()
            assert left.geometry().bottom() > bottom.geometry().top()
            assert bottom.geometry().left() > left.geometry().right()
            assert abs(bottom.geometry().left() - window.tabs.geometry().left()) <= 2
            gap = window.statusBar().geometry().top() - left.geometry().bottom()
            assert 0 <= gap <= 2 * window.fontMetrics().height() + 12
