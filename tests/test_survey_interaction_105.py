"""User gestures, dock lifetime and calibrated picks against actual geometry."""
import numpy as np
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent
from photomesh.survey_gestures import LineGesture
from test_survey_ui_105 import mesh_project


def wait_picks(window, qtbot):
    qtbot.waitUntil(lambda: getattr(window, '_survey_pick_job', None) is None and not window._survey_pick_queue and not window._survey_busy, timeout=10000)


def photo_project(window, tmp_path):
    from PIL import Image
    from photomesh import colmap_io as cio
    from photomesh.project import Camera
    from test_dense_mesh_gcp import synthetic_model
    mesh_project(window, tmp_path)
    path = str(tmp_path / 'photo.jpg')
    Image.new('RGB', (1000, 1000), (100, 120, 140)).save(path)
    model = synthetic_model(n_img=2, n_pts=40, two_cameras=False)
    camera = cio.Camera(4, 1000, 1000, np.array([1000., 1000., 500., 500., .02, -.001, .001, -.001]))
    rotation = np.diag([1., -1., -1.])
    image = cio.Image('photo.jpg', 1, cio.rot_to_qvec(rotation), -rotation @ [5., 5., 50.], np.empty((0, 2)), np.empty(0, np.int64))
    model.cameras, model.images = {1: camera}, {1: image}
    directory = window._model_dir()
    cio.write_model(directory, model)
    window.dataset.cameras = [Camera(path, aligned=True, width=1000, height=1000, colmap_name='photo.jpg')]
    window.open_photo(0)
    return camera, image


@pytest.mark.parametrize('section', [False, True])
def test_both_tools_use_closable_nonfloating_bottom_panel(window, tmp_path, section):
    mesh_project(window, tmp_path)
    window._open_survey(section)
    panel = window._survey_dialog
    assert window.dockWidgetArea(panel) == Qt.BottomDockWidgetArea
    assert not panel.isFloating()
    assert window.model_view.survey_enabled and window.photo_view.survey_enabled and window.ortho_view.survey_enabled
    from PySide6.QtWidgets import QPushButton
    close = panel.findChild(QPushButton, 'surveyClose')
    assert close.isVisible()
    close.click()
    assert not window.model_view.survey_enabled and not window.photo_view.survey_enabled


def test_draft_is_live_and_does_not_compute_a_section(window, tmp_path, qtbot):
    mesh_project(window, tmp_path)
    window.show_cross_section()
    window._survey_pick_ray([1, 1, 50], [0, 0, -1]); wait_picks(window, qtbot)
    assert window._survey_profile is None and window._survey_pending is None
    assert window.model_view._survey_anchor is not None
    assert window.model_view._survey_line is None
    window._survey_pick_ray([4, 1, 50], [0, 0, -1]); wait_picks(window, qtbot)
    qtbot.waitUntil(lambda: window._survey_profile is not None, timeout=10000)
    along, heights = window._survey_profile
    np.testing.assert_allclose(heights, along + 3, atol=1e-6)
    assert window.model_view._survey_anchor is None
    assert window.model_view._survey_line.shape == (2, 3)


def test_photo_picks_use_actual_calibration_and_mesh_and_keep_overlay_on_rotated_photo(window, tmp_path, qtbot):
    from photomesh.colmap_io import project
    camera, image = photo_project(window, tmp_path)
    points = np.array([[1, 1, 3], [4, 5, 14]], float)
    pixels, _ = project(camera, image.R(), image.tvec, points)
    window.show_measurement()
    window._survey_pick_photo(*pixels[0]); wait_picks(window, qtbot); window._survey_pick_photo(*pixels[1]); wait_picks(window, qtbot)
    np.testing.assert_allclose(window._survey_endpoints_model, points, atol=1e-7)
    np.testing.assert_allclose(window.photo_view._survey_line, pixels, atol=1e-7)
    window.rotate_photo(90)
    for pixel in pixels:
        screen = window.photo_view.view.viewportTransform().map(QPointF(*pixel))
        np.testing.assert_allclose(window.photo_view._survey_scene_point([screen.x(), screen.y()]), pixel, atol=1e-9)
    before = window._survey_dialog.points[0].copy()
    # An invalid paired move is atomic: it cannot move only the first endpoint.
    window._survey_edit_photo([(0, *pixels[0]), (1, 1e6, 1e6)])
    np.testing.assert_array_equal(window._survey_dialog.points[0], before)


def test_photo_section_endpoint_drag_and_middle_pair_recalculate(window, tmp_path, qtbot):
    from photomesh.colmap_io import project
    camera, image = photo_project(window, tmp_path)
    window.show_cross_section()
    def pixels(points):
        return project(camera, image.R(), image.tvec, np.asarray(points))[0]
    uv = pixels([[1, 1, 3], [4, 1, 6]])
    window._survey_pick_photo(*uv[0]); wait_picks(window, qtbot); window._survey_pick_photo(*uv[1]); wait_picks(window, qtbot)
    moved = np.array([[2, 2, 6], [5, 2, 9]], float)
    uv2 = pixels(moved)
    window._survey_edit_photo([(0, *uv2[0]), (1, *uv2[1])]); wait_picks(window, qtbot)
    qtbot.waitUntil(lambda: window._survey_profile is not None, timeout=10000)
    np.testing.assert_allclose(window._survey_dialog.points, moved[:, :2], atol=1e-7)
    np.testing.assert_allclose(window._survey_profile[1], window._survey_profile[0] + 6, atol=1e-7)


@pytest.mark.parametrize('section', [False, True])
def test_ortho_supports_both_tools_and_atomic_middle_translation(window, tmp_path, qtbot, section, monkeypatch):
    mesh_project(window, tmp_path)
    window._open_survey(section)
    monkeypatch.setattr(window, '_survey_ortho_rotation', lambda: np.eye(3))
    window._survey_pick_plan(1, 1); wait_picks(window, qtbot); window._survey_pick_plan(4, 1); wait_picks(window, qtbot)
    window._survey_edit_plan([(0, 2, 2), (1, 5, 2)]); wait_picks(window, qtbot)
    expected = np.array([[2, 2, 6], [5, 2, 9]], float)
    np.testing.assert_allclose(window._survey_dialog.points, expected[:, :2], atol=1e-7)
    if section:
        qtbot.waitUntil(lambda: window._survey_profile is not None, timeout=10000)


def test_middle_and_endpoint_screen_gestures_do_not_capture_normal_rotation():
    line = np.array([[20., 20.], [120., 20.]])
    gesture = LineGesture()
    assert gesture.start([70, 20], line) and gesture.editing == 2
    edits = gesture.move([80, 35])
    np.testing.assert_allclose([p for _, p in edits], line + [10, 15])
    assert not gesture.finish([80, 35])
    assert gesture.start([20, 20], line) and gesture.editing == 0
    assert gesture.move([25, 30])[0][0] == 0
    assert not gesture.start([200, 100], line)
    assert gesture.move([250, 100]) is None
    assert not gesture.finish([200, 100])  # returning to press does not turn a drag into a click.


def test_model_filter_passes_rotation_and_wheel_and_emits_click_on_release(window, tmp_path, monkeypatch):
    mesh_project(window, tmp_path); window.show_measurement()
    view = window.model_view
    monkeypatch.setattr(view, 'ray_at', lambda x, y: (np.array([1, 1, 50]), np.array([0, 0, -1])))
    hits = []; view.surveyRay.connect(lambda *_: hits.append(True))
    def event(kind, x, y, button, buttons):
        return QMouseEvent(kind, QPointF(x, y), QPointF(x, y), button, buttons, Qt.NoModifier)
    assert not view.eventFilter(view, event(QEvent.MouseButtonPress, 100, 100, Qt.LeftButton, Qt.LeftButton))
    assert hits == []
    assert not view.eventFilter(view, event(QEvent.MouseMove, 140, 100, Qt.NoButton, Qt.LeftButton))
    assert not view.eventFilter(view, event(QEvent.MouseButtonRelease, 140, 100, Qt.LeftButton, Qt.NoButton))
    assert hits == []
    view.eventFilter(view, event(QEvent.MouseButtonPress, 100, 100, Qt.LeftButton, Qt.LeftButton))
    view.eventFilter(view, event(QEvent.MouseButtonRelease, 100, 100, Qt.LeftButton, Qt.NoButton))
    assert hits == [True]


def test_photo_mouse_preview_tracks_cursor_without_geometry_work(window, tmp_path, qtbot):
    photo_project(window, tmp_path)
    window.show_measurement()
    window._survey_pick_photo(500, 500); wait_picks(window, qtbot)
    view = window.photo_view
    assert view._survey_preview_item is not None
    qtbot.mouseMove(view.view.viewport(), QPoint(200, 150))
    line = view._survey_preview_item.line()
    expected = view._survey_scene_point([200, 150])
    np.testing.assert_allclose([line.x2(), line.y2()], expected)
    assert window._survey_dialog.points[1] is None and window._survey_profile is None


def test_manual_coordinates_and_close_reopen_do_not_accept_old_worker(window, tmp_path, qtbot):
    mesh_project(window, tmp_path); window.show_measurement()
    first = window._survey_dialog
    window._survey_pick_ray([1, 1, 50], [0, 0, -1])
    window.show_measurement()
    qtbot.waitUntil(lambda: getattr(window, '_survey_pick_job', None) is None, timeout=10000)
    assert window._survey_dialog is not first and window._survey_dialog.points == [None, None]
    for row, values in enumerate(([1, 2, 3], [4, 6, 15])):
        for box, value in zip(window._survey_dialog.coordinates[row], values):
            box.setValue(value)
    wait_picks(window, qtbot)
    assert 'Horizontal: 5' in window._survey_dialog.result.text()
    assert '3D distance: 12.083' in window._survey_dialog.result.text()


def test_photo_middle_handle_drag_moves_both_endpoints_without_panning(window, tmp_path, qtbot):
    from photomesh.colmap_io import project
    camera, image = photo_project(window, tmp_path)
    window.show_measurement()
    uv, _ = project(camera, image.R(), image.tvec, np.array([[1, 1, 3], [7, 1, 9]], float))
    window._survey_pick_photo(*uv[0]); wait_picks(window, qtbot); window._survey_pick_photo(*uv[1]); wait_picks(window, qtbot)
    photo = window.photo_view
    pixels = [photo.view.viewportTransform().map(QPointF(*p)) for p in photo._survey_line]
    mid = (pixels[0] + pixels[1]) / 2
    before = np.array(window._survey_endpoints_model)
    transform = photo.view.viewportTransform()
    qtbot.mousePress(photo.view.viewport(), Qt.LeftButton, pos=mid.toPoint())
    assert photo._survey_gesture.editing == 2
    qtbot.mouseMove(photo.view.viewport(), (mid + QPointF(8, -5)).toPoint())
    qtbot.mouseRelease(photo.view.viewport(), Qt.LeftButton, pos=(mid + QPointF(8, -5)).toPoint())
    wait_picks(window, qtbot)
    assert photo.view.viewportTransform() == transform
    after = np.array(window._survey_endpoints_model)
    assert np.linalg.norm(after[0] - before[0]) > .01 and np.linalg.norm(after[1] - before[1]) > .01
    # Both new hits still lie on the independently known plane z=x+2*y.
    np.testing.assert_allclose(after[:, 2], after[:, 0] + 2*after[:, 1], atol=1e-7)


def test_ortho_real_mouse_drag_selects_midpoint_and_keeps_line_parallel(window, tmp_path, qtbot, monkeypatch):
    mesh_project(window, tmp_path); window.show_measurement()
    monkeypatch.setattr(window, '_survey_ortho_rotation', lambda: np.eye(3))
    view = window.ortho_view
    view.center, view.scale = (5, 5), 20
    window.show_view(view)
    window._survey_pick_plan(1, 1); wait_picks(window, qtbot); window._survey_pick_plan(5, 1); wait_picks(window, qtbot)
    before = view.survey_line.copy(); mid = np.mean([view.to_screen(*p) for p in before], axis=0)
    start = QPoint(round(mid[0]), round(mid[1])); end = start + QPoint(10, -10)
    qtbot.mousePress(view, Qt.LeftButton, pos=start)
    assert view._survey_gesture.editing == 2
    qtbot.mouseMove(view, end); qtbot.mouseRelease(view, Qt.LeftButton, pos=end)
    wait_picks(window, qtbot)
    np.testing.assert_allclose(view.survey_line, before + [.5, .5], atol=1e-7)
    assert view.center == (5, 5)


def test_rotated_ortho_and_world_offset_roundtrip_keep_actual_model_endpoints(window, tmp_path, qtbot, monkeypatch):
    from scipy.spatial.transform import Rotation
    mesh_project(window, tmp_path)
    offset = np.array([500000., 4500000., 100.])
    window.dataset.georef = {'offset': offset.tolist(), 'crs': 'EPSG:32638'}
    rotation = Rotation.from_euler('x', 20, degrees=True).as_matrix()
    monkeypatch.setattr(window, '_survey_ortho_rotation', lambda: rotation)
    window.show_measurement()
    actual = np.array([[1., 1., 3.], [4., 2., 8.]])
    projected = actual @ rotation.T + offset
    for point in projected:
        window._survey_pick_plan(*point[:2]); wait_picks(window, qtbot)
    wait_picks(window, qtbot)
    np.testing.assert_allclose(window._survey_dialog.points, projected[:, :2], atol=1e-7)
    np.testing.assert_allclose(window.model_view._survey_line, actual, atol=1e-7)
    # The complete section, not just its endpoint labels, uses the same frame.
    along, elevations = window._survey_profile
    direction = (projected[1, :2]-projected[0, :2])/np.linalg.norm(projected[1, :2]-projected[0, :2])
    local = np.column_stack([projected[0, :2]-offset[:2]+along[:, None]*direction,
                             elevations-offset[2]]) @ rotation
    finite = np.isfinite(local).all(1)
    np.testing.assert_allclose(local[finite, 2], local[finite, 0]+2*local[finite, 1], atol=1e-7)


def test_photo_resolution_scaling_and_unaligned_guard(window, tmp_path, qtbot):
    from photomesh import colmap_io as cio
    camera, image = photo_project(window, tmp_path)
    point = np.array([[3., 2., 7.]])
    pixels, _ = cio.project(camera, image.R(), image.tvec, point)
    camera.width = camera.height = 500
    camera.params[:4] *= .5
    model = window._sparse_model(); model.cameras[1] = camera
    cio.write_model(window._model_dir(), model)
    window.show_measurement(); window._survey_pick_photo(*pixels[0]); wait_picks(window, qtbot)
    np.testing.assert_allclose(window._survey_endpoints_model[0], point[0], atol=1e-7)
    window._survey_clear(); window.dataset.cameras[0].aligned = False
    window._survey_pick_photo(*pixels[0])
    assert window._survey_dialog.points == [None, None]
    assert 'Align this photo' in window._survey_dialog.status.text()
