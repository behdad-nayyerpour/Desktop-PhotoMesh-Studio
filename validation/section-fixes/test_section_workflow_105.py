"""Complete UI paths for the unified section, including slow and rejected picks."""
import threading
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtWidgets import QPushButton, QMenu
from test_survey_interaction_105 import photo_project, wait_picks
from test_survey_ui_105 import mesh_project


def native_ortho(window, tmp_path):
    from photomesh.geotiff import TiledTiffWriter
    from photomesh.workflow import file_stamp
    mesh = mesh_project(window, tmp_path)
    path = str(tmp_path/'ortho.tif')
    writer = TiledTiffWriter(path, [(256, 256)], 3, tile=256, geo=(0, 10, 10/256, 10/256))
    writer.write_tile(0, 0, 0, np.full((256, 256, 3), 120, np.uint8)); writer.close()
    window.dataset.orthomosaic = dict(path=path, format='photomesh-ortho/1', rotation=np.eye(3).tolist(),
        offset=[0, 0, 0], origin=[0, 10], pixel_size=10/256, source_mesh_stamp=file_stamp(mesh))
    window.load_ortho_view(); window.show_ortho('ortho')


def screen_photo(window, uv):
    return window.photo_view.view.viewportTransform().map(QPointF(*uv)).toPoint()


@pytest.mark.parametrize('kind', ['photo', 'ortho'])
def test_actual_click_move_click_and_all_three_handles(window, tmp_path, qtbot, kind):
    if kind == 'photo':
        from photomesh.colmap_io import project
        camera, image = photo_project(window, tmp_path)
        uv, _ = project(camera, image.R(), image.tvec, np.array([[3, 4, 11], [6, 4, 14]], float))
        widget = window.photo_view.view.viewport()
    else:
        native_ortho(window, tmp_path); widget = window.ortho_view
    window.show_cross_section(); qtbot.wait(20)
    if kind == 'photo':
        window.photo_view.fit()
        positions = [screen_photo(window, p) for p in uv]
    else:
        widget.fit(); positions = [QPoint(*map(round, widget.to_screen(*p))) for p in ([3, 4], [6, 4])]
    assert all(widget.rect().contains(p) for p in positions)
    qtbot.mouseClick(widget, Qt.LeftButton, pos=positions[0]); wait_picks(window, qtbot)
    assert window._survey_dialog.points[0] is not None and window._survey_dialog.points[1] is None
    qtbot.mouseMove(widget, positions[1]); qtbot.mouseClick(widget, Qt.LeftButton, pos=positions[1]); wait_picks(window, qtbot)
    assert window._survey_profile is not None
    assert '3D distance:' in window._survey_dialog.result.text()
    for handle in (0, 1, 2):
        if kind == 'photo':
            pixels = [screen_photo(window, p) for p in window.photo_view._survey_line]
        else:
            pixels = [QPoint(*map(round, widget.to_screen(*p))) for p in widget.survey_line]
        start = pixels[handle] if handle < 2 else (pixels[0]+pixels[1])/2
        end = start + QPoint(6, -6)
        before = np.array(window._survey_dialog.points)
        qtbot.mousePress(widget, Qt.LeftButton, pos=start)
        qtbot.mouseMove(widget, end)
        qtbot.mouseRelease(widget, Qt.LeftButton, pos=end)
        wait_picks(window, qtbot)
        after = np.array(window._survey_dialog.points)
        assert np.linalg.norm(after[handle if handle < 2 else 0]-before[handle if handle < 2 else 0]) > .001
        if handle == 2:
            assert np.linalg.norm(after[1]-before[1]) > .001
        assert window._survey_profile is not None and not window._survey_busy


def test_stale_ortho_never_creates_fake_draft_and_reports_rebuild(window, tmp_path, qtbot):
    native_ortho(window, tmp_path)
    window.dataset.orthomosaic['stale'] = 'built from an earlier model'
    window.show_cross_section(); view = window.ortho_view; view.fit()
    pos = QPoint(*map(round, view.to_screen(4, 4)))
    qtbot.mouseClick(view, Qt.LeftButton, pos=pos)
    assert window._survey_dialog.points == [None, None]
    assert getattr(view, '_survey_anchor', None) is None
    assert 'Build Orthomosaic' in window._survey_dialog.status.text()


def test_slow_geometry_locks_new_drawing_and_restores_after_cancel(window, tmp_path, qtbot, monkeypatch):
    from photomesh import survey_geometry
    photo_project(window, tmp_path); window.show_cross_section()
    entered, release = threading.Event(), threading.Event()
    original = survey_geometry.load_surface
    def delayed(*args, **kwargs):
        entered.set(); release.wait(5)
        return original(*args, **kwargs)
    monkeypatch.setattr(survey_geometry, 'load_surface', delayed)
    window._survey_pick_photo(500, 500)
    qtbot.waitUntil(entered.is_set, timeout=10000)
    try:
        assert window._survey_busy and window.photo_view.survey_busy
        assert window._survey_dialog.progress.isVisible() and window._survey_dialog.cancel.isVisible()
        assert not window._survey_dialog.reset.isEnabled()
        window._survey_pick_photo(510, 510)
        assert not window._survey_pick_queue  # The second request is rejected while preparing.
        window._survey_cancel()
    finally:
        release.set()
    wait_picks(window, qtbot)
    assert window._survey_dialog.points == [None, None]
    assert not window._survey_busy and window._survey_dialog.reset.isEnabled()


def test_photo_context_and_control_edits_are_blocked_then_restored(window, tmp_path, qtbot, monkeypatch):
    photo_project(window, tmp_path)
    photo = window.photo_view
    calls = []; photo.addMarker.connect(lambda *_: calls.append('add'))
    menus = []
    from PySide6 import QtWidgets
    class TestMenu(QMenu):
        def exec(self, *_args):
            menus.append(True)
    monkeypatch.setattr(QtWidgets, 'QMenu', TestMenu)
    window.show_cross_section()
    photo._context(QPoint(100, 100)); photo.ctrl_click(500, 500)
    assert calls == [] and menus == [] and not window.actions['Add Marker'].isEnabled()
    assert window.add_marker_at_photo(500, 500) is None
    photo.view.setFocus()
    qtbot.mouseClick(photo.view.viewport(), Qt.LeftButton, Qt.ControlModifier, pos=QPoint(200, 150))
    assert not window.dataset.markers
    window._survey_dialog.close()
    assert window.actions['Add Marker'].isEnabled()
    photo._context(QPoint(100, 100)); photo.ctrl_click(500, 500)
    assert menus and calls == ['add']


def test_one_survey_command_and_no_pick_buttons(window, tmp_path):
    from photomesh.menus import MENUS
    survey = next(items for name, items in MENUS if name == '&Survey')
    display = next(items for name, items in MENUS if name == '&Display')
    assert 'Cross Section...' in survey and 'Cross Section...' not in display
    assert 'Measure Distance...' not in window.actions
    mesh_project(window, tmp_path); window.show_cross_section()
    texts = [button.text() for button in window._survey_dialog.findChildren(QPushButton)]
    assert 'Pick Start' not in texts and 'Pick End' not in texts


def test_ortho_context_is_blocked_until_panel_closes(window, tmp_path, monkeypatch):
    from photomesh import orthoview
    from PySide6.QtGui import QContextMenuEvent
    native_ortho(window, tmp_path)
    menus = []
    class TestMenu(QMenu):
        def exec(self, *_args):
            menus.append(True)
    monkeypatch.setattr(orthoview, 'QMenu', TestMenu)
    view = window.ortho_view
    window.show_cross_section()
    event = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(20, 20), QPoint(20, 20))
    view.contextMenuEvent(event)
    assert not menus
    window._survey_dialog.close()
    view.contextMenuEvent(event)
    assert menus == [True]


@pytest.mark.parametrize('kind', ['photo', 'ortho'])
def test_double_click_end_is_committed_without_resetting_view(window, tmp_path, qtbot, kind):
    if kind == 'photo':
        photo_project(window, tmp_path)
        widget = window.photo_view.view.viewport()
    else:
        native_ortho(window, tmp_path); widget = window.ortho_view
    window.show_cross_section(); qtbot.wait(20)
    if kind == 'photo':
        window.photo_view.fit()
        start, end = [screen_photo(window, p) for p in ([480, 510], [530, 510])]
    else:
        widget.fit()
        start, end = [QPoint(*map(round, widget.to_screen(*p))) for p in ([4, 4], [6, 4])]
    qtbot.mouseClick(widget, Qt.LeftButton, pos=start); wait_picks(window, qtbot)
    qtbot.mouseDClick(widget, Qt.LeftButton, pos=end)
    qtbot.mouseRelease(widget, Qt.LeftButton, pos=end)
    wait_picks(window, qtbot)
    assert all(point is not None for point in window._survey_dialog.points)
    assert window._survey_profile is not None
