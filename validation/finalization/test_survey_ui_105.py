import os
import numpy as np
from photomesh.plyio import save_ply
from photomesh.project import Project


def mesh_project(window, tmp_path):
    window.project.path = str(tmp_path / 'survey.pmsx')
    path = tmp_path / 'mesh.ply'
    vertices = np.array([[0, 0, 0], [10, 0, 10], [0, 10, 20], [10, 10, 30]], float)
    save_ply(str(path), vertices, faces=np.array([[0, 1, 2], [1, 3, 2]], np.int32))
    window.dataset.model_ply = str(path)
    window.dataset.face_count = 2
    window.set_layer_visible('mesh', True)
    return path


def test_measurement_uses_actual_points_and_local_units(window, tmp_path, qtbot):
    mesh_project(window, tmp_path)
    window.show_measurement()
    window._survey_pick_ray(np.array([1, 1, 50]), np.array([0, 0, -1]))
    qtbot.waitUntil(lambda: not window._survey_busy, timeout=10000)
    window._survey_pick_ray(np.array([4, 5, 50]), np.array([0, 0, -1]))
    dialog = window._survey_dialog
    qtbot.waitUntil(lambda: all(p is not None for p in dialog.points), timeout=10000)
    qtbot.waitUntil(lambda: not window._survey_busy, timeout=10000)
    np.testing.assert_allclose(window._survey_endpoints_model, [[1, 1, 3], [4, 5, 14]])
    assert 'model units' in dialog.result.text()
    assert '3D distance:' in dialog.result.text()
    dialog.close()


def test_section_endpoint_updates_and_new_project_cannot_take_old_result(window, tmp_path, qtbot):
    mesh_project(window, tmp_path)
    window.show_cross_section()
    window._survey_set_point([1, 1])
    window._survey_set_point([4, 1])
    qtbot.waitUntil(lambda: window._survey_profile is not None, timeout=10000)
    along, heights = window._survey_profile
    np.testing.assert_allclose(heights, along + 3, atol=1e-6)
    window._survey_dialog.coordinates[1][1].setValue(2)
    qtbot.waitUntil(lambda: window._survey_profile is not None and abs(window._survey_profile[1][-1] - 8) < 1e-6, timeout=10000)
    old = window._survey_dialog
    window.project = Project()
    window.reload_view()
    assert not old.isVisible()


def test_classified_cloud_and_display_settings_survive_project_move(window, tmp_path, monkeypatch):
    from test_terrain_bundle_105 import cloud
    from photomesh.survey_ui import GroundDialog
    source = tmp_path / 'input.ply'
    cloud(source)
    window.project.path = str(tmp_path / 'survey.pmsx')
    window.dataset.point_cloud_ply = str(source)
    monkeypatch.setattr(GroundDialog, 'exec', lambda self: 1)
    monkeypatch.setattr(GroundDialog, 'settings', lambda self: dict(cell_size=1, slope=.15,
        initial_height=.2, max_height=2, max_radius=8, up='z'))
    window.classify_point_cloud()
    classified = window.dataset.point_cloud_ply
    assert classified != str(source) and os.path.isfile(classified) and source.exists()
    window.show_point_classes([2], True)
    window.project.save(window.project.path)
    reopened = Project.load(window.project.path)
    assert reopened.dataset.meta['class_display']['source'] == classified
    assert reopened.dataset.meta['class_display']['visible'] == [2]
    assert reopened.dataset.point_cloud_ply == classified
    import shutil
    relocated = tmp_path.parent / (tmp_path.name + '-relocated')
    shutil.copytree(tmp_path, relocated)
    moved = Project.load(str(relocated / 'survey.pmsx'))
    assert moved.dataset.point_cloud_ply.startswith(str(relocated))
    assert moved.dataset.meta['class_display']['source'] == moved.dataset.point_cloud_ply
    assert os.path.isfile(moved.dataset.point_cloud_ply)


def test_dtm_path_is_independent_and_persisted(window, tmp_path):
    window.project.path = str(tmp_path / 'survey.pmsx')
    window.dataset.dem = {'path': str(tmp_path / 'dsm.tif')}
    window.dataset.dtm = {'path': str(tmp_path / 'dtm.tif'), 'surface_type': 'DTM'}
    window.project.save(window.project.path)
    project = Project.load(window.project.path)
    assert project.dataset.dem['path'] != project.dataset.dtm['path']
    assert project.dataset.dtm['surface_type'] == 'DTM'


def test_unknown_height_keeps_image_error_visible_without_xyz_rmse(window):
    window.dataset.markers = [{'label': 'check', 'enabled': False, 'ref': [1, 2, 3]}]
    window.dataset.georef = {'rows': [], 'reference_heights_verified': False,
        'marker_image_errors': {'check': {'pix': .25, 'n': 4}}}
    window.markers_pane.refresh(window.dataset)
    assert window.markers_pane.item(0, 5).text() == ''
    assert window.markers_pane.item(0, 7).text() == '0.250'
    assert window.markers_pane.error_summary['Check points']['error'] is None
    assert window.markers_pane.error_summary['Check points']['pixel'] == .25


def test_dtm_build_publishes_ground_only_and_activates_without_replacing_dsm(window, tmp_path, monkeypatch, no_dialogs):
    import json
    from test_terrain_bundle_105 import cloud
    from test_build_display import runner
    from photomesh.ground import classify_cloud
    from photomesh.dem_engine import build_dem
    from photomesh.dialogs import BuildDEMDialog
    source, classified = tmp_path / 'input.ply', tmp_path / 'classified.ply'
    cloud(source)
    classify_cloud(source, classified, max_radius=8)
    window.project.path = str(tmp_path / 'survey.pmsx')
    window.dataset.point_cloud_ply = str(classified)
    window.dataset.georef = {'offset': [500000, 4500000, 100], 'crs': 'EPSG:32638', 'crs_kind': 'utm'}
    window.dataset.dem = {'path': 'previous-dsm.tif', 'surface_type': 'DSM'}
    monkeypatch.setattr(BuildDEMDialog, 'exec', lambda self: 1)
    monkeypatch.setattr(BuildDEMDialog, 'settings', lambda self: dict(source='Point cloud', pixel_size=1., interpolation='Disabled'))
    def process():
        config = os.path.join(window.project.default_workdir(window.dataset), 'build_dtm.json')
        with open(config, encoding='utf-8') as stream:
            settings = json.load(stream)
        assert settings['ground_only']
        result = build_dem(settings, log=lambda *_: None)
        with open(settings['result'], 'w', encoding='utf-8') as stream:
            json.dump(result, stream)
    runner(monkeypatch, before=process)
    window.build_dem(True)
    assert not no_dialogs
    assert window.dataset.dem['path'] == 'previous-dsm.tif'
    assert window.dataset.dtm['surface_type'] == 'DTM'
    assert window.layer_action('dtm').isChecked() and not window.layer_action('dem').isChecked()
    assert window.tabs.currentWidget() is window.plan_view
    assert not no_dialogs
