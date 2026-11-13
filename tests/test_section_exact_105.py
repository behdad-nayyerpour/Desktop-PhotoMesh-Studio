"""Mesh-plane geometry, surface-bound display, and equal-scale profile fitting."""
import numpy as np
import pytest
from PySide6.QtCore import QPointF
from photomesh.survey_geometry import MeshSurface, section_plot_data
from photomesh.survey_gestures import LineGesture
from test_survey_interaction_105 import wait_picks
from test_survey_ui_105 import mesh_project


def extruded_outline():
    # A roof folds back over the floor: three elevations at x=2.5.
    outline = np.array([[0, 0], [4, 0], [4, 3], [2, 3], [3, 2], [1, 2], [0, 1]], float)
    vertices = np.array([[x, y, z] for y in (-1, 1) for x, z in outline])
    n = len(outline)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend([[i, j, i+n], [j, j+n, i+n]])
    return outline, vertices, np.array(faces)


def test_exact_section_retains_floor_vertical_wall_and_reverse_overhang():
    outline, vertices, faces = extruded_outline()
    segments = MeshSurface(vertices, faces).section_segments([0, 0], [4, 0])
    # Every output endpoint lies on an actual outline edge, and total length
    # equals that outline: no dropped layers or invented connections.
    delta = np.roll(outline, -1, axis=0) - outline
    np.testing.assert_allclose(np.linalg.norm(segments[:, 1]-segments[:, 0], axis=1).sum(),
                               np.linalg.norm(delta, axis=1).sum(), atol=1e-10)
    for p in segments.reshape(-1, 2):
        t = np.clip(np.einsum('ij,ij->i', p-outline, delta)/(delta*delta).sum(1), 0, 1)
        assert np.linalg.norm(outline+t[:, None]*delta-p, axis=1).min() < 1e-10
    heights = []
    for a, b in segments:
        if min(a[0], b[0]) < 2.4 < max(a[0], b[0]):
            heights.append(a[1]+(2.4-a[0])/(b[0]-a[0])*(b[1]-a[1]))
    np.testing.assert_allclose(sorted(heights), [0, 2, 2.6, 3])
    _, _, components = section_plot_data(segments)
    assert len(set(components)) == 1


def test_coplanar_face_boundary_is_clipped_without_interior_diagonal():
    vertices = np.array([[0, 0, 0], [4, 0, 0], [4, 0, 4], [0, 0, 4]], float)
    mesh = MeshSurface(vertices, np.array([[0, 1, 2], [0, 2, 3]]))
    segments = mesh.section_segments([1, 0], [3, 0])
    np.testing.assert_allclose(np.linalg.norm(segments[:, 1]-segments[:, 0], axis=1).sum(), 12)
    for a, b in segments:
        assert ((abs(a[0]-b[0]) < 1e-10 and (abs(a[0]) < 1e-10 or abs(a[0]-2) < 1e-10))
                or (abs(a[1]-b[1]) < 1e-10 and a[1] in (0, 4)))


def test_shared_mesh_edge_is_not_duplicated_and_layers_do_not_connect():
    base = np.array([[0, -1, 0], [2, 0, 0], [0, 0, 0], [0, 1, 0]], float)
    vertices = np.vstack([base, base+[0, 0, 3]])
    faces = np.array([[0, 1, 2], [3, 2, 1], [4, 5, 6], [7, 6, 5]])
    segments = MeshSurface(vertices, faces).section_segments([0, 0], [2, 0])
    assert segments.shape == (2, 2, 2)
    along, z, components = section_plot_data(segments)
    assert len(set(components)) == 2
    assert np.isnan(along[2::3]).all() and np.isnan(z[2::3]).all()


def test_real_hole_and_reversed_span_at_large_coordinate_origin():
    from test_survey_geometry_105 import surface
    original = surface()
    shifted = MeshSurface(original.triangles.reshape(-1, 3)+[500000, 4500000, 100],
                          np.arange(original.triangles.size//3).reshape(-1, 3))
    segments = shifted.section_segments([500002.75, 4500000.5], [500000.25, 4500000.5])
    assert np.all(segments[:, :, 0] >= 0) and np.all(segments[:, :, 0] <= 2.5)
    np.testing.assert_allclose(segments[:, :, 1], 103.75-segments[:, :, 0], atol=1e-9)
    assert not np.any((segments[:, :, 0] > .75) & (segments[:, :, 0] < 1.75))
    assert len(set(section_plot_data(segments)[2])) == 2
    with pytest.raises(InterruptedError):
        shifted.section_segments([500000, 4500000], [500003, 4500000], cancel=lambda: True)
    assert shifted.section_segments([0, 0], [1, 0]).shape == (0, 2, 2)


def test_one_to_one_button_fits_entire_profile_with_equal_pixel_units(window, tmp_path, qtbot):
    mesh_project(window, tmp_path)
    window.show_cross_section()
    panel = window._survey_dialog
    panel.curve.setData([0, 1, np.nan, 8, 9], [0, 20, np.nan, -4, -3])
    panel.fit_equal.click(); qtbot.wait(20)
    view = panel.plot.plotItem.vb
    origin = view.mapViewToScene(QPointF(0, 0))
    x = view.mapViewToScene(QPointF(1, 0))
    y = view.mapViewToScene(QPointF(0, 1))
    assert abs(abs(x.x()-origin.x())-abs(y.y()-origin.y())) < 1e-6
    (xmin, xmax), (ymin, ymax) = view.viewRange()
    assert xmin <= 0 and xmax >= 9 and ymin <= -4 and ymax >= 20


def test_surface_display_and_middle_handle_use_actual_mesh_not_endpoint_chord(window, tmp_path, qtbot, monkeypatch):
    from photomesh.plyio import save_ply
    import photomesh.views as views
    outline, vertices, faces = extruded_outline()
    path = mesh_project(window, tmp_path)
    save_ply(str(path), vertices, faces=faces)
    window.show_cross_section()
    window._survey_pick_ray([0, 0, 10], [0, 0, -1]); wait_picks(window, qtbot)
    window._survey_pick_ray([4, 0, 10], [0, 0, -1]); wait_picks(window, qtbot)
    along, z = window._survey_profile
    assert np.nanmin(z) == 0 and np.nanmax(z) == 3
    view = window.model_view
    # Exercise the rendering contract even on the offscreen test platform.
    captured = {}
    class Item:
        def __init__(self, **kw): captured.update(kw)
        def setGLOptions(self, options): captured['options'] = options
        def setDepthValue(self, value): pass
    class Canvas:
        def addItem(self, item): pass
        def removeItem(self, item): pass
        def update(self): pass
    monkeypatch.setattr(views.gl, 'GLLinePlotItem', Item)
    monkeypatch.setattr(view, 'gl', Canvas())
    xyz = np.column_stack([along, np.zeros(len(along)), z])
    view.set_survey_surface(xyz, [2, 0, 3])
    assert captured['mode'] == 'lines'
    np.testing.assert_allclose(captured['pos']/view.flip, xyz.reshape(-1, 3, 3)[:, :2].reshape(-1, 3))
    assert captured['options'][views._GL.GL_DEPTH_TEST] is True
    # A middle handle on a roof, away from the straight endpoint midpoint,
    # still moves both endpoints. A normal drag remains navigation.
    gesture = LineGesture()
    assert gesture.start([40, 80], [[0, 0], [80, 0]], center=[40, 80])
    edits = gesture.move([45, 87])
    assert [i for i, _ in edits] == [0, 1]
    assert not gesture.start([40, 40], [[0, 0], [80, 0]], center=[40, 80])
    window._survey_dialog.close()
    assert view.layers.get('survey_line') is None and view._survey_surface_center is None


def test_profile_click_selects_correct_layer_and_rejects_slope_across_gap(window, tmp_path):
    from PySide6.QtCore import Qt
    mesh_project(window, tmp_path); window.show_cross_section()
    panel = window._survey_dialog
    segments = np.array([[[0, 0], [2, 0]], [[0, 3], [2, 3]]], float)
    along, z, components = section_plot_data(segments)
    window._survey_profile = along, z
    window._survey_profile_components = components
    panel.curve.setData(along, z, connect='finite'); panel.fit_equal.click()
    def click(x, y):
        class Event:
            def button(self): return Qt.LeftButton
            def scenePos(self): return panel.plot.plotItem.vb.mapViewToScene(QPointF(x, y))
        window._survey_profile_clicked(Event())
    click(.7, 3)
    np.testing.assert_allclose(window._survey_selected[0][0], [.7, 3])
    click(1.5, 0)
    assert 'mesh gap' in panel.result.text()
