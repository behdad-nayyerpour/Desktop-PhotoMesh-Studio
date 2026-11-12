"""Dockable panes: Workspace, Reference, Markers, Photos, Console, Properties, Jobs."""
from __future__ import annotations

import collections
import contextlib
import io
import os

from PySide6.QtCore import Qt, Signal, QSize, QItemSelectionModel
from PySide6.QtGui import QIcon, QPixmap, QColor, QBrush
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, QListWidget,
    QListWidgetItem, QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit, QMenu,
    QHeaderView, QListView, QAbstractItemView)

ROLE = Qt.UserRole


def _fmt(v, nd=6):
    return "" if v is None else f"{v:.{nd}f}"


def summary_item(text="", tooltip=""):
    """Footer cells carry no entity identity and cannot be edited or selected."""
    item = QTableWidgetItem(str(text))
    item.setFlags(Qt.ItemIsEnabled)
    item.setData(ROLE + 2, "summary")
    font = item.font(); font.setBold(True); item.setFont(font)
    item.setToolTip(tooltip)
    return item


@contextlib.contextmanager
def bulk_fill(table):
    """Fill a QTableWidget fast. With QHeaderView.ResizeToContents every
    setItem() re-measured the whole column, so refilling the 641-camera
    Reference table took ~2 minutes (O(rows^2)) and froze the window after
    File > Save. Fill with resizing/painting/signals off, size columns once."""
    hdr = table.horizontalHeader()
    table.setUpdatesEnabled(False)
    blocked = table.blockSignals(True)
    sorting = table.isSortingEnabled(); table.setSortingEnabled(False)
    hdr.setSectionResizeMode(QHeaderView.Interactive)
    try:
        yield
    finally:
        table.setSortingEnabled(sorting)
        table.blockSignals(blocked)
        table.resizeColumnsToContents()
        table.setUpdatesEnabled(True)


# Workspace rows that mirror a 3D-view layer (row kind -> layer key)
ROW_LAYER = {"cameras": "cameras", "markers": "markers", "tie": "tie", "cloud": "cloud", "model": "mesh",
             "tiled": "tiled", "ortho": "ortho", "dem": "dem", "shapes": "shapes"}
MAX_SHAPE_ROWS = 400        # per layer; larger layers list the first ones (all are drawn)



def _outdated(prod):
    """Label suffix for a product made from an earlier model (see MainWindow._model_replaced)."""
    return " - outdated, rebuild" if isinstance(prod, dict) and prod.get("stale") else ""


class WorkspacePane(QTreeWidget):
    """Single-project product tree:

    Project (M images)
        Images (a/n aligned)            [camera groups per sensor if > 1]
        Markers (K)
        Tie Points (T points)
        Depth Maps (n, Q quality, F filtering)
        Point Cloud (P points, Q quality)
        3D Model (F faces, ...)

    Only products that exist get a row. Product rows that are also
    3D-view layers carry a visibility checkbox (synced with the layer toggles);
    double-click shows the item."""
    cameraActivated = Signal(int, int)      # dataset index, camera index
    contextAction = Signal(str, int)        # action, dataset index
    selectionInfo = Signal(dict)
    layerToggled = Signal(str, bool)        # layer key, visible
    showRequested = Signal(str, int)        # row kind, dataset index
    markerActivated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIconSize(QSize(16, 16))
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.itemDoubleClicked.connect(self._dbl)
        self.itemSelectionChanged.connect(self._sel)
        self.itemChanged.connect(self._changed)
        self.vis = {}
        self._layer_items = {}
        self._filling = False
        self.shape_provider = None      # callable(dataset index) -> shape set (shapes.py) or None

    @staticmethod
    def _icon(key):
        from .icons import icon
        return icon(key)

    def _item(self, parent, text, role, icon=None, layer=None, bold=False, tip=None):
        it = QTreeWidgetItem([text])
        it.setData(0, ROLE, role)
        if icon:
            it.setIcon(0, self._icon(icon))
        if bold:
            f = it.font(0); f.setBold(True); it.setFont(0, f)
        if tip:
            it.setToolTip(0, tip)
        if layer is not None:
            it.setCheckState(0, Qt.Checked if self.vis.get(layer, True) else Qt.Unchecked)
            self._layer_items[layer] = it
        (parent.addChild if isinstance(parent, QTreeWidgetItem) else parent.addTopLevelItem)(it)
        return it

    def refresh(self, project):
        from . import procmeta as pm
        expanded = {self._key(i) for i in self._iter() if i.isExpanded()}
        selected = set(self.selected_roles())
        scroll = self.verticalScrollBar().value()
        first = not expanded
        self._filling = True
        self.setUpdatesEnabled(False)
        try:
            self.clear(); self._layer_items = {}
            n_img = len(project.dataset.cameras)
            name = os.path.splitext(os.path.basename(project.path))[0] if project.path else "Untitled"
            root = self._item(self, f"{name} ({n_img:,} images)", ("project", project.active), "workspace", bold=True)
            for ci, ch in [(project.active, project.dataset)]:
                active = ci == project.active
                parts = [f"{len(ch.cameras):,} images"]
                if ch.markers:
                    parts.append(f"{len(ch.markers):,} markers")
                if ch.tie_point_count:
                    parts.append(f"{ch.tie_point_count:,} tie points")
                crs = (ch.georef or {}).get("crs") or ch.crs
                it = root
                it.setToolTip(0, ("Georeferenced: " + crs) if ch.georef else "Not georeferenced (local frame)")
                lay = (lambda k: k) if active else (lambda k: None)
                al = ch.aligned_count()
                imgs = self._item(it, f"Images ({al:,}/{len(ch.cameras):,} aligned)", ("cameras", ci), "folder",
                                  layer=lay("cameras"))
                groups = pm.camera_groups(ch)
                if len(groups) > 1:
                    parents = {g[3]: self._item(imgs, f"{g[0]} ({g[1]:,}/{g[2]:,} aligned)", ("group", ci, g[3]),
                                                "folder") for g in groups}
                else:
                    parents = None
                aligned_run = bool(ch.tie_point_count)
                for k, c in enumerate(ch.cameras):
                    par = parents[(c.width, c.height) if c.width and c.height else None] if parents else imgs
                    na = aligned_run and not c.aligned
                    ci_ = QTreeWidgetItem([c.label + ("  (NA)" if na else "")])
                    ci_.setData(0, ROLE, ("camera", ci, k))
                    ci_.setIcon(0, self._icon("photo" if c.enabled else "photo_off"))
                    ci_.setCheckState(0, Qt.Checked if c.enabled else Qt.Unchecked)
                    if na:
                        ci_.setForeground(0, QBrush(QColor(200, 120, 120)))
                        ci_.setToolTip(0, "Not aligned")
                    elif not c.enabled:
                        ci_.setForeground(0, QBrush(QColor(130, 130, 130)))
                        ci_.setToolTip(0, "Disabled")
                    par.addChild(ci_)
                if ch.markers:
                    nctl = sum(1 for m in ch.markers if m.get("enabled", True))
                    mk = self._item(it, f"Markers ({len(ch.markers):,})", ("markers", ci), "markers",
                                    layer=lay("markers"),
                                    tip=f"{nctl} control, {len(ch.markers) - nctl} check")
                    for m in ch.markers:
                        ctl = m.get("enabled", True)
                        r = self._item(mk, m["label"] + ("" if ctl else "  (check)"), ("marker", ci, m["label"]),
                                       "markers")
                        from .marker_style import flag_icon, marker_state
                        r.setIcon(0, flag_icon(marker_state(m)))
                        if not ctl:
                            r.setForeground(0, QBrush(QColor(120, 210, 240)))
                if ch.tie_point_count:
                    self._item(it, f"Tie Points ({pm.summary(ch, 'tie')})", ("tie", ci), "tie", layer=lay("tie"))
                dm = (ch.meta or {}).get("depth_maps")
                if dm:
                    self._item(it, f"Depth Maps ({pm.summary(ch, 'depth')})", ("depth", ci), "depth")
                if ch.point_cloud_ply:
                    self._item(it, f"Point Cloud ({pm.summary(ch, 'cloud')})", ("cloud", ci), "cloud",
                               layer=lay("cloud"))
                if ch.model_ply:
                    self._item(it, f"3D Model ({pm.summary(ch, 'model')})", ("model", ci), "mesh",
                               layer=lay("mesh"))
                if getattr(ch, "tiled_model", None):
                    self._item(it, f"Tiled Model ({pm.summary(ch, 'tiled')})" + _outdated(ch.tiled_model), ("tiled", ci), "mesh",
                               layer=lay("tiled"))
                if getattr(ch, "dem", None):
                    self._item(it, f"DEM ({pm.summary(ch, 'dem')})" + _outdated(ch.dem), ("dem", ci), "dem", layer=lay("dem"),
                               tip="Digital elevation model - double-click to show it in the Ortho view")
                if getattr(ch, 'dtm', None):
                    self._item(it, f"DTM ({ch.dtm.get('width', '?')} x {ch.dtm.get('height', '?')})" + _outdated(ch.dtm),
                               ('dtm', ci), 'dem', layer=lay('dtm'), tip='Ground-only terrain model; double-click to display')
                if getattr(ch, "orthomosaic", None):
                    o = ch.orthomosaic
                    tip = (f"Created {o.get('created', '?')}; surface {o.get('surface')}, blending {o.get('blending')}"
                           f", hole filling {'on' if o.get('hole_filling') else 'off'}, ghosting filter "
                           f"{'on' if o.get('ghosting') else 'off'}")
                    self._item(it, f"Orthomosaic ({pm.summary(ch, 'ortho')})" + _outdated(ch.orthomosaic), ("ortho", ci), "ortho",
                               layer=lay("ortho"), tip=tip)
                sset = self.shape_provider(ci) if (self.shape_provider and getattr(ch, "shapes", None)) else None
                if sset and sset.get("shapes"):
                    self._shape_rows(it, ci, ch, sset, lay("shapes"))
                it.setExpanded(True)
            root.setExpanded(True)
            for row in self._iter():
                if self._key(row) in selected:
                    row.setSelected(True)
            self.verticalScrollBar().setValue(scroll)
            if not first:
                for i in self._iter():
                    if self._key(i) in expanded:
                        i.setExpanded(True)
        finally:
            self.setUpdatesEnabled(True)
            self._filling = False

    def _shape_rows(self, parent, ci, ch, sset, layer):
        from .shapes import shape_name
        from PySide6.QtGui import QPixmap, QIcon
        n = len(sset["shapes"])
        top = self._item(parent, f"Shapes ({n:,})", ("shapes", ci), "shapes", layer=layer,
                         tip="Imported shapes - File > Import > Import Shapes...")
        hidden = set((ch.shapes or {}).get("hidden") or [])
        by = {}
        for k, s in enumerate(sset["shapes"]):
            by.setdefault(s["layer"], []).append(k)
        for li, L in enumerate(sset["layers"]):
            idx = by.get(li, [])
            r = QTreeWidgetItem([f"{L['name']} ({len(idx):,})"])
            r.setData(0, ROLE, ("shape_layer", ci, L["name"]))
            pm = QPixmap(14, 14); pm.fill(QColor(*[int(v) for v in L.get("color", (255, 140, 0))[:3]]))
            r.setIcon(0, QIcon(pm))
            r.setCheckState(0, Qt.Unchecked if L["name"] in hidden else Qt.Checked)
            src = L.get("source") or ""
            r.setToolTip(0, f"{L.get('format', '')} {src}".strip())
            top.addChild(r)
            for k in idx[:MAX_SHAPE_ROWS]:
                s = sset["shapes"][k]
                c = QTreeWidgetItem([shape_name(s, k)])
                c.setData(0, ROLE, ("shape", ci, k))
                c.setIcon(0, self._icon("shapes"))
                r.addChild(c)
            if len(idx) > MAX_SHAPE_ROWS:
                more = QTreeWidgetItem([f"... {len(idx) - MAX_SHAPE_ROWS:,} more"])
                more.setDisabled(True); r.addChild(more)

    def _iter(self):
        stack = [self.topLevelItem(k) for k in range(self.topLevelItemCount())]
        while stack:
            it = stack.pop()
            yield it
            stack += [it.child(k) for k in range(it.childCount())]

    @staticmethod
    def _key(it):
        d = it.data(0, ROLE)
        return tuple(d) if d else None

    def set_layer_states(self, states):
        """Mirror layer visibility (from menu/toolbar) in the row checkboxes."""
        self.vis.update(states)
        self._filling = True
        try:
            for key, on in states.items():
                it = self._layer_items.get(key)
                if it is not None:
                    it.setCheckState(0, Qt.Checked if on else Qt.Unchecked)
        finally:
            self._filling = False

    def _changed(self, item, _col=0):
        if self._filling:
            return
        d = item.data(0, ROLE)
        if not d:
            return
        on = item.checkState(0) == Qt.Checked
        if d[0] in ROW_LAYER and self._layer_items.get(ROW_LAYER[d[0]]) is item:
            self.vis[ROW_LAYER[d[0]]] = on
            self.layerToggled.emit(ROW_LAYER[d[0]], on)
        elif d[0] == "camera":
            self.contextAction.emit(f"set_camera:{d[2]}:{int(on)}", d[1])
        elif d[0] == "shape_layer":
            self.contextAction.emit(f"shape_layer:{int(on)}:{d[2]}", d[1])

    def _dbl(self, item, _):
        d = item.data(0, ROLE)
        if not d:
            return
        if d[0] == "camera":
            self.cameraActivated.emit(d[1], d[2])
        elif d[0] == "marker":
            self.markerActivated.emit(d[2])
        elif d[0] in ("tie", "cloud", "model", "markers", "cameras", "depth", "tiled", "ortho", "dem", "shapes"):
            self.showRequested.emit(d[0], d[1])
        elif d[0] == "shape":
            self.contextAction.emit(f"show_shape:{d[2]}", d[1])
        elif d[0] == "shape_layer":                   # double-click a layer: its style window
            self.contextAction.emit(f"shape_style:layer:{d[2]}", d[1])

    def selected_roles(self):
        return [tuple(i.data(0, ROLE)) for i in self.selectedItems() if i.data(0, ROLE)]

    def _sel(self):
        items = self.selectedItems()
        if items and items[0].data(0, ROLE):
            d = items[0].data(0, ROLE)
            if d[0] == "workspace":
                return
            self.selectionInfo.emit({"kind": d[0], "dataset": d[1], "index": d[2] if len(d) > 2 else None})

    def _menu(self, pos):
        item = self.itemAt(pos)
        d = item.data(0, ROLE) if item else None
        ci = d[1] if d and len(d) > 1 else -1
        m = QMenu(self)
        if d and d[0] == "camera":
            m.addSeparator(); m.addAction("Open Photo"); m.addAction("Enable/Disable Camera"); m.addAction("Align Selected Photos from GCPs")
        if d and d[0] in ("camera", "cameras", "group", "project"):
            m.addSeparator(); m.addAction("Change Image Paths...")
        if d and d[0] in ("tie", "cloud", "model", "tiled", "ortho", "dem", "shapes"):
            m.addSeparator(); m.addAction("Show")
        if d and d[0] in ("marker", "markers"):
            m.addSeparator(); m.addAction("Add Marker")
            if d[0] == "marker":
                m.addAction("Rename Marker..."); m.addAction("Remove Marker")
            m.addAction("Filter Photos by Markers"); m.addAction("Reset Filter")
        if d and d[0] in ("shapes", "shape_layer", "shape"):
            m.addSeparator()
            m.addAction({"shapes": "Shape Settings...", "shape_layer": "Layer Style...",
                         "shape": "Shape Style..."}[d[0]])
            m.addAction("Export Shapes...")
            m.addAction("Remove Layer" if d[0] == "shape_layer" else "Remove Shapes")
        a = m.exec(self.viewport().mapToGlobal(pos))
        if a:
            if a.text() == "Open Photo":
                self.cameraActivated.emit(d[1], d[2])
            elif a.text() == "Align Selected Photos from GCPs":
                self.contextAction.emit("register_camera:%d" % d[2], ci)
            elif a.text() == "Enable/Disable Camera":
                self.contextAction.emit("toggle_camera:%d" % d[2], ci)
            elif a.text() == "Show":
                self.showRequested.emit(d[0], d[1])
            elif a.text() == "Remove Layer":
                self.contextAction.emit(f"remove_shape_layer:{d[2]}", ci)
            elif a.text() == "Layer Style..." and d[0] == "shape_layer":
                self.contextAction.emit(f"shape_style:layer:{d[2]}", ci)
            elif a.text() == "Shape Style...":
                self.contextAction.emit(f"shape_style:shape:{d[2]}", ci)
            elif a.text() == "Shape Settings...":
                self.contextAction.emit("shape_style:all:", ci)
            elif a.text() in ("Rename Marker...", "Remove Marker", "Filter Photos by Markers", "Reset Filter",
                              "Add Marker"):
                labels = [r[2] for r in self.selected_roles() if r[0] == "marker"] or \
                    ([d[2]] if d[0] == "marker" else [])
                if a.text() == "Filter Photos by Markers" and d[0] == "markers" and not labels:
                    labels = ["*"]
                self.contextAction.emit("marker:" + a.text() + ":" + "\x1f".join(labels), ci)
            else:
                self.contextAction.emit(a.text(), ci)


class ReferencePane(QTableWidget):
    """Camera coordinates and errors; GPS policy is project-wide in Settings."""
    COLS = ["Cameras", "X / Longitude", "Y / Latitude", "Z / Altitude", "Accuracy (m)",
            "Error (m)", "X estimated", "Y estimated", "Z estimated"]
    cameraActivated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLS), parent)
        self.setHorizontalHeaderLabels(self.COLS)
        self.verticalHeader().hide()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self._filling = False
        self.cellClicked.connect(self._activate_camera)

    def _activate_camera(self, row, column):
        item = self.item(row, 0)
        if item is not None and item.data(ROLE) is not None:
            self.cameraActivated.emit(item.data(ROLE))

    def refresh(self, dataset):
        import math
        import numpy as np
        from .georef import CRS
        from .photo_gps import use_photo_gps, reported_accuracy
        gps_enabled = use_photo_gps(dataset)
        selected = {self.item(r, 0).data(ROLE) for r in {i.row() for i in self.selectedIndexes()}
                    if self.item(r, 0)}
        scroll = self.verticalScrollBar().value()
        errors = []
        self._filling = True
        try:
            with bulk_fill(self):
                self.clearContents()
                self.data_row_count = len(dataset.cameras)
                self.setRowCount(self.data_row_count + 1)
                geo = dataset.georef or {}
                try:
                    crs = CRS.parse(geo.get("crs") or dataset.crs)
                except ValueError:
                    crs = CRS()
                for row, camera in enumerate(dataset.cameras):
                    est = list(camera.est) if camera.est is not None else [None] * 3
                    ref = [camera.lon, camera.lat, camera.alt]
                    err = None
                    has_gps = all(v is not None and math.isfinite(v) for v in ref)
                    if geo.get("offset") is not None and est[0] is not None:
                        est = (np.asarray(est) + np.asarray(geo["offset"])).tolist()
                        if has_gps and crs.kind in ("utm", "wgs84", "proj"):
                            try:
                                if crs.kind == 'proj':
                                    from pyproj import Transformer
                                    gps = np.asarray(Transformer.from_crs(4326, crs.name, always_xy=True).transform(*ref))
                                else:
                                    gps = CRS.parse("EPSG:4326").to_metric(np.asarray([ref]), (crs.zone, crs.south) if crs.kind == "utm" else geo.get("zone"), geo.get("coordinate_frame"))[0]
                                if crs.kind in ("utm", "proj"):
                                    ref = gps.tolist()
                                err = float(np.linalg.norm(np.asarray(est) - gps))
                            except (ValueError, TypeError):
                                pass
                    height_verified = ('camera_height_reference' not in geo or
                                       (geo.get('camera_height_reference') == geo.get('height_reference') and
                                        geo.get('height_reference') not in (None, 'unknown')))
                    if not height_verified:
                        err = None
                    if err is not None and gps_enabled and camera.enabled:
                        errors.append(err)
                    accuracy = reported_accuracy(camera)
                    values = [camera.label, _fmt(ref[0]), _fmt(ref[1]), _fmt(ref[2], 3),
                              _fmt((dataset.reference_settings or {}).get("camera_accuracy", 10.0), 3) if has_gps else "",
                              _fmt(err, 3), *[_fmt(v, 3) for v in est]]
                    for col, value in enumerate(values):
                        item = QTableWidgetItem(value)
                        item.setData(ROLE, row)
                        if col == 5 and not height_verified:
                            item.setToolTip('3D GPS residual unavailable until camera and model height references are confirmed compatible.')
                        if col == 4 and accuracy is not None:
                            item.setToolTip('Reported E/N/height deviations: ' + ' / '.join(f'{value:.6g}' for value in accuracy) +
                                            ' m. Used only when reported photo accuracy is explicitly enabled; transformed to adjustment-frame axes before fitting.')
                            if dataset.reference_settings.get('reported_gps_accuracy', False):
                                item.setText(' / '.join(f'{value:.4g}' for value in accuracy))
                        if col == 0:
                            from .icons import icon
                            item.setIcon(icon("photo"))
                            item.setFlags(item.flags() & ~Qt.ItemIsUserCheckable)
                            item.setToolTip("Photo GPS is controlled by Use Photo GPS in Settings." if has_gps else
                                            "No complete GPS position; this photo can still be aligned.")
                        self.setItem(row, col, item)
                    if row in selected:
                        self.selectRow(row)
                self.summary_row = self.data_row_count
                rmse = math.sqrt(sum(x * x for x in errors) / len(errors)) if errors else None
                self.error_summary = {"error": rmse, "measured": len(errors)}
                tip = f"Camera RMSE from {len(errors)} GPS references with measured errors."
                for column in range(self.columnCount()):
                    self.setItem(self.summary_row, column, summary_item(tooltip=tip))
                self.item(self.summary_row, 0).setText("Total Error")
                self.item(self.summary_row, 5).setText(_fmt(rmse, 3) if rmse is not None else "—")
        finally:
            self._filling = False
            self.verticalScrollBar().setValue(scroll)



class MarkersPane(QTableWidget):
    """Markers (ground control / check points) with reference and errors.

    Double-click a Markers / X / Y / Z / Accuracy cell to edit it (validated by
    the main window; Edit > Undo reverts). Double-click another cell opens the
    marker's photo. Right-click: Add / Rename / Remove Marker, Filter Photos
    by Markers, Reset Filter. The checkbox makes the marker a control (checked)
    or check (unchecked) point."""
    COLS = ["Markers", "X/Easting", "Y/Northing", "Z/Altitude", "Accuracy (m)",
            "Error (m)", "Projections", "Error (pix)"]
    EDITABLE = (0, 1, 2, 3, 4)
    markerActivated = Signal(str)
    markerToggled = Signal(str, bool)
    markerEdited = Signal(str, int, str)        # label, column, new text
    markerAction = Signal(str, list)            # menu action, selected labels

    def __init__(self, parent=None):
        super().__init__(0, len(self.COLS), parent)
        self.setHorizontalHeaderLabels(self.COLS)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self._busy = False
        self.pending = {}
        self.itemChanged.connect(self._changed)
        self.cellDoubleClicked.connect(self._dbl)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    def _dbl(self, r, c):
        if c not in self.EDITABLE and self.item(r, 0) and self.item(r, 0).data(ROLE) is not None:
            self.markerActivated.emit(self.item(r, 0).data(ROLE) or self.item(r, 0).text())

    def refresh(self, dataset):
        self._busy = True
        try:
            with bulk_fill(self):
                self._fill(dataset)
        finally:
            self._busy = False

    def _fill(self, dataset):
        ms = getattr(dataset, "markers", None) or []
        rows = {r.get("label"): r for r in (getattr(dataset, "georef", {}) or {}).get("rows", [])}
        selected = set(self.selected_labels())
        self.clearContents()
        self.data_row_count = len(ms)
        self.setRowCount(len(ms) + 2)
        self._marker_groups = [bool(m.get("enabled", True)) for m in ms]
        self.error_summary = marker_error_summary(ms, rows)
        for r, m in enumerate(ms):
            pend = (self.pending or {}).get(m["label"])
            ref = pend or m.get("ref") or [None, None, None]
            acc = m.get("acc")
            e = rows.get(m["label"], {})
            proj = m.get("projections", {})
            pinned = sum(1 for v in proj.values() if len(v) < 3 or v[2])
            vals = [m["label"], _fmt(ref[0], 4), _fmt(ref[1], 4), _fmt(ref[2], 4),
                    "" if not acc else (f"{acc[0]:.3f}" if acc[0] == acc[1] else f"{acc[0]:.3f}/{acc[1]:.3f}"),
                    _fmt(e.get("total"), 4), f"{pinned}/{len(proj)}", _fmt(e.get("pix"), 3)]
            for k, v in enumerate(vals):
                it = QTableWidgetItem(v)
                it.setData(ROLE, m["label"])            # label before any edit
                if k not in self.EDITABLE:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if k == 0:
                    it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                    it.setCheckState(Qt.Checked if m.get("enabled", True) else Qt.Unchecked)
                    it.setToolTip(("Control point" if m.get("enabled", True) else "Check point") +
                                  (" - ignored" if m.get("disabled", False) else "") +
                                  "; checkbox changes Control/Check; double-click to rename")
                    from .marker_style import flag_icon, marker_state
                    it.setIcon(flag_icon(marker_state(m)))
                    if m.get("disabled"):
                        it.setForeground(QBrush(QColor(150, 150, 150)))
                    it.setData(ROLE + 1, bool(m.get("enabled", True)))
                elif k in (1, 2, 3, 4):
                    it.setToolTip("Double-click to edit" + (" (incomplete: enter X, Y and Z)" if pend else ""))
                    if pend:
                        f = it.font(); f.setItalic(True); it.setFont(f)
                        it.setForeground(QBrush(QColor(230, 160, 60)))
                elif k == 6:
                    it.setToolTip(f"{pinned} pinned / {len(proj)} locations. Gray predictions are display hints; "
                                  "blue refined placements and green pins are image observations.")
                self.setItem(r, k, it)
            if m["label"] in selected:
                from PySide6.QtCore import QItemSelectionModel
                self.selectionModel().select(self.model().index(r, 0),
                                             QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.summary_rows = {}
        for offset, group in enumerate(("Control points", "Check points")):
            index = len(ms) + offset
            self.summary_rows[group] = index
            totals = self.error_summary[group]
            tip = (f"RMSE: {totals['measured']} measured coordinate errors / {totals['count']} points. "
                   "Pixel RMSE is weighted by observation count; ignored points are excluded.")
            for column in range(self.columnCount()):
                self.setItem(index, column, summary_item(tooltip=tip))
            self.item(index, 0).setText(group)
            self.item(index, 5).setText(_fmt(totals["error"], 3) if totals["error"] is not None else "—")
            self.item(index, 7).setText(_fmt(totals["pixel"], 3) if totals["pixel"] is not None else "—")
            self.setRowHidden(index, False)
        self.filter_group(getattr(self, "_group", 0))

    def filter_group(self, group):
        if group != getattr(self, "_group", 0):
            self.clearSelection()
            self.setCurrentCell(-1, -1)
        self._group = group
        for row, control in enumerate(getattr(self, "_marker_groups", [])):
            self.setRowHidden(row, (group == 1 and not control) or (group == 2 and control))

    def _changed(self, it):
        if self._busy or it.data(ROLE) is None:
            return
        label = it.data(ROLE)
        if it.column() == 0:
            on = it.checkState() == Qt.Checked
            if it.data(ROLE + 1) is not None and bool(it.data(ROLE + 1)) != on:
                self._busy = True; it.setData(ROLE + 1, on); self._busy = False
                self.markerToggled.emit(label, on)
                return
            if it.text() != label:
                self.markerEdited.emit(label, 0, it.text())
            return
        if it.column() in self.EDITABLE:
            self.markerEdited.emit(label, it.column(), it.text())

    def current_label(self):
        r = self.currentRow()
        it = self.item(r, 0) if r >= 0 else None
        return it.data(ROLE) if it else None

    def selected_labels(self):
        rows = sorted({i.row() for i in self.selectedIndexes()})
        out = []
        for r in rows:
            it = self.item(r, 0)
            if it and it.data(ROLE) is not None:
                out.append(it.data(ROLE))
        return out

    def _menu(self, pos):
        it = self.itemAt(pos)
        if it is not None and it.row() not in {i.row() for i in self.selectedIndexes()}:
            self.selectRow(it.row())
        labels = self.selected_labels()
        m = QMenu(self)
        m.addAction("Add Marker")
        for name in ("Rename Marker...", "Remove Markers", "-", "Show Marker", "Filter Photos by Markers",
                     "Reset Filter"):
            if name == "-":
                m.addSeparator(); continue
            a = m.addAction(name)
            a.setEnabled(bool(labels) or name == "Reset Filter")
        a = m.exec(self.viewport().mapToGlobal(pos))
        if a:
            self.markerAction.emit(a.text(), labels)



def marker_error_summary(markers, rows):
    """Coordinate RMSE per marker; pixel RMSE weighted by observation count."""
    import math
    summary = {}
    for group in ("Control points", "Check points", "All points"):
        values, pixels, weights = [], [], []
        eligible = [m for m in markers if not m.get("disabled", False) and
                    (group == "All points" or bool(m.get("enabled", True)) == (group == "Control points"))]
        for marker in eligible:
            row = rows.get(marker["label"], {})
            error = row.get("total")
            if error is not None and math.isfinite(error):
                values.append(error)
            pixel = row.get("pix")
            if pixel is not None and math.isfinite(pixel):
                weight = max(1, row.get("n") or len(marker.get("projections", {})))
                pixels.append(pixel); weights.append(weight)
        summary[group] = {"count": len(eligible), "measured": len(values),
                          "error": math.sqrt(sum(e * e for e in values) / len(values)) if values else None,
                          "pixel": math.sqrt(sum(e * e * w for e, w in zip(pixels, weights)) / sum(weights))
                                   if weights else None}
    return summary


def markers_panel(table):
    from PySide6.QtWidgets import QTabBar
    panel = QWidget()
    layout = QVBoxLayout(panel); layout.setContentsMargins(2, 2, 2, 2)
    groups = QTabBar()
    for text in ("All points", "Control points", "Check points"):
        groups.addTab(text)
    groups.currentChanged.connect(table.filter_group)
    layout.addWidget(groups); layout.addWidget(table, 1)
    return panel


class PhotosPane(QListWidget):
    photoActivated = Signal(int)
    registerRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(120, 90))
        self.setGridSize(QSize(140, 120))
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setSpacing(4)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.itemClicked.connect(lambda it: self.photoActivated.emit(it.data(ROLE)))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._photo_menu)
        self._cache = {}

    def _photo_menu(self, pos):
        item=self.itemAt(pos)
        if item is not None and not item.isSelected():
            self.clearSelection(); item.setSelected(True)
        menu=QMenu(self)
        action=menu.addAction("Align Selected Photos from GCPs")
        action.setEnabled(bool(self.selectedItems()))
        if menu.exec(self.viewport().mapToGlobal(pos)) is action:
            self.registerRequested.emit()

    _placeholder = None

    @classmethod
    def placeholder(cls):
        if cls._placeholder is None:
            pm = QPixmap(120, 90); pm.fill(QColor(70, 70, 76))
            from PySide6.QtGui import QPainter
            p = QPainter(pm); p.setPen(QColor(150, 150, 158)); p.drawRect(0, 0, 119, 89)
            p.drawText(pm.rect(), Qt.AlignCenter, "..."); p.end()
            cls._placeholder = QIcon(pm)
        return cls._placeholder

    def _icon(self, cam):
        """Small cached thumbnail only - the original photo (often 20+ MB) is
        never decoded here; thumbnails are made by a background job."""
        key = cam.thumb
        if not key or not os.path.exists(key):
            return self.placeholder()
        if key not in self._cache:
            self._cache[key] = QIcon(QPixmap(key))
        return self._cache[key]

    def set_thumb(self, k, cam):
        it = self.item(k)
        if it is not None and it.data(ROLE) == k:
            it.setIcon(self._icon(cam))

    filter = None                      # set of photo indices shown, or None (all)

    def set_filter(self, indices):
        """Filter Photos by Markers: show only these photo indices (None = all)."""
        self.filter = None if indices is None else set(indices)
        for r in range(self.count()):
            it = self.item(r)
            it.setHidden(self.filter is not None and it.data(ROLE) not in self.filter)

    def visible_indices(self):
        return [self.item(r).data(ROLE) for r in range(self.count()) if not self.item(r).isHidden()]

    def refresh(self, dataset):
        """Marker edits leave existing items, selection and scroll position intact."""
        identity = tuple(c.path for c in dataset.cameras)
        same = getattr(self, "_photo_identity", None) == identity
        selected = {it.data(ROLE) for it in self.selectedItems()}
        current = self.currentRow()
        scroll = self.verticalScrollBar().value()
        self.setUpdatesEnabled(False)
        blocked = self.blockSignals(True)
        try:
            if not same:
                self.clear()
            for k, camera in enumerate(dataset.cameras):
                item = self.item(k) if same else QListWidgetItem()
                if not same:
                    item.setData(ROLE, k)
                    self.addItem(item)
                item.setText(camera.label)
                item.setIcon(self._icon(camera))
                item.setToolTip(camera.path + ("\nAligned" if camera.aligned else "\nNot aligned"))
                item.setForeground(QBrush() if camera.enabled else QBrush(QColor(130, 130, 130)))
                item.setHidden(self.filter is not None and k not in self.filter)
                if not same:
                    item.setSelected(k in selected)
            if not same and 0 <= current < self.count():
                self.setCurrentRow(current, QItemSelectionModel.NoUpdate)
            self._photo_identity = identity
            self.verticalScrollBar().setValue(scroll)
        finally:
            self.blockSignals(blocked)
            self.setUpdatesEnabled(True)


class ConsolePane(QWidget):
    """Log output plus a Python command line with access to the app."""

    def __init__(self, namespace: dict, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self); lay.setContentsMargins(2, 2, 2, 2)
        self.out = QPlainTextEdit(); self.out.setReadOnly(True)
        self.out.setMaximumBlockCount(10000)
        f = self.out.font(); f.setFamily("Monospace"); f.setStyleHint(f.StyleHint.Monospace)
        self.out.setFont(f)
        self.inp = QLineEdit(); self.inp.setPlaceholderText(">>> Python (objects: app, window, project)")
        self.inp.returnPressed.connect(self._run)
        lay.addWidget(self.out, 1); lay.addWidget(self.inp)
        self.ns = namespace
        # plain-text history for error reports (readable from any thread)
        self.history = collections.deque(maxlen=20000)
        self.written = 0

    def mark(self):
        """Position in the history; lines_since(mark) gives what came after."""
        return self.written

    def lines_since(self, mark=0, n=None):
        lines = list(self.history)
        first = self.written - len(lines)
        lines = lines[max(0, mark - first):]
        return lines[-n:] if n else lines

    def write(self, text):
        for line in str(text).splitlines() or [""]:
            self.history.append(line)
            self.written += 1
        self.out.appendPlainText(text)
        sb = self.out.verticalScrollBar(); sb.setValue(sb.maximum())

    def _run(self):
        code = self.inp.text(); self.inp.clear()
        self.write(">>> " + code)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                try:
                    r = eval(code, self.ns)
                    if r is not None:
                        print(repr(r))
                except SyntaxError:
                    exec(code, self.ns)
        except Exception as e:
            buf.write(f"{type(e).__name__}: {e}\n")
        if buf.getvalue():
            self.write(buf.getvalue().rstrip())


class PropertiesPane(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["Property", "Value"])
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWordWrap(False)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setMinimumSectionSize(16)
        self.verticalHeader().setDefaultSectionSize(max(18, self.fontMetrics().height() + 2))
        self.setStyleSheet("QTableView::item { padding: 0px 3px; }")

    def show_props(self, props: dict):
        self.setUpdatesEnabled(False)
        self.setRowCount(len(props))
        for r, (k, v) in enumerate(props.items()):
            self.setItem(r, 0, QTableWidgetItem(str(k)))
            value = QTableWidgetItem(str(v)); value.setToolTip(str(v))
            self.setItem(r, 1, value)
        self.setUpdatesEnabled(True)


class JobsPane(QListWidget):
    def add_job(self, text):
        self.addItem(text); self.scrollToBottom()
