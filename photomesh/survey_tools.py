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
        # Retain the script entry point; the UI has one combined section tool.
        self.show_cross_section()

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
        self._survey_busy = False
        self._survey_dragging = False
        self._survey_drag_changed = False
        self._survey_error = None
        self._survey_busy_note = ''
        self._survey_pick_queue = []
        self._survey_mesh_cache = self._survey_pick_cache = None
        self._survey_profile = None
        self._survey_selected = []
        self._survey_endpoints_model = [None, None]
        panel = SurveyPanel(self, True, source_unit(self.dataset.georef))
        self._survey_dialog = panel
        vertical = 'Up from ENU tangent origin' if self.dataset.georef.get('coordinate_frame') else 'Elevation' if self.dataset.georef else 'Model Z'
        panel.plot.setLabel('left', vertical, units=panel.unit)
        panel.closed.connect(self._survey_closed)
        self.addDockWidget(Qt.BottomDockWidgetArea, panel)
        panel.show(); self.resizeDocks([panel], [320], Qt.Vertical)
        for view in (self.model_view, self.ortho_view, self.photo_view):
            view.survey_enabled = True
            view.survey_busy = False
        self.photo_view.cancel_marker_move()
        self._update_menu_actions()

    def _survey_closed(self):
        from .survey_gestures import LineGesture
        for view in (self.model_view, self.ortho_view, self.photo_view):
            view.survey_enabled = False
            view.survey_busy = False
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
        self._update_menu_actions()

    def _survey_refresh_busy(self):
        if not self._survey_current():
            return
        busy = bool(self._survey_pending is not None or self._survey_pick_queue or
                    getattr(self, '_survey_pick_job', None) is not None or getattr(self, '_survey_job', None) is not None)
        changed = busy != self._survey_busy
        self._survey_busy = busy
        self._survey_dialog.set_busy(busy)
        for view in (self.model_view, self.ortho_view, self.photo_view):
            view.survey_busy = busy
        if busy:
            text = self._survey_busy_note or 'Calculating section... Navigation and Close remain available.'
        elif self._survey_error:
            text = self._survey_error
        elif self._survey_dragging:
            text = 'Moving line. Release the handle to calculate the section.'
        elif all(point is not None for point in self._survey_dialog.points):
            text = 'Section ready. Drag either end or the centre handle; click two profile points for slope.'
        elif any(point is not None for point in self._survey_dialog.points):
            text = 'Move the mouse, then click the end point.'
        else:
            text = 'Click the start point.'
        self._survey_dialog.status.setText(text)
        if changed:
            self._survey_sync_views()

    def _survey_fail(self, message):
        self._survey_error = str(message)
        self._survey_sync_views()
        self._survey_refresh_busy()

    def _survey_cancel(self):
        if not self._survey_current():
            return
        self._survey_generation += 1; self._survey_request += 1
        self._survey_pick_queue = []; self._survey_pending = None
        self._survey_dragging = False
        self._survey_busy_note = 'Cancelling calculation...'
        self._survey_error = 'Calculation cancelled. Choose a point or move a handle to continue.'
        for name in ('_survey_pick_job', '_survey_job'):
            job = getattr(self, name, None)
            if job is not None:
                job.cancel()
        self._survey_refresh_busy()

    def _survey_drag_started(self):
        if not self._survey_current() or self._survey_busy:
            return
        self._survey_dragging = True
        self._survey_drag_changed = False
        self._survey_error = None

    def _survey_drag_finished(self):
        if not self._survey_current():
            return
        self._survey_dragging = False
        if self._survey_drag_changed and getattr(self, '_survey_pick_job', None) is None and not self._survey_pick_queue:
            self._survey_update()
        self._survey_refresh_busy()

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
        self._survey_error = None
        self._survey_dragging = False
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
        self._survey_refresh_busy()

    def _survey_clear_profile(self):
        self._survey_profile = None
        self.model_view.set_survey_surface(None)
        self._survey_selected = []
        if self._survey_dialog.section:
            self._survey_dialog.curve.setData([], [])
            self._survey_dialog.selection.setData([], [])

    def _survey_coordinates_changed(self, index):
        if not self._survey_current():
            return
        self._survey_generation += 1; self._survey_pick_queue = []
        self._survey_error = None
        panel = self._survey_dialog
        panel.points[index] = np.array([box.value() for box in panel.coordinates[index]])
        self._survey_endpoints_model[index] = None
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
            raise ValueError('This orthophoto is missing a current mesh link or is out of date. Use Process > Build Orthomosaic to rebuild it from the current mesh before drawing a section.')
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
            self._survey_fail(error); return
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
            source_kind = 'model' if self.dataset.model_ply else 'point_cloud'
            if self.dataset.meta.get(source_kind, {}).get('stale'):
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
            self._survey_fail(error); return
        self._survey_queue_pick(rays, 'photo', editing=editing)

    def _survey_queue_pick(self, rays, kind, rotation=None, editing=False):
        if not self._survey_current():
            return
        if self._survey_busy and not (editing and self._survey_dragging):
            return
        if not editing and all(point is not None for point in self._survey_dialog.points):
            self._survey_clear()
        ch = self.dataset
        source = ch.model_ply
        if not source or not os.path.isfile(source):
            self._survey_fail('Build a usable mesh first.'); return
        rotation = np.eye(3) if rotation is None else rotation.copy()
        request = (self._survey_generation, rays, kind, rotation, source)
        if editing:
            if not self._survey_drag_changed:
                self._survey_clear_profile()
            self._survey_drag_changed = True
            # A drag keeps only the latest pending position; a pair is atomic.
            self._survey_pick_queue = [request]
        else:
            self._survey_pick_queue.append(request)
        self._survey_error = None
        self._survey_refresh_busy()
        self._survey_start_pick()

    def _survey_start_pick(self):
        previous = getattr(self, '_survey_pick_job', None)
        if previous is not None:
            return
        if not self._survey_current() or not self._survey_pick_queue:
            return
        generation, rays, kind, rotation, source = self._survey_pick_queue.pop(0)
        stamp = file_stamp(source)
        key = source, stamp, rotation.tobytes()
        cache = self._survey_pick_cache
        panel = self._survey_dialog
        offset = self._survey_offset()
        self._survey_busy_note = 'Preparing the mesh / locating the endpoint... Wait before drawing; navigation remains available.'
        def work(_report, stop):
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
                else:
                    point = surface.pick(origin, direction)
                if point is None:
                    raise ValueError('No model surface at this location; the previous line is retained.')
                points.append((index, point))
            return surface, points
        job = BackgroundJob(work, name='Survey surface pick', parent=self)
        self._survey_pick_job = job
        self._survey_refresh_busy()
        def done(result, error):
            job.wait()
            if self._survey_current() and self._survey_dialog is panel and generation == self._survey_generation and file_stamp(source) == stamp:
                if error:
                    self._survey_fail(error)
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
                        world = point @ self._survey_rotation.T + offset
                        panel.set_point(index, world[:2])
                    self._survey_update()
            job.result = None; job.fn = None
            if self._survey_pick_job is job:
                self._survey_pick_job = None
            job.deleteLater()
            self._survey_start_pick()
            self._survey_refresh_busy()
        job.done.connect(done, Qt.QueuedConnection); job.start()

    def _survey_set_point(self, point, frame_kind='model', rotation=None):
        """Coordinate entry/test API; point is in the session's displayed frame."""
        if not self._survey_current():
            return
        self._survey_frame_kind = frame_kind
        if rotation is not None:
            self._survey_rotation = rotation
        self._survey_dialog.set_point(self._survey_dialog.next_pick, np.asarray(point)[:2])
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
        panel.result.setText(self._survey_metrics())
        if self._survey_dragging:
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
        self._survey_busy_note = 'Calculating section... Wait before editing or drawing another line. Navigation remains available.'
        self._survey_refresh_busy()

    def _survey_metrics(self):
        panel = self._survey_dialog
        points = self._survey_endpoints_model
        if all(point is not None for point in points):
            values = np.asarray(points) @ self._survey_rotation.T + self._survey_offset()
            result = self.measure_points(*values)
            return f"Horizontal: {result['horizontal']:.6g} {panel.unit}; 3D distance: {result['distance']:.6g} {panel.unit}; ΔZ: {result['height']:.6g} {panel.unit}"
        a, b = panel.points
        return f'Horizontal: {np.linalg.norm(b-a):.6g} {panel.unit}. 3D distance requires valid surface endpoints.'

    def _survey_start_profile(self):
        if not self._survey_current() or self._survey_pending is None:
            return
        previous = getattr(self, '_survey_job', None)
        if previous is not None:
            return
        request, a, b, rotation = self._survey_pending; self._survey_pending = None
        source = self.dataset.model_ply; stamp = file_stamp(source)
        offset = self._survey_offset()
        key = source, stamp, rotation.tobytes()
        cache = self._survey_mesh_cache or self._survey_pick_cache
        panel = self._survey_dialog
        def work(_report, stop):
            from .survey_geometry import load_surface, section_plot_data
            surface = cache[1] if cache and cache[0] == key else load_surface(source, rotation, stop)
            segments=surface.section_segments(a-offset[:2],b-offset[:2],cancel=stop)
            along,z,components=section_plot_data(segments)
            direction=(b-a)/np.linalg.norm(b-a)
            xyz=np.column_stack([a-offset[:2]+along[:,None]*direction,z]) @ rotation
            # The middle grip lies on the actual section, even beside a gap.
            center=None
            if len(segments):
                delta=segments[:,1]-segments[:,0]
                t=np.divide(np.linalg.norm(b-a)/2-segments[:,0,0],delta[:,0],out=np.zeros(len(delta)),where=abs(delta[:,0])>1e-12)
                candidates=segments[:,0]+np.clip(t,0,1)[:,None]*delta
                order=np.lexsort((-candidates[:,1],abs(candidates[:,0]-np.linalg.norm(b-a)/2)))
                s,h=candidates[order[0]]
                center=np.r_[a-offset[:2]+s*direction,h] @ rotation
            ends=[]
            for point in (a,b):
                hit=surface.pick(np.r_[point-offset[:2],surface.high[2]+max(1.,surface.high[2]-surface.low[2])],[0,0,-1])
                ends.append(None if hit is None else hit @ rotation)
            return surface, along, z + offset[2], xyz, center, ends, components
        job = BackgroundJob(work, name='Mesh cross section', parent=self); self._survey_job = job
        self._survey_refresh_busy()
        def done(result, error):
            job.wait()
            if self._survey_current() and self._survey_dialog is panel and file_stamp(source) == stamp and request == self._survey_request:
                if error:
                    self._survey_fail(error)
                elif result is not None:
                    surface, along, z, xyz, center, ends, components = result
                    self._survey_mesh_cache = key, surface
                    self._survey_profile = along, z; self._survey_selected = []
                    self._survey_profile_components=components
                    panel.curve.setData(along, z, connect='finite'); panel.selection.setData([], [])
                    for i in range(2):
                        if self._survey_endpoints_model[i] is None and ends[i] is not None:
                            self._survey_endpoints_model[i] = ends[i]
                    self._survey_sync_views()
                    self.model_view.set_survey_surface(xyz, center)
                    panel.result.setText(self._survey_metrics())
            job.result = None; job.fn = None
            if self._survey_job is job:
                self._survey_job = None
            job.deleteLater()
            if self._survey_pending is not None:
                self._survey_start_profile()
            self._survey_refresh_busy()
        job.done.connect(done, Qt.QueuedConnection); job.start()

    def _survey_profile_clicked(self, event):
        if event.button() != Qt.LeftButton:
            return
        if not self._survey_current() or self._survey_profile is None or self._survey_busy:
            return
        dialog = self._survey_dialog
        along, z = self._survey_profile
        point = dialog.plot.plotItem.vb.mapSceneToView(event.scenePos())
        if not len(along):return
        ranges=dialog.plot.plotItem.vb.viewRange()
        view=dialog.plot.plotItem.vb
        scale=np.array([max(r[1]-r[0],1e-12) for r in ranges])/np.maximum([view.width(),view.height()],1)
        starts=np.column_stack([along[::3],z[::3]])
        delta=np.column_stack([along[1::3],z[1::3]])-starts
        vector=delta/scale
        t=np.clip(np.einsum('ij,ij->i',(np.array([point.x(),point.y()])-starts)/scale,vector)/np.maximum(np.sum(vector*vector,axis=1),1e-30),0,1)
        candidates=starts+t[:,None]*delta
        row=int(np.argmin(np.linalg.norm((candidates-[point.x(),point.y()])/scale,axis=1)))
        index=row*3
        if not np.isfinite(z[index]):
            dialog.result.setText('No measured mesh surface at that profile position.'); return
        if len(self._survey_selected) == 2:
            self._survey_selected = []
        self._survey_selected.append((candidates[row],self._survey_profile_components[index]))
        chosen = self._survey_selected
        selected=np.array([item[0] for item in chosen])
        dialog.selection.setData(selected[:,0],selected[:,1])
        if len(chosen) == 2:
            if chosen[0][1] != chosen[1][1]:
                dialog.result.setText('The selected interval crosses a mesh gap; slope is unavailable.'); return
            left,right=sorted(selected,key=lambda p:p[0])
            result = distance_components([left[0],0,left[1]],[right[0],0,right[1]])
            if result['slope_percent'] is None:
                dialog.result.setText('Choose two profile points with different horizontal positions.'); return
            dialog.result.setText(self._survey_metrics() + f"\nSlope: {result['slope_percent']:.4g}% ({result['slope_degrees']:.4g}°); horizontal {result['horizontal']:.6g} {dialog.unit}, height difference {result['height']:.6g} {dialog.unit}")
