"""Transactional project preparation, with no widget access from workers."""
import os
from .project import Project
from .reference_ui import ReferenceMixin
from . import procmeta
from .photonames import recover_names, photo_map


def prepare_project(path, report, cancelled):
    project = Project.load(path)
    if len(project.datasets) != 1:
        raise ValueError("This legacy project contains multiple datasets. Open it with an older release "
                         "and save each dataset as a separate project before using version 1.0. "
                         "The original file has not been changed.")
    notes = []
    report(1, 4, "Reading project and checking paths")
    if cancelled():
        return None
    dataset = project.dataset
    added = procmeta.backfill(dataset, project.path)
    if added:
        project.modified = True
        notes.append("Processing metadata recovered: " + ", ".join(added))
    report(2, 4, "Recovering camera references")
    if cancelled():
        return None
    if any(c.aligned and not c.colmap_name for c in dataset.cameras):
        if recover_names(dataset, dataset.workdir):
            project.modified = True
    context = ReferenceMixin()
    context.project = project
    context.dataset = dataset
    report(3, 4, "Preparing marker observations")
    markers = None
    if dataset.markers:
        try:
            markers = context._marker_positions()
        except (OSError, ValueError, RuntimeError) as error:
            notes.append(f"Marker display could not be prepared: {error}")
    if cancelled():
        return None
    ambiguous = photo_map(dataset)[1]
    found = [c for c in dataset.cameras if os.path.exists(c.path)]
    shape_cache = None
    shape_path = (dataset.shapes or {}).get("path")
    if shape_path and os.path.exists(shape_path):
        from . import shapes
        try:
            shape_cache = ((shape_path, os.path.getmtime(shape_path)), shapes.load(shape_path))
        except (OSError, ValueError) as error:
            notes.append(f"Shapes could not be loaded: {error}")
    rasters = {}
    from .orthoview import RasterLayer
    for kind, info in (("dem", dataset.dem), ("ortho", dataset.orthomosaic)):
        if info and info.get("path") and os.path.exists(info["path"]):
            try:
                rasters[kind] = RasterLayer(kind, info)
            except (OSError, ValueError, RuntimeError) as error:
                notes.append(f"{kind} could not be opened: {error}")
    if cancelled():
        for raster in rasters.values():
            raster.close()
        return None
    report(4, 4, "Project ready")
    return {"project": project, "notes": notes, "found": found,
            "model_cache": getattr(context, "_model_cache", (None,)),
            "marker_cache": getattr(context, "_marker_xyz_cache", None),
            "markers": markers, "ambiguous": ambiguous, "rasters": rasters, "shape_cache": shape_cache}
