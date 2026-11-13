"""Actual UI captures using CC-BY public terrain; original app license retained."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.request


def main(output):
    from benchmark_public_ground_105 import COMMIT, evaluate
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    source=output/'autzen-classified.laz'
    urllib.request.urlretrieve(f'https://media.githubusercontent.com/media/PDAL/data/{COMMIT}/autzen/autzen-classified.laz',source)
    # The numerical fixture verifies the LFS hash, separate horizontal/vertical
    # units, classes, LAS round trips and DTM before its cloud is displayed.
    evaluate(source,output/'validation')
    result=json.loads((output/'validation/results.json').read_text(encoding='utf-8'))
    from photomesh.project import Project
    project=Project();project.path=str(output/'Autzen_LiDAR.pmsx')
    data=project.dataset;data.name='Autzen public ground classification'
    data.point_cloud_ply=str(output/'validation/classified.ply');data.point_count=result['points']
    data.georef={'metric_scale':True,'offset':[0,0,0],'height_reference':'source NAVD88; local metric offset for display'}
    data.meta['class_display']={'source':data.point_cloud_ply,'colors':True,'visible':[1,2]}
    project.save(project.path)
    from PySide6.QtCore import QCoreApplication,Qt,QSettings
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    from PySide6.QtWidgets import QApplication
    app=QApplication([]);app.setOrganizationName('Lens2Mesh105VisualReview');app.setApplicationName('PublicTerrain')
    from photomesh.appicon import app_icon
    app.setWindowIcon(app_icon())
    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat,QSettings.UserScope,tempfile.mkdtemp())
    from photomesh.mainwindow import MainWindow
    from photomesh.theme import apply_theme
    window=MainWindow();window.resize(1920,1160);window.move(20,20);window.show()
    window.open_project(project.path)
    deadline=time.monotonic()+90
    while window.view_loading and time.monotonic()<deadline:
        app.processEvents();time.sleep(.02)
    assert not window.view_loading and window.model_view.gl is not None
    window.docks['Photos'].hide()
    window._solo('cloud')
    window.model_view.gl.setCameraPosition(elevation=45,azimuth=145)
    for theme,name in [('Dark','screenshot.png'),('Light','screenshot-light.png')]:
        apply_theme(app,theme)
        for _ in range(30):
            app.processEvents();time.sleep(.04)
        frame=window.frameGeometry()
        shot=app.primaryScreen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
        assert shot.width()>=1800 and shot.height()>=1000
        assert shot.save(str(output/name),'PNG')
    (output/'screenshot-provenance.json').write_text(json.dumps(dict(application='Lens2Mesh1.0.5',
        source='Actual MainWindow and Mesa OpenGL with native title/icon',dataset='PDAL/data Autzen',commit=COMMIT,
        dataset_license='CC-BY-4.0',attribution=result['attribution'],
        derivative='Coordinates converted to local metres; actual automatic ground/non-ground colours; bounded viewer preview',
        original_interface_license='Existing application license unchanged; public dataset content retains CC-BY-4.0'),indent=2),encoding='utf-8')
    print('Actual CC-BY terrain Dark/Light UI screenshots captured',flush=True)
    os._exit(0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    main(args.output)
