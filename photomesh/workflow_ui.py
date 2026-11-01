"""Lightweight settings feedback; heavy geometry stays in processing workers."""
import json
import math
import os
from PySide6.QtWidgets import (QLabel, QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox,
                              QPushButton, QDialog, QVBoxLayout, QTableWidget,
                              QTableWidgetItem, QDialogButtonBox)
from PySide6.QtCore import Qt


def note(dialog, text, advanced=False):
    label = QLabel(text); label.setWordWrap(True)
    (dialog.aform if advanced else dialog.gform).addRow(label)
    return label


def number(lo, hi, value, decimals=2):
    widget = QDoubleSpinBox(); widget.setRange(lo, hi); widget.setDecimals(decimals); widget.setValue(value)
    return widget


def alignment_context(d, parent):
    cameras = [c for c in getattr(getattr(parent, "chunk", None), "cameras", []) if c.enabled]
    gps = sum(all(v is not None and math.isfinite(v) for v in (c.lon, c.lat, c.alt)) for c in cameras)
    d.reference.setChecked(gps >= 2); d.reference.setEnabled(gps >= 2)
    d.reference.setToolTip(f"{gps}/{len(cameras)} photos have complete GPS; pair selection only, not georeferencing.")
    d.summary = note(d, "")
    d.single_camera.setToolTip("Groups use compatible model, image size and initial calibration. Poses remain independent.")
    d.guided.setToolTip("Use pair geometry to search for additional correspondences; adds matching work.")
    d.accuracy.setToolTip("High = full image; Medium = half dimensions; Low = quarter; Lowest = one eighth.")
    def update(*_):
        from .fastpipe import COARSE_MAX_SIZE
        mode = d.mode.currentText()
        d.reference.setEnabled(mode == "Fast" and gps >= 2)
        maximum = max([max(c.width, c.height) for c in cameras] or [0])
        from .colmap import ACCURACY_DOWNSCALE, find_glomap
        side = max(256, maximum // ACCURACY_DOWNSCALE[d.accuracy.currentText()]) if maximum else 0
        fine = mode == "Fast" and d.c2f.isChecked() and side > COARSE_MAX_SIZE * 1.25
        kind = d.mapper.currentText()
        if kind == "Auto":
            kind = "Global" if len(cameras) >= 100 and find_glomap() else "Incremental"
        text = f"{len(cameras)} photos; solver: {kind}. "
        text += f"Two stages: up to 1024 px / {side} px." if fine else f"One stage: {side or 'unknown'} px."
        if mode == "Fast" and d.c2f.isChecked() and side and not fine:
            text += " Target resolution does not require a second stage."
        text += f" GPS available: {gps}."
        d.summary.setText(text)
    for control in (d.mode, d.mapper, d.accuracy):
        control.currentTextChanged.connect(update)
    d.c2f.toggled.connect(update)
    button = QPushButton("Review calibration groups...")
    d.aform.addRow(button)
    d.calibration_groups = {}
    def groups():
        w = QDialog(d); w.setWindowTitle("Calibration groups")
        layout = QVBoxLayout(w); table = QTableWidget(len(cameras), 2)
        table.setHorizontalHeaderLabels(["Photo", "Group (blank = automatic)"])
        for r, camera in enumerate(cameras):
            name = QTableWidgetItem(camera.label); name.setFlags(name.flags() & ~Qt.ItemIsEditable)
            table.setItem(r, 0, name)
            table.setItem(r, 1, QTableWidgetItem(d.calibration_groups.get(camera.path, "")))
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(w.accept); buttons.rejected.connect(w.reject); layout.addWidget(buttons)
        if w.exec():
            d.calibration_groups = {c.path: table.item(r, 1).text().strip() for r, c in enumerate(cameras)}
    button.clicked.connect(groups)
    update()


def dense_context(d, parent):
    d.local_ratio = number(1, 20, 3)
    d.elevation_k = number(1, 30, 6)
    d.elevation_dev = number(0, 1e6, 0, 4); d.elevation_dev.setSpecialValueText("Auto (survey height)")
    d.outl.layout().addRow("Local isolation ratio:", d.local_ratio)
    d.outl.layout().addRow("Terrain deviation multiplier:", d.elevation_k)
    d.outl.layout().addRow("Minimum terrain deviation (model units):", d.elevation_dev)
    d.up_mode=QComboBox(); d.up_mode.addItems(["Camera-derived up","Project Z","Custom"])
    d.up_values=[number(-1,1,v,5) for v in (0,0,1)]
    d.outl.layout().addRow("Terrain up direction:",d.up_mode)
    for axis,control in zip("XYZ",d.up_values): d.outl.layout().addRow(f"Custom up {axis}:",control)
    def up_mode(*_):
        for control in d.up_values: control.setEnabled(d.up_mode.currentText()=="Custom")
    d.up_mode.currentTextChanged.connect(up_mode); up_mode()
    d.elev.setToolTip("Off by default. Not ground classification; may remove buildings or steep terrain.")
    d.sor.setText("Statistical isolation (local density)")
    d.radius.setText("Neighbour isolation (adaptive distance)")
    d.filtering.setToolTip("Disabled = no PatchMatch depth filter. Fusion consistency checks remain necessary.")
    d.keep_depth.setToolTip("Keep depth/normal maps for later reuse; unchecked removes them only after a valid cloud is published.")
    d.reuse.setToolTip("Reuse only when cameras, photos and all depth-computation parameters match.")
    text = "Depth maps are temporary unless Keep is checked. Processing reports dimensions, disk needs and removals per filter."
    ch = getattr(parent, "chunk", None)
    if ch and ch.workdir:
        from .dense import depth_maps_size
        size, files = depth_maps_size(os.path.join(ch.workdir, "dense"))
        text += f" Existing map files: {files}; {size/2**30:.2f} GiB (compatibility checked at start)."
    note(d, text, True)


def mesh_context(d, parent):
    from .mesh import target_faces
    ch = getattr(parent, "chunk", None)
    d.input_points = getattr(ch, "point_count", 0)
    if ch and ch.workdir:
        path = os.path.join(ch.workdir, "dense", "fused.ply")
        if os.path.isfile(path):
            from .plyio import ply_counts
            try:
                d.input_points_raw = ply_counts(path)[0]
            except ValueError:
                d.input_points_raw = d.input_points
        else:
            d.input_points_raw = d.input_points
    else:
        d.input_points_raw = d.input_points
    d.component_faces = QSpinBox(); d.component_faces.setRange(0, 1_000_000); d.component_faces.setValue(200)
    d.aform.addRow("Minimum component faces (0 = no absolute threshold):", d.component_faces)
    d.voxel.setSuffix(" m" if ch and ch.georef else " model units")
    d.interp.setItemText(0, "Strong trimming")
    d.interp.setItemText(1, "Moderate trimming (default)")
    d.interp.setItemText(2, "Allow extrapolation")
    summary = note(d, "")
    def update(*_):
        poisson = d.source.currentIndex() == 0
        for widget in (d.interp, d.voxel, d.max_pts):
            widget.setEnabled(poisson)
        d.input_points = d.input_points_raw if not poisson else getattr(ch, "point_count", 0)
        custom = d.face_count.currentText() == "Custom"
        d.custom.setEnabled(custom)
        if not custom:
            d.custom.setValue(target_faces(d.input_points, d.face_count.currentText()))
        summary.setText(f"Target: {d.custom.value():,} triangles; {d.input_points:,} source points. "
                        "A target is not a guaranteed final count; cleanup may reduce it.")
    d.source.currentTextChanged.connect(update); d.face_count.currentTextChanged.connect(update)
    d.custom.valueChanged.connect(lambda *_: summary.setText(
        f"Target: {d.custom.value():,} triangles; cleanup may reduce the final count."))
    update()


def texture_context(d, parent, has_uv):
    d.auto_pages = QCheckBox("Automatic page count (otherwise count is a hard maximum)")
    d.auto_pages.setChecked(False); d.aform.addRow(d.auto_pages)
    summary = note(d, "", True)
    def update(*_):
        keep = d.mapping.currentText() == "Keep uv"
        d.count.setEnabled(not keep); d.auto_pages.setEnabled(not keep)
        if keep:
            ch = getattr(parent, "chunk", None)
            d.count.setValue(int((getattr(ch, "texture", {}) or {}).get("count", d.count.value())))
        try:
            size = int(d.size.currentText())
            summary.setText(f"RGB pages alone: {size*size*d.count.value()*3/2**20:.0f} MiB. "
                            "Large builds use disk-backed pages. Hole filling estimates colour, not geometry.")
        except ValueError:
            summary.setText("Enter an integer texture size.")
    d.mapping.currentTextChanged.connect(update); d.size.currentTextChanged.connect(update)
    d.count.valueChanged.connect(update)
    def validate():
        try:
            n = int(d.size.currentText())
        except ValueError:
            raise ValueError("Texture size must be an integer")
        if not 256 <= n <= 32768:
            raise ValueError("Texture size must be between 256 and 32768")
    d.validate_settings = validate
    d.holes.setText("Fill colour where photos provide no coverage")
    d.ghost.setToolTip("Colour outlier rejection requires at least four valid views; coverage is reported.")
    d.mapping.setToolTip("Orthophoto can collapse vertical/overlapping surfaces. Adaptive mapping uses camera charts for steep faces.")
    update()


def tiles_context(d, parent):
    def update(*_):
        points = d.source.currentText() == "Point cloud"
        d.pixel.setEnabled(not points); d.max_tex.setEnabled(not points)
        old = d.fmt.currentText()
        d.fmt.blockSignals(True); d.fmt.clear()
        d.fmt.addItems(["Point tiles (pnts)"] if points else
                       ["Cesium 3D Tiles 1.0 (b3dm)", "Cesium 3D Tiles 1.1 (glb)"])
        if not points and old in [d.fmt.itemText(i) for i in range(d.fmt.count())]:
            d.fmt.setCurrentText(old)
        d.fmt.blockSignals(False)
        label = d.aform.labelForField(d.tile_faces)
        if label:
            label.setText("Points per tile:" if points else "Triangles per tile:")
    d.source.currentTextChanged.connect(update)
    note(d, "Auto uses source texture resolution, or mesh-edge spacing if no texture is available. "
            "A manual value is the requested minimum texel size; effective values are reported.", True)
    update()


def dem_context(d, parent):
    d.aggregation = QComboBox(); d.aggregation.addItems(["Mean", "Median", "Highest"])
    d.max_fill = number(0, 1e6, 10, 4)
    d.smooth_distance = number(0, 1e6, 0, 4)
    d.aform.addRow("Point-cell height:", d.aggregation)
    d.aform.addRow("Maximum fill distance (model units):", d.max_fill)
    d.aform.addRow("Fill smoothing distance (0 = none):", d.smooth_distance)
    note(d, "Surface model (DSM): buildings/vegetation are retained. This is not classified bare earth.")
    grid_info=note(d, "")
    def preview(*_):
        from .ortho import raster_size
        plans=getattr(parent,"_workflow_source_plans",{}) or {}
        plan=plans.get(d.source.currentText())
        if not plan: return
        try:
            bounds=d.region_box.region() or plan["bounds"]
            pixel=d.pixel.value() or plan["auto"]
            px,width,height=raster_size(*bounds,pixel)
            grid_info.setText(f"Estimated grid: {width:,} x {height:,}; pixel ~{px:.6g} model units. "
                              f"Uncompressed heights: {width*height*4/2**20:.0f} MiB; auto is finalized from source density.")
        except ValueError as error: grid_info.setText(str(error))
    def selected_source(*_):
        plan=(getattr(parent,"_workflow_source_plans",{}) or {}).get(d.source.currentText())
        if plan:
            for control,value in zip(d.region_box.spins,plan["bounds"]): control.setValue(value)
        preview()
    d.source.currentTextChanged.connect(selected_source)
    d.pixel.valueChanged.connect(preview); d.region_box.toggled.connect(preview)
    for control in d.region_box.spins: control.valueChanged.connect(preview)
    def update(*_):
        d.aggregation.setEnabled(d.source.currentText() != "Mesh")
        enabled = d.interp.currentText() != "Disabled"
        d.max_fill.setEnabled(enabled and d.interp.currentText() != "Extrapolated")
        d.smooth_distance.setEnabled(enabled)
    d.source.currentTextChanged.connect(update); d.interp.currentTextChanged.connect(update)
    selected_source(); update()


def ortho_context(d, parent):
    d.hole_distance = number(0, 1e6, 0, 4)
    d.hole_distance.setSpecialValueText("Auto (64 output pixels)")
    d.aform.addRow("Maximum fill distance (model units):", d.hole_distance)
    def update(*_):
        d.pixel.setEnabled(d.r_pix.isChecked()); d.maxdim.setEnabled(d.r_max.isChecked())
        d.seams.setEnabled(d.blending.currentText().startswith("Mosaic"))
        if not d.seams.isEnabled():
            d.seams.setChecked(False)
        d.hole_distance.setEnabled(d.holes.isChecked())
        d._update_size()
    d.r_pix.toggled.connect(update); d.blending.currentTextChanged.connect(update)
    d.holes.toggled.connect(update)
    def surface(*_):
        ch = getattr(parent, "chunk", None)
        if ch and d.surface.currentText() == "DEM" and ch.dem.get("bounds"):
            off = ch.dem.get("offset") or [0, 0, 0]
            b = ch.dem["bounds"]
            d.plan = {"bounds": (b[0]-off[0], b[1]-off[1], b[2]-off[0], b[3]-off[1]), "off": off}
        elif hasattr(d, "_mesh_plan"):
            d.plan = d._mesh_plan
        d._update_size()
    d._mesh_plan = d.plan
    d.surface.currentTextChanged.connect(surface)
    d.res.currentTextChanged.connect(d._update_size)
    d.holes.setToolTip("Fills short gaps with inferred heights/colours; does not create measured detail.")
    d.ghost.setToolTip("Coarse colour outlier detection requires four valid views. Coverage is reported.")
    surface(); update()


def prepare_source_plans(window, sources):
    """Cached projection bounds; one bounded scan per changed source, never on GUI thread."""
    from .workflow import file_stamp, vertex_blocks, require_points
    from .bgjob import run_modal
    import numpy as np
    ch=window.chunk
    rotation=np.eye(3)
    if not ch.georef and ch.aligned_count():
        from .tasks import model_up
        from .tiles import rotation_to_z
        rotation=rotation_to_z(model_up(window._model_dir(),False))
        # Use precisely the orthographic frame employed by DEM/Ortho.
        from .texture import load_views
        from .ortho import projection_rotation
        views=load_views(window._model_dir(),window._photo_map(ch),lambda *_:None)
        if views: rotation=projection_rotation(views,False)
    cache=getattr(window,"_workflow_plan_cache",{})
    off=np.asarray((ch.georef or {}).get("offset") or [0,0,0],float)
    def work(report,cancel):
        plans={}
        for index,(name,path) in enumerate(sources.items()):
            key=json.dumps([file_stamp(path),rotation.tolist(),off.tolist()])
            if key in cache: plans[name]=cache[key]; continue
            lo,hi=np.full(3,np.inf),np.full(3,-np.inf); count=0; occupied=set()
            for records in vertex_blocks(path):
                if cancel(): return None
                xyz=np.column_stack([records["x"],records["y"],records["z"]]).astype(float) @ rotation.T
                require_points(xyz)
                lo,hi=np.minimum(lo,xyz.min(0)),np.maximum(hi,xyz.max(0)); count+=len(xyz)
            bounds=[float(lo[0]+off[0]),float(lo[1]+off[1]),float(hi[0]+off[0]),float(hi[1]+off[1])]
            auto=2*math.sqrt(max((hi[0]-lo[0])*(hi[1]-lo[1]),1e-12)/max(count,1))
            plan={"bounds":bounds,"count":count,"auto":auto,"rotation":rotation.tolist()}
            cache[key]=plan; plans[name]=plan; report(index+1,len(sources))
        return plans
    result,cancelled,error=run_modal(window,"Prepare Raster","Checking source extents...",work,len(sources))
    if error: raise ValueError(error)
    if cancelled or result is None: return None
    window._workflow_plan_cache=cache
    return result
