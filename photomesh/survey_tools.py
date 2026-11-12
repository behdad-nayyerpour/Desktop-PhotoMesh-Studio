"""Docked survey sessions, calibrated picks and cancellable mesh profiles."""
import os
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMessageBox
from .bgjob import BackgroundJob
from .workflow import file_stamp, source_unit
from .survey_geometry import distance_components
from .survey_widgets import SurveyPanel


class SurveyToolsMixin:
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
            old.close(); self.removeDockWidget(old); old.deleteLater()
        self._survey_owner = self.project, self.dataset
        self._survey_owner_files = self._survey_files()
        self._survey_generation = getattr(self, '_survey_generation', 0) + 1
        self._survey_rotation = np.eye(3)
        self._survey_frame_kind = None
        self._survey_request = 0
        self._survey_pending = None
        self._survey_pick_queue = []
        self._survey_mesh_cache = self._survey_pick_cache = None
        self._survey_profile = None
        self._survey_selected = []
        self._survey_endpoints_model = [None, None]
        panel = SurveyPanel(self, section, source_unit(self.dataset.georef))
        self._survey_dialog = panel
        if section:
            vertical = 'Up from ENU tangent origin' if self.dataset.georef.get('coordinate_frame') else 'Elevation' if self.dataset.georef else 'Model Z'
            panel.plot.setLabel('left', vertical, units=panel.unit)
        panel.closed.connect(self._survey_closed)
        self.addDockWidget(Qt.BottomDockWidgetArea, panel)
        panel.show(); self.resizeDocks([panel], [280], Qt.Vertical)
        for view in (self.model_view, self.ortho_view, self.photo_view):
            view.survey_enabled = True
        self.photo_view.cancel_marker_move()

    def _survey_closed(self):
        from .survey_gestures import LineGesture
        for view in (self.model_view, self.ortho_view, self.photo_view):
            view.survey_enabled = False
            view.set_survey_line(None); view.set_survey_anchor(None)
            view._survey_drag = None
            view._survey_gesture = LineGesture()
        self._survey_generation = getattr(self, '_survey_generation', 0) + 1
        self._survey_request = getattr(self, '_survey_request', 0) + 1
        self._survey_pending = None
        self._survey_pick_queue = []
        self._survey_mesh_cache = self._survey_pick_cache = None
        for name in ('_survey_job', '_survey_pick_job'):
            job = getattr(self, name, None)
            if job is not None:
                job.cancel()

    def _survey_files(self):
        def stamp(path):
            try:
                return file_stamp(path) if path else None
            except OSError:
                return None
        model = self._model_dir()
        paths = [self.dataset.model_ply, self.dataset.point_cloud_ply, self.dataset.tie_points_ply]
        if model:
            paths += [os.path.join(model, name) for name in ('cameras.bin', 'images.bin')]
        return tuple((path, stamp(path)) for path in paths)

    def _survey_current(self):
        panel = getattr(self, '_survey_dialog', None)
        current = (panel is not None and panel.isVisible() and
                   self._survey_owner[0] is self.project and self._survey_owner[1] is self.dataset)
        if current and self._survey_owner_files != self._survey_files():
            panel.close(); return False
        return current

    def _survey_clear(self):
        if not self._survey_current():
            return
        self._survey_generation += 1
        self._survey_request += 1
        self._survey_pending = None
        self._survey_pick_queue = []
        self._survey_profile = None
        self._survey_selected = []
        self._survey_frame_kind = None
        self._survey_rotation = np.eye(3)
        self._survey_endpoints_model = [None, None]
        panel = self._survey_dialog
        panel.points, panel.next_pick = [None, None], 0
        for name in ('_survey_job', '_survey_pick_job'):
            job = getattr(self, name, None)
            if job is not None:
                job.cancel()
        panel.result.setText('Choose the start and end points.')
        self._survey_clear_profile()
        self._survey_sync_views()

    def _survey_clear_profile(self):
        self._survey_profile = None
        self._survey_selected = []
        if self._survey_dialog.section:
            self._survey_dialog.curve.setData([], [])
            self._survey_dialog.selection.setData([], [])

    def _survey_begin_pick(self, index):
        if not self._survey_current():
            return
        self._survey_generation += 1
        self._survey_pick_queue = []
        self._survey_request += 1; self._survey_pending = None
        self._survey_dialog.points[index] = None
        self._survey_endpoints_model[index] = None
        self._survey_dialog.next_pick = index
        self._survey_clear_profile()
        self._survey_dialog.result.setText('Move the mouse and click the replacement endpoint.')
        self._survey_sync_views()

    def _survey_coordinates_changed(self, index):
        if not self._survey_current():
            return
        self._survey_generation += 1; self._survey_pick_queue = []
        panel = self._survey_dialog
        panel.points[index] = np.array([box.value() for box in panel.coordinates[index]])
        self._survey_endpoints_model[index] = None if panel.section else panel.points[index] - self._survey_offset()
        self._survey_update()

    def _survey_offset(self):
        return np.asarray(self.dataset.georef.get('offset') or [0, 0, 0], float)

    def _survey_ortho_rotation(self):
        info = self.dataset.orthomosaic or {}
        mesh = self.dataset.model_ply
        if (not mesh or not os.path.isfile(mesh) or not self.layer_action('ortho').isChecked() or
                not self.ortho_view.has_raster('ortho') or info.get('stale') or
                not info.get('format', '').startswith('photomesh-ortho') or
                info.get('source_mesh_stamp') != file_stamp(mesh)):
            raise ValueError('Show an orthophoto built from this current mesh. Rebuild older/stale orthophotos once to establish their mesh link.')
        rotation = np.asarray(info.get('rotation'), float)
        if rotation.shape != (3, 3) or not np.isfinite(rotation).all() or not np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-8) or np.linalg.det(rotation) < 0:
            raise ValueError('Orthophoto projection frame is invalid')
        return rotation

    def _survey_pick_ray(self, origin, direction):
        self._survey_queue_pick([(None, origin, direction)], 'model')

    def _survey_edit_rays(self, rays):
        self._survey_queue_pick(rays, 'model', editing=True)

    def _survey_pick_plan(self, x, y):
        self._survey_edit_plan([(None, x, y)], editing=False)

    def _survey_edit_plan(self, points, editing=True):
        if not self._survey_current():
            return
        try:
            rotation = self._survey_ortho_rotation()
        except ValueError as error:
            self._survey_dialog.result.setText(str(error)); return
        self._survey_queue_pick([(i, np.array([x, y]), None) for i, x, y in points],
                                'ortho', rotation, editing)

    def _survey_pick_photo(self, u, v):
        self._survey_edit_photo([(None, u, v)], editing=False)

    def _survey_edit_photo(self, points, editing=True):
        if not self._survey_current():
            return
        try:
            if not (0 <= self.current_photo < len(self.dataset.cameras)) or not self.dataset.cameras[self.current_photo].aligned:
                raise ValueError('Align this photo before measuring on it; a single unaligned photo has no 3D depth.')
            if self.dataset.meta.get('model', {}).get('stale') or self.dataset.meta.get('point_cloud', {}).get('stale'):
                raise ValueError('Rebuild the surface after camera changes before measuring on a photo.')
            rays = []
            for index, u, v in points:
                if not self.photo_view.view.sceneRect().contains(u, v):
                    raise ValueError('Choose a location inside the photo')
                ray = self.photo_pixel_ray(self.current_photo, u, v)
                if ray is None:
                    raise ValueError('This photo has no calibrated pose in the current model')
                rays.append((index, *ray))
        except (ValueError, OSError) as error:
            self._survey_dialog.result.setText(str(error)); return
        self._survey_queue_pick(rays, 'photo', editing=editing)

    def _survey_queue_pick(self, rays, kind, rotation=None, editing=False):
        if not self._survey_current():
            return
        if not editing and all(point is not None for point in self._survey_dialog.points):
            self._survey_clear()
        ch = self.dataset
        mesh = ch.model_ply if kind != 'model' or self._survey_dialog.section or self.layer_action('mesh').isChecked() else None
        cloud = ch.point_cloud_ply or ch.tie_points_ply
        if kind == 'model' and not mesh:
            cloud = ch.point_cloud_ply if self.layer_action('cloud').isChecked() else ch.tie_points_ply if self.layer_action('tie').isChecked() else None
        source = mesh or cloud
        if not source or not os.path.isfile(source) or (kind == 'ortho' and not mesh):
            self._survey_dialog.result.setText('Show or build a usable mesh / point cloud first.'); return
        rotation = np.eye(3) if rotation is None else rotation.copy()
        request = (self._survey_generation, rays, kind, rotation, source, bool(mesh))
        if editing:
            # A drag keeps only the latest pending position; a pair is atomic.
            self._survey_pick_queue = [request]
        else:
            self._survey_pick_queue.append(request)
        self._survey_start_pick()

    def _survey_start_pick(self):
        previous = getattr(self, '_survey_pick_job', None)
        if previous is not None:
            return
        if not self._survey_current() or not self._survey_pick_queue:
            return
        generation, rays, kind, rotation, source, mesh = self._survey_pick_queue.pop(0)
        stamp = file_stamp(source)
        key = source, stamp, rotation.tobytes()
        cache = self._survey_pick_cache
        panel = self._survey_dialog
        offset = self._survey_offset()
        state = self.dataset.meta.get('class_display') or {}
        classes = state.get('visible') if state.get('source') == source else None
        panel.result.setText('Finding the actual surface... Navigation remains available.')
        def work(_report, stop):
            surface = None
            if mesh:
                from .survey_geometry import load_surface
                surface = cache[1] if cache and cache[0] == key else load_surface(source, rotation, stop)
            points = []
            for index, origin, direction in rays:
                if stop():
                    return None
                if kind == 'ortho':
                    xy = np.asarray(origin) - offset[:2]
                    top = surface.high[2] + max(1., surface.high[2] - surface.low[2])
                    point = surface.pick([*xy, top], [0, 0, -1])
                    point = None if point is None else point @ rotation
                elif mesh:
                    point = surface.pick(origin, direction)
                else:
                    from .survey_geometry import pick_cloud
                    point = pick_cloud(source, origin, direction, classes=classes, cancel=stop)
                if point is None:
                    raise ValueError('No model surface at this location; the previous line is retained.')
                points.append((index, point))
            return surface, points
        job = BackgroundJob(work, name='Survey surface pick', parent=self)
        self._survey_pick_job = job
        def done(result, error):
            job.wait()
            if self._survey_current() and self._survey_dialog is panel and generation == self._survey_generation and file_stamp(source) == stamp:
                if error:
                    panel.result.setText(str(error))
                    self._survey_sync_views()
                elif result is not None:
                    surface, points = result
                    if surface is not None:
                        self._survey_pick_cache = key, surface
                    if not any(point is not None for point in panel.points):
                        self._survey_rotation = rotation.copy()
                        self._survey_frame_kind = kind
                        if panel.section and not np.allclose(rotation, np.eye(3)):
                            panel.plot.setLabel('left', 'Height in orthophoto frame', units=panel.unit)
                    for index, point in points:
                        index = panel.next_pick if index is None else index
                        self._survey_endpoints_model[index] = point
                        world = point @ self._survey_rotation.T + offset if panel.section else point + offset
                        panel.set_point(index, world[:2] if panel.section else world)
                    self._survey_update()
            job.result = None; job.fn = None
            if self._survey_pick_job is job:
                self._survey_pick_job = None
            job.deleteLater()
            self._survey_start_pick()
        job.done.connect(done, Qt.QueuedConnection); job.start()

    def _survey_set_point(self, point, frame_kind='model', rotation=None):
        """Coordinate entry/test API; point is in the session's displayed frame."""
        if not self._survey_current():
            return
        self._survey_frame_kind = frame_kind
        if rotation is not None:
            self._survey_rotation = rotation
        self._survey_dialog.set_point(self._survey_dialog.next_pick, point)
        self._survey_update()

    def _survey_sync_views(self):
        if not self._survey_current():
            return
        points = self._survey_endpoints_model
        complete = all(point is not None for point in points)
        anchor = next((point for point in points if point is not None), None) if not complete else None
        self.model_view.set_survey_line(np.array(points) if complete else None)
        self.model_view.set_survey_anchor(anchor)
        info = self.dataset.orthomosaic or {}
        rotation = np.asarray(info.get('rotation', np.eye(3)), float)
        if rotation.shape == (3, 3):
            convert = lambda point: (np.asarray(point) @ rotation.T + self._survey_offset())[:2]
            self.ortho_view.set_survey_line(np.array([convert(point) for point in points]) if complete else None)
            self.ortho_view.set_survey_anchor(convert(anchor) if anchor is not None else None)
        self.photo_view.set_survey_line(None); self.photo_view.set_survey_anchor(None)
        if self.photo_view.path is None or not (0 <= self.current_photo < len(self.dataset.cameras)):
            return
        camera = self._camera_of_photo(self.current_photo)
        if camera is None:
            return
        from .colmap_io import project
        model, iid, sx, sy = camera
        image = model.images[iid]
        selected = np.asarray(points if complete else [anchor] if anchor is not None else [])
        if not len(selected):
            return
        uv, depth = project(model.cameras[image.camera_id], image.R(), image.tvec, selected)
        if np.isfinite(uv).all() and np.all(depth > 0):
            uv *= [sx, sy]
            if complete:
                self.photo_view.set_survey_line(uv)
            else:
                self.photo_view.set_survey_anchor(uv[0])

    def _survey_update(self):
        panel = self._survey_dialog
        self._survey_sync_views()
        if not all(point is not None for point in panel.points):
            panel.result.setText('Move the mouse, then click the end point. Calculations start after the second point.')
            return
        a, b = panel.points
        if not panel.section:
            result = self.measure_points(a, b); delta = result['delta']
            panel.result.setText(f"3D distance: {result['distance']:.6g} {panel.unit}\nHorizontal: {result['horizontal']:.6g}; ΔX {delta[0]:.6g}, ΔY {delta[1]:.6g}, ΔZ {delta[2]:.6g} {panel.unit}")
            return
        self._survey_clear_profile()
        self._survey_request += 1
        self._survey_pending = self._survey_request, a.copy(), b.copy(), self._survey_rotation.copy()
        previous = getattr(self, '_survey_job', None)
        if previous is not None:
            previous.cancel()
        if getattr(self, '_survey_timer', None) is None:
            self._survey_timer = QTimer(self); self._survey_timer.setSingleShot(True)
            self._survey_timer.timeout.connect(self._survey_start_profile)
        self._survey_timer.start(150)

    def _survey_start_profile(self):
        if not self._survey_current() or self._survey_pending is None:
            return
        previous = getattr(self, '_survey_job', None)
        if previous is not None and not previous.finished:
            return
        request, a, b, rotation = self._survey_pending; self._survey_pending = None
        source = self.dataset.model_ply; stamp = file_stamp(source)
        offset = self._survey_offset()
        key = source, stamp, rotation.tobytes()
        cache = self._survey_mesh_cache or self._survey_pick_cache
        panel = self._survey_dialog
        panel.result.setText('Calculating the mesh section...')
        def work(_report, stop):
            from .survey_geometry import load_surface
            surface = cache[1] if cache and cache[0] == key else load_surface(source, rotation, stop)
            along, z = surface.section(a - offset[:2], b - offset[:2], cancel=stop)
            return surface, along, z + offset[2]
        job = BackgroundJob(work, name='Mesh cross section', parent=self); self._survey_job = job
        def done(result, error):
            job.wait()
            if self._survey_current() and self._survey_dialog is panel and file_stamp(source) == stamp and request == self._survey_request:
                if error:
                    panel.result.setText(str(error))
                elif result is not None:
                    surface, along, z = result
                    self._survey_mesh_cache = key, surface
                    self._survey_profile = along, z; self._survey_selected = []
                    panel.curve.setData(along, z, connect='finite'); panel.selection.setData([], [])
                    panel.result.setText(f'Length: {along[-1]:.6g} {panel.unit}. Click two profile points for slope.')
                    ends = np.column_stack([np.array([a, b]) - offset[:2], np.array([z[0], z[-1]]) - offset[2]]) @ rotation
                    for i in range(2):
                        if self._survey_endpoints_model[i] is None and np.isfinite(ends[i]).all():
                            self._survey_endpoints_model[i] = ends[i]
                    self._survey_sync_views()
            job.result = None; job.fn = None
            if self._survey_job is job:
                self._survey_job = None
            job.deleteLater()
            if self._survey_pending is not None:
                self._survey_start_profile()
        job.done.connect(done, Qt.QueuedConnection); job.start()

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
