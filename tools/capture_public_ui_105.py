"""Capture actual Lens2Mesh UI with the public held-out survey reconstruction.

The screenshots show a sparse model, never a fabricated textured/dense result.
Only display-fixture photos/calibration pixels are downscaled together by 4.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.request


def main(evidence, output):
    evidence, output = evidence.resolve(), output.resolve()
    import numpy as np
    from PIL import Image
    from photomesh import colmap_io as cio
    from photomesh.plyio import save_ply
    from photomesh.project import Project, Camera
    from benchmark_public_survey_105 import parse_gcps, DATA_REPO, DATA_COMMIT
    output.mkdir(parents=True, exist_ok=True)
    fixture = output/'fixture'; fixture.mkdir()
    photos = fixture/'photos'; photos.mkdir()
    model = cio.read_model(str(evidence/'public-survey/evaluation/controls'))
    for camera in model.cameras.values():
        assert camera.model == 2 and camera.width % 4 == camera.height % 4 == 0
        camera.width //= 4; camera.height //= 4; camera.params[:3] /= 4
    for image in model.images.values():
        path = photos/image.name
        request = urllib.request.Request(f'https://raw.githubusercontent.com/{DATA_REPO}/{DATA_COMMIT}/images/{image.name}')
        with urllib.request.urlopen(request, timeout=120) as source:
            with Image.open(source) as photo:
                photo.resize((photo.width//4, photo.height//4), Image.Resampling.LANCZOS).save(path, quality=94)
        image.xys /= 4
    project = Project(); project.path = str(fixture/'Helenenschacht.pmsx')
    dataset = project.dataset; dataset.name = 'Helenenschacht public survey'
    dataset.workdir = str(fixture/'processing')
    model_path = Path(dataset.workdir)/'sparse/0'; cio.write_model(str(model_path), model)
    dataset.tie_points_ply = str(fixture/'tie_points.ply'); dataset.tie_point_count = len(model.points)
    save_ply(dataset.tie_points_ply, model.points.xyz, model.points.rgb/255.)
    dataset.crs = 'EPSG:4326'
    dataset.markers = copy.deepcopy(parse_gcps(evidence/'public-data'))
    for marker in dataset.markers:
        for projection in marker['projections'].values():
            projection[0] /= 4; projection[1] /= 4
    import pyproj
    transform = pyproj.Transformer.from_crs(4326, 32633, always_xy=True)
    controls = [m for m in dataset.markers if m['enabled']]
    positions = np.array([[*transform.transform(*m['ref'][:2]), m['ref'][2]] for m in controls])
    dataset.georef = dict(crs='EPSG:32633', offset=np.round(positions.mean(0), -2).tolist())
    for image in sorted(model.images.values(), key=lambda i:i.name):
        camera = model.cameras[image.camera_id]
        dataset.cameras.append(Camera(path=str(photos/image.name), aligned=True, est=image.center().tolist(),
            rot=image.R().tolist(), width=camera.width, height=camera.height, colmap_name=image.name,
            thumb=str(photos/image.name)))
    project.save(project.path)
    from PySide6.QtCore import QCoreApplication, Qt, QSettings
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    from PySide6.QtWidgets import QApplication
    app = QApplication([]); app.setOrganizationName('Lens2Mesh105VisualReview'); app.setApplicationName('PublicSurvey')
    from photomesh.appicon import app_icon
    app.setWindowIcon(app_icon())
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())
    from photomesh.mainwindow import MainWindow
    from photomesh.theme import apply_theme
    window = MainWindow(); window.resize(1920, 1160); window.move(20, 20); window.show()
    window.open_project(project.path)
    deadline = time.monotonic()+60
    while getattr(window, 'view_loading', False) and time.monotonic() < deadline:
        app.processEvents(); time.sleep(.02)
    assert not window.view_loading
    assert window.model_view.gl is not None
    window._solo('tie'); window.model_view.fit_raw(model.points.xyz)
    window.model_view.gl.setCameraPosition(elevation=60, azimuth=15)
    for theme, name in [('Dark', 'screenshot.png'), ('Light','screenshot-light.png')]:
        apply_theme(app, theme)
        for _ in range(25):
            app.processEvents(); time.sleep(.04)
        frame = window.frameGeometry()
        # Capture the real window-manager title/icon as well as the client UI.
        image = app.primaryScreen().grabWindow(0, frame.x(), frame.y(), frame.width(), frame.height())
        assert image.width() >= 1800 and image.height() >= 1000
        assert image.save(str(output/name), 'PNG')
    (output/'screenshot-provenance.json').write_text(json.dumps(dict(application='Lens2Mesh1.0.5',
        source='Actual MainWindow and Mesa OpenGL capture', dataset=DATA_REPO, commit=DATA_COMMIT,
        dataset_license='GPL-3.0', derivative='Sparse reconstruction; photos and calibration pixels reduced together by4 for display only',
        reference='Three surveyed controls, two held-out checks; no dense/mesh product is implied'), indent=2))
    print('Actual Dark/Light UI captured with '+str(len(model.images))+' public cameras and '+str(len(model.points))+' tie points', flush=True)
    os._exit(0)  # Fixture may still have idle Qt/OpenGL background finalizers.


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main(args.evidence, args.output)
