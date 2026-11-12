"""Survey tools and classified-cloud presentation; computation stays off the GUI thread."""
import os
import uuid
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QSpinBox, QComboBox, QDialogButtonBox, QMessageBox)

from .bgjob import run_modal
from .workflow import file_stamp, source_unit
from .survey_tools import SurveyToolsMixin


def number(value, minimum=0., maximum=1e9, decimals=4):
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setValue(value)
    return box


class GroundDialog(QDialog):
    def __init__(self, parent, unit, georeferenced=False):
        super().__init__(parent)
        self.setWindowTitle('Point Cloud Classification')
        layout = QVBoxLayout(self)
        note = QLabel('Classify ground (2) and non-ground (1). A separate cloud is created; the original and its attributes are retained.')
        note.setWordWrap(True)
        layout.addWidget(note)
        form = QFormLayout()
        self.cell = number(1, .0001)
        self.slope = number(.15, 0, 10)
        self.initial = number(.2)
        self.height = number(2)
        self.radius = QSpinBox(); self.radius.setRange(1, 128); self.radius.setValue(16)
        self.up = QComboBox()
        self.up.addItem('Project Z axis', 'z')
        if not georeferenced:
            self.up.addItem('Camera-derived up direction', 'camera')
            self.up.setCurrentIndex(1)
        form.addRow('Up direction:', self.up)
        for label, widget in [(f'Grid cell ({unit}):', self.cell), ('Terrain slope (rise / run):', self.slope),
                (f'Initial height tolerance ({unit}):', self.initial), (f'Maximum height tolerance ({unit}):', self.height),
                ('Maximum window radius (cells):', self.radius)]:
            form.addRow(label, widget)
        layout.addLayout(form)
        warning = QLabel('Ground is an estimate. Inspect steep slopes, large roofs and sparse areas before using the classes for a DTM. Thresholds use the source units shown above.')
        warning.setWordWrap(True)
        layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def settings(self):
        return dict(cell_size=self.cell.value(), slope=self.slope.value(), initial_height=self.initial.value(),
                    max_height=self.height.value(), max_radius=self.radius.value(), up=self.up.currentData())


class SurveyMixin(SurveyToolsMixin):
    def refresh_photo_gps_metadata(self):
        ch, project = self.dataset, self.project
        cameras = list(ch.cameras)
        if not cameras:
            return
        paths = [camera.path for camera in cameras]
        def work(report, stop):
            from .fastpipe import read_header
            results, errors = {}, []
            for i, path in enumerate(paths):
                if stop():
                    return None
                try:
                    results[path] = read_header(path)
                except (OSError, ValueError) as error:
                    errors.append(f'{os.path.basename(path)}: {error}')
                report(i + 1, len(paths), 'Reading original photo GPS metadata')
            return results, errors
        result, cancelled, error = run_modal(self, 'Refresh Photo GPS Metadata', 'Reading photos...', work, len(paths))
        if cancelled or self.project is not project or self.dataset is not ch:
            return
        if error:
            self.show_error('Refresh Photo GPS Metadata', error); return
        results, errors = result
        current_ids = {id(camera) for camera in ch.cameras}
        for camera in cameras:
            if id(camera) in current_ids and camera.path in results:
                metadata = results[camera.path]
                camera.lon, camera.lat, camera.alt = metadata['lon'], metadata['lat'], metadata['alt']
                camera.gps_accuracy, camera.gps_metadata = metadata['gps_accuracy'], metadata['gps_metadata']
        self.set_modified(); self.refresh_all()
        for message in errors:
            self.log(message)
        self.log(f'GPS metadata refreshed from {len(results)} original photos. Existing model coordinates are unchanged; Optimize Cameras to apply the updated references.')

    def classify_point_cloud(self):
        if not self._require_saved('Point Cloud Classification'):
            return
        ch, project = self.dataset, self.project
        source = ch.point_cloud_ply
        if not source or not os.path.isfile(source):
            QMessageBox.information(self, 'Point Cloud Classification', 'Build or import a point cloud first.'); return
        dialog = GroundDialog(self, source_unit(ch.georef), bool(ch.georef))
        if not dialog.exec():
            return
        options = dialog.settings()
        source_stamp = file_stamp(source)
        model_directory, photos = self._model_dir(ch), self._photo_map(ch)
        destination = os.path.join(self.project.default_workdir(ch), 'classified-' + uuid.uuid4().hex[:12] + '.ply')
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        def work(report, cancelled):
            from .ground import classify_cloud
            rotation = np.eye(3)
            if options['up'] == 'camera':
                from .texture import load_views
                from .ortho import projection_rotation
                views = load_views(model_directory, photos, lambda _text: None)
                if not views:
                    raise ValueError('Camera-derived up needs aligned cameras; choose Project Z only if its vertical axis is known')
                rotation = projection_rotation(views, False)
            return classify_cloud(source, destination, rotation=rotation, progress=report, cancel=cancelled,
                                  **{key: value for key, value in options.items() if key != 'up'})
        result, cancelled, error = run_modal(self, 'Point Cloud Classification', 'Classifying ground...', work, 100)
        if cancelled:
            return
        if error:
            self.show_error('Point Cloud Classification', error); return
        if self.project is not project or self.dataset is not ch or file_stamp(source) != source_stamp:
            self.log('Classification result kept on disk; the active project/source changed.'); return
        ch.point_cloud_ply = destination
        ch.meta['classification'] = dict(result, source=source, source_stamp=source_stamp)
        ch.meta['class_display'] = {'source': destination, 'colors': True, 'visible': None}
        if ch.dtm:
            ch.dtm['stale'] = 'built before ground reclassification'
        self.set_modified(); self.reload_view(); self.show_layer('cloud')
        self.log(f"Classified {result['ground']:,} ground and {result['non_ground']:,} non-ground points; original cloud retained")

    def show_point_classes(self, classes=None, colors=None):
        from .workflow import vertex_blocks
        path = self.dataset.point_cloud_ply
        if not path or not os.path.exists(path):
            return
        records = next(iter(vertex_blocks(path, block=1)))
        if 'classification' not in records.dtype.names:
            QMessageBox.information(self, 'Point Classes', 'Classify this point cloud first.'); return
        if colors is None:
            colors = self.dataset.meta.get('class_display', {}).get('colors', True)
        self.dataset.meta['class_display'] = {'source': path, 'colors': colors, 'visible': classes}
        self.set_modified(); self.reload_view(); self.show_layer('cloud')
        self._sync_mode_button('Point Cloud - Classification' if colors else 'Point Cloud - Colors')

    def show_cloud_rgb(self):
        state = self.dataset.meta.get('class_display') or {}
        if state.get('source') == self.dataset.point_cloud_ply:
            self.show_point_classes(state.get('visible'), False)
        else:
            self.show_layer('cloud')

    def export_las_to(self, destination, source=None, precision=.001):
        from .las_export import export_las
        source = source or self.dataset.point_cloud_ply or self.dataset.tie_points_ply
        georef = dict(self.dataset.georef)
        result, cancelled, error = run_modal(self, 'Export LAS / LAZ', 'Writing point cloud...',
            lambda report, stop: export_las(source, destination, georef, precision, report, stop), 0)
        if cancelled:
            return None
        if error:
            raise error if isinstance(error, BaseException) else RuntimeError(str(error))
        self.log(f'Exported {result:,} points to {destination}')
        return destination

