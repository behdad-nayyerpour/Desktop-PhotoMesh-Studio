"""Survey tools and classified-cloud presentation; computation stays off the GUI thread."""
import os
import uuid
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QDoubleSpinBox,
    QSpinBox, QComboBox, QDialogButtonBox, QMessageBox, QPushButton, QHBoxLayout)

from .bgjob import BackgroundJob, run_modal
from .workflow import file_stamp, source_unit
from .survey_geometry import distance_components


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


class SurveyDialog(QDialog):
    def __init__(self, parent, section, unit):
        super().__init__(parent, Qt.Tool)
        self.section = section
        self.unit = unit
        self.points = [None, None]
        self.next_pick = 0
        self.setWindowTitle('Cross Section' if section else 'Measure Distance')
        self.resize(720 if section else 480, 480 if section else 300)
        layout = QVBoxLayout(self)
        self.hint = QLabel('Pick two locations on the mesh or point cloud in 3D View.' if not section else
                           'Pick two locations on the mesh in 3D View or a matching orthophoto in Plan View. The profile shows the highest mesh intersection; gaps stay empty.')
        self.hint.setWordWrap(True); layout.addWidget(self.hint)
        form = QFormLayout()
        self.coordinates = []
        for i, label in enumerate(('Start', 'End')):
            row = QHBoxLayout()
            spins = [number(0, -1e12, 1e12, 6) for _ in range(2 if section else 3)]
            for spin in spins:
                spin.valueChanged.connect(lambda _value, index=i: parent._survey_coordinates_changed(index))
                row.addWidget(spin)
            button = QPushButton('Pick ' + label)
            button.clicked.connect(lambda _checked=False, index=i: setattr(self, 'next_pick', index))
            row.addWidget(button)
            form.addRow(f'{label} {"X / Y" if section else "X / Y / Z"} ({unit}):', row)
            self.coordinates.append(spins)
        layout.addLayout(form)
        self.result = QLabel('Choose the start and end points.'); self.result.setWordWrap(True)
        layout.addWidget(self.result)
        if section:
            import pyqtgraph as pg
            self.plot = pg.PlotWidget()
            self.plot.setBackground(self.palette().base().color())
            for axis in ('left', 'bottom'):
                self.plot.getAxis(axis).setTextPen(self.palette().text().color())
                self.plot.getAxis(axis).setPen(self.palette().text().color())
            self.plot.setLabel('bottom', 'Distance along section', units=unit)
            self.plot.setLabel('left', 'Elevation / model Z', units=unit)
            self.curve = self.plot.plot(pen=pg.mkPen('#31b6dd', width=2), connect='finite')
            self.selection = self.plot.plot(pen=None, symbol='o', symbolBrush='#ffb33b', symbolSize=9)
            self.plot.scene().sigMouseClicked.connect(parent._survey_profile_clicked)
            layout.addWidget(self.plot, 1)
        reset = QPushButton('Clear / choose new line' if section else 'Clear measurement')
        reset.clicked.connect(parent._survey_clear)
        layout.addWidget(reset)

    def set_point(self, index, point):
        self.points[index] = np.asarray(point, float)
        for spin, value in zip(self.coordinates[index], point):
            spin.blockSignals(True); spin.setValue(float(value)); spin.blockSignals(False)
        self.next_pick = 1 - index


class SurveyMixin:
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

    def measure_points(self, a, b):
        return dict(distance_components(a, b), units=source_unit(self.dataset.georef))

    def show_measurement(self):
        self._open_survey(False)

    def show_cross_section(self):
        if not self.dataset.model_ply or not os.path.isfile(self.dataset.model_ply):
            QMessageBox.information(self, 'Cross Section', 'Build or import a mesh first.'); return
        self._open_survey(True)

    def _open_survey(self, section):
        old = getattr(self, '_survey_dialog', None)
        if old is not None:
            old.close()
        self._survey_owner = self.project, self.dataset
        self._survey_owner_files = self._survey_files()
        self._survey_rotation = np.eye(3)
        self._survey_frame_kind = None
        self._survey_request = 0
        self._survey_pending = None
        self._survey_mesh_cache = None
        self._survey_pick_cache = None
        self._survey_profile = None
        self._survey_selected = []
        self._survey_dialog = SurveyDialog(self, section, source_unit(self.dataset.georef))
        if section:
            vertical = 'Up from ENU tangent origin' if self.dataset.georef.get('coordinate_frame') else 'Elevation' if self.dataset.georef else 'Model Z'
            self._survey_dialog.plot.setLabel('left', vertical, units=source_unit(self.dataset.georef))
        self._survey_dialog.finished.connect(self._survey_closed)
        self.model_view.survey_enabled = True
        self.model_view.survey_drag_enabled = section
        self.ortho_view.survey_enabled = section
        self._survey_dialog.show()

    def _survey_closed(self, *_args):
        self.model_view.survey_enabled = False
        self.ortho_view.survey_enabled = False
        self._survey_request = getattr(self, '_survey_request', 0) + 1
        self._survey_pending = None
        self._survey_mesh_cache = None
        self._survey_pick_cache = None
        job = getattr(self, '_survey_job', None)
        if job is not None:
            job.cancel()
        self.model_view.set_survey_line(None)
        self.ortho_view.set_survey_line(None)
        self.model_view._survey_drag = None
        self.ortho_view._survey_drag = None

    def _survey_files(self):
        def stamp(path):
            try:
                return file_stamp(path) if path else None
            except OSError:
                return None
        return tuple((path, stamp(path)) for path in
                     (self.dataset.model_ply, self.dataset.point_cloud_ply, self.dataset.tie_points_ply))

    def _survey_current(self):
        dialog = getattr(self, '_survey_dialog', None)
        current = (dialog is not None and dialog.isVisible() and
                   self._survey_owner[0] is self.project and self._survey_owner[1] is self.dataset)
        if current and self._survey_owner_files != self._survey_files():
            dialog.close()
            return False
        return current

    def _survey_move_plan(self, index, x, y):
        if self._survey_current() and self._survey_frame_kind == 'ortho':
            self._survey_dialog.set_point(index, [x, y])
            self.ortho_view.set_survey_line(np.array(self._survey_dialog.points))
            self._survey_update()

    def _survey_move_model(self, index, point):
        if not self._survey_current() or not self._survey_dialog.section:
            return
        offset = np.asarray(self.dataset.georef.get('offset') or [0, 0, 0])
        world = self._survey_rotation @ np.asarray(point) + offset
        self._survey_dialog.set_point(index, world[:2])
        self._survey_update()

    def _survey_clear(self):
        if not self._survey_current():
            return
        self._survey_dialog.points = [None, None]
        self._survey_dialog.next_pick = 0
        self._survey_frame_kind = None
        self._survey_request += 1
        self._survey_pending = None
        self._survey_profile = None
        self._survey_selected = []
        job = getattr(self, '_survey_job', None)
        if job is not None:
            job.cancel()
        self._survey_dialog.result.setText('Choose the start and end points.')
        if self._survey_dialog.section:
            self._survey_dialog.curve.setData([], [])
            self._survey_dialog.selection.setData([], [])
        self.model_view.set_survey_line(None); self.ortho_view.set_survey_line(None)

    def _survey_coordinates_changed(self, index):
        if not self._survey_current():
            return
        dialog = self._survey_dialog
        dialog.points[index] = np.array([box.value() for box in dialog.coordinates[index]])
        self._survey_update()

    def _survey_set_point(self, point, frame_kind='model', rotation=None):
        if not self._survey_current():
            return
        if self._survey_frame_kind is not None and self._survey_frame_kind != frame_kind:
            self._survey_dialog.result.setText('Clear the line before switching its drawing frame between 3D and Plan View.'); return
        self._survey_frame_kind = frame_kind
        self._survey_rotation = np.eye(3) if rotation is None else rotation
        self._survey_dialog.set_point(self._survey_dialog.next_pick, point)
        self._survey_update()

    def _survey_pick_ray(self, origin, direction):
        if not self._survey_current():
            return
        ch, project = self.dataset, self.project
        dialog = self._survey_dialog
        mesh = ch.model_ply if dialog.section or self.layer_action('mesh').isChecked() else None
        cloud = (ch.point_cloud_ply if self.layer_action('cloud').isChecked() else ch.tie_points_ply if self.layer_action('tie').isChecked() else None)
        source = mesh or cloud
        if not source or not os.path.exists(source):
            dialog.result.setText('Show a usable mesh or point cloud before picking.'); return
        stamp = file_stamp(source)
        cache_key = (source, stamp, np.eye(3).tobytes())
        cache = getattr(self, '_survey_pick_cache', None)
        display = ch.meta.get('class_display') or {}
        visible_classes = display.get('visible') if display.get('source') == source else None
        def work(report, stop):
            if mesh:
                from .survey_geometry import load_surface
                surface = cache[1] if cache is not None and cache[0] == cache_key else load_surface(mesh, cancel=stop)
                return surface, surface.pick(origin, direction)
            from .survey_geometry import pick_cloud
            return pick_cloud(source, origin, direction, cancel=stop, classes=visible_classes)
        point, cancelled, error = run_modal(self, 'Pick Surface Point', 'Finding the actual surface...', work, 0)
        if cancelled or not self._survey_current() or self.project is not project or self.dataset is not ch or file_stamp(source) != stamp:
            return
        if mesh and not error:
            surface, point = point
            self._survey_pick_cache = cache_key, surface
        if error or point is None:
            dialog.result.setText(str(error) if error else 'No surface at this location.'); return
        offset = np.asarray(ch.georef.get('offset') or [0, 0, 0])
        self._survey_set_point((point + offset)[:2] if dialog.section else point + offset)

    def _survey_pick_plan(self, x, y):
        if not self._survey_current() or not self._survey_dialog.section:
            return
        info = self.dataset.orthomosaic or {}
        if (not self.layer_action('ortho').isChecked() or not self.ortho_view.has_raster('ortho') or
                not info.get('format', '').startswith('photomesh-ortho') or info.get('stale') or 'rotation' not in info or
                info.get('source_mesh_stamp') != file_stamp(self.dataset.model_ply)):
            self._survey_dialog.result.setText('Show an orthophoto built from this current mesh. Rebuild older orthophotos once to establish their source-mesh link; imported/stale rasters cannot establish a mesh frame.'); return
        rotation = np.asarray(info['rotation'], float)
        self._survey_set_point([x, y], frame_kind='ortho', rotation=rotation)

    def _survey_update(self):
        dialog = self._survey_dialog
        if not all(point is not None for point in dialog.points):
            return
        a, b = dialog.points
        if not dialog.section:
            result = self.measure_points(a, b)
            delta = result['delta']
            dialog.result.setText(f"3D distance: {result['distance']:.6g} {dialog.unit}\n"
                                 f"Horizontal: {result['horizontal']:.6g}; ΔX {delta[0]:.6g}, ΔY {delta[1]:.6g}, ΔZ {delta[2]:.6g} {dialog.unit}")
            offset = np.asarray(self.dataset.georef.get('offset') or [0, 0, 0])
            self.model_view.set_survey_line(np.array([a, b]) - offset)
            return
        self._survey_request += 1
        self._survey_pending = (self._survey_request, a.copy(), b.copy(), self._survey_rotation.copy())
        job = getattr(self, '_survey_job', None)
        if job is not None and not job.finished:
            job.cancel()
        timer = getattr(self, '_survey_timer', None)
        if timer is None:
            self._survey_timer = QTimer(self); self._survey_timer.setSingleShot(True)
            self._survey_timer.timeout.connect(self._survey_start_profile)
        self._survey_timer.start(150)

    def _survey_start_profile(self):
        if not self._survey_current() or self._survey_pending is None:
            return
        previous = getattr(self, '_survey_job', None)
        if previous is not None and not previous.finished:
            return  # Its queued completion starts the latest pending request.
        request, a, b, rotation = self._survey_pending
        self._survey_pending = None
        ch = self.dataset
        source = ch.model_ply
        stamp = file_stamp(source)
        offset = np.asarray(ch.georef.get('offset') or [0, 0, 0], float)
        cache_key = (source, stamp, rotation.tobytes())
        cache = self._survey_mesh_cache or self._survey_pick_cache
        dialog = self._survey_dialog
        owner = self.project, ch
        dialog.result.setText('Calculating the mesh section...')
        def work(report, stop):
            if cache is not None and cache[0] == cache_key:
                surface = cache[1]
            else:
                from .survey_geometry import load_surface
                surface = load_surface(source, rotation, stop)
            along, z = surface.section(a - offset[:2], b - offset[:2], cancel=stop)
            return surface, along, z + offset[2]
        job = BackgroundJob(work, name='Mesh cross section', parent=self)
        self._survey_job = job
        def done(result, error):
            job.wait()
            if self._survey_current() and self._survey_dialog is dialog and owner[0] is self.project and owner[1] is self.dataset and file_stamp(source) == stamp and request == self._survey_request:
                if error:
                    dialog.result.setText(str(error))
                elif result is not None:
                    surface, along, z = result
                    self._survey_mesh_cache = cache_key, surface
                    self._survey_profile = along, z
                    self._survey_selected = []
                    dialog.curve.setData(along, z, connect='finite')
                    dialog.selection.setData([], [])
                    dialog.result.setText(f'Length: {along[-1]:.6g} {dialog.unit}. Highest mesh intersections; gaps stay empty. Click two profile points for slope.')
                    xy = np.array([a, b]) - offset[:2]
                    ends = np.column_stack([xy, np.array([z[0], z[-1]]) - offset[2]])
                    if np.isfinite(ends).all():
                        self.model_view.survey_plane_normal = rotation[2]
                        self.model_view.set_survey_line(ends @ rotation)
                    else:
                        self.model_view.set_survey_line(None)
                    if self._survey_frame_kind == 'ortho':
                        self.ortho_view.set_survey_line(np.array([a, b]))
            job.result = None
            job.fn = None
            if self._survey_job is job:
                self._survey_job = None
            job.deleteLater()
            if self._survey_pending is not None:
                self._survey_start_profile()
        job.done.connect(done, Qt.QueuedConnection)
        job.start()

    def _survey_profile_clicked(self, event):
        if event.button() != Qt.LeftButton:
            return
        if not self._survey_current() or self._survey_profile is None:
            return
        dialog = self._survey_dialog
        along, z = self._survey_profile
        point = dialog.plot.plotItem.vb.mapSceneToView(event.scenePos())
        index = int(np.argmin(abs(along - point.x())))
        if not np.isfinite(z[index]):
            dialog.result.setText('No measured mesh surface at that profile position.'); return
        if len(self._survey_selected) == 2:
            self._survey_selected = []
        self._survey_selected.append(index)
        chosen = self._survey_selected
        dialog.selection.setData(along[chosen], z[chosen])
        if len(chosen) == 2:
            i, j = sorted(chosen)
            if not np.isfinite(z[i:j + 1]).all():
                dialog.result.setText('The selected interval crosses a mesh gap; slope is unavailable.'); return
            result = distance_components([along[i], 0, z[i]], [along[j], 0, z[j]])
            if result['slope_percent'] is None:
                dialog.result.setText('Choose two profile points with different horizontal positions.'); return
            dialog.result.setText(f"Slope: {result['slope_percent']:.4g}% ({result['slope_degrees']:.4g}°); horizontal {result['horizontal']:.6g} {dialog.unit}, height difference {result['height']:.6g} {dialog.unit}")
