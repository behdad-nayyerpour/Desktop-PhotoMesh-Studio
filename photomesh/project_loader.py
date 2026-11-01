"""Transactional project preparation, with no widget access from workers."""
import os
from .project import Project
from .reference_ui import ReferenceMixin
from . import procmeta
from .photonames import recover_names


def prepare_project(path, report, cancelled):
    project = Project.load(path)
    if len(project.chunks) != 1:
        raise ValueError("This legacy project contains multiple chunks. Open it with an older release "
                         "and save each dataset as a separate project before using version 1.0. "
                         "The original file has not been changed.")
    notes = []
    report(1, 4, "Reading project and checking paths")
    if cancelled():
        return None
    chunk = project.chunk
    added = procmeta.backfill(chunk, project.path)
    if added:
        project.modified = True
        notes.append("Processing metadata recovered: " + ", ".join(added))
    report(2, 4, "Recovering camera references")
    if cancelled():
        return None
    if any(c.aligned and not c.colmap_name for c in chunk.cameras):
        if recover_names(chunk, chunk.workdir):
            project.modified = True
    context = ReferenceMixin()
    context.project = project
    context.chunk = chunk
    report(3, 4, "Preparing marker observations")
    markers = None
    if chunk.markers:
        try:
            markers = context._marker_positions()
        except (OSError, ValueError, RuntimeError) as error:
            notes.append(f"Marker display could not be prepared: {error}")
    if cancelled():
        return None
    found = [c for c in chunk.cameras if os.path.exists(c.path)]
    report(4, 4, "Project ready")
    return {"project": project, "notes": notes, "found": found,
            "model_cache": getattr(context, "_model_cache", (None,)),
            "marker_cache": getattr(context, "_marker_xyz_cache", None),
            "markers": markers}
