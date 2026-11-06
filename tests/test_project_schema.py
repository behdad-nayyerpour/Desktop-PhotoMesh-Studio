"""Project-schema migration and shared split-button behavior."""
import json
import os
import pytest
from photomesh.project import Project, ProjectData, Camera


def test_legacy_record_container_loads_without_touching_sources(tmp_path):
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"source bytes")
    results = tmp_path / "older-results"
    results.mkdir()
    model = results / "model.ply"
    model.write_bytes(b"existing result")
    path = tmp_path / "legacy.pmsx"
    payload = {"format": "photomesh-studio/1", "active": 0, "legacy_records": [{
        "name": "Original survey", "workdir": "older-results", "model_ply": "older-results/model.ply",
        "cameras": [{"path": "photo.jpg", "label": "photo.jpg", "use_reference": False}],
        "markers": [{"label": "G1", "ref": [1, 2, 3], "projections": {}}],
        "georef": {"offset": [10, 20, 30]}, "meta": {"alignment": {"seconds": 3}},
    }]}
    path.write_text(json.dumps(payload))
    source = path.read_bytes()
    project = Project.load(str(path))
    assert path.read_bytes() == source
    assert photo.read_bytes() == b"source bytes" and model.read_bytes() == b"existing result"
    assert project.dataset.workdir == str(results)
    assert project.dataset.model_ply == str(model)
    assert not project.dataset.cameras[0].use_reference
    assert project.dataset.markers[0]["ref"] == [1, 2, 3]
    saved = tmp_path / "new.pmsx"
    project.save(str(saved))
    new = json.loads(saved.read_text())
    assert new["format"] == "photomesh-studio/2"
    assert set(new) == {"format", "active", "datasets"}
    restored = Project.load(str(saved))
    assert restored.dataset.georef == project.dataset.georef
    assert restored.dataset.meta == project.dataset.meta
    assert restored.dataset.markers == project.dataset.markers


def test_legacy_product_only_record_is_not_discarded(tmp_path):
    path = tmp_path / "products.pmsx"
    path.write_text(json.dumps({"format": "photomesh-studio/1", "legacy_records": [{
        "model_ply": "existing.ply", "face_count": 42, "texture": {"size": 1024},
    }]}))
    project = Project.load(str(path))
    assert project.dataset.face_count == 42
    assert project.dataset.model_ply == str(tmp_path / "existing.ply")
    assert project.dataset.texture["size"] == 1024


def test_new_workspace_names_and_save_as_plan(tmp_path):
    from photomesh import datafolder
    project = Project()
    project.path = str(tmp_path / "site.pmsx")
    assert project.default_workdir(project.dataset) == str(tmp_path / "site.files" / "processing")
    os.makedirs(project.dataset.workdir)
    with open(os.path.join(project.dataset.workdir, "result.txt"), "w") as fh:
        fh.write("result")
    items = datafolder.plan(project, str(tmp_path / "copy.pmsx"))
    assert len(items) == 1
    assert items[0]["dst"] == str(tmp_path / "copy.files" / "processing")


def test_reference_xml_roundtrip_uses_application_schema(tmp_path):
    from photomesh.georef import Marker, write_markers_xml, read_markers_xml
    from xml.etree import ElementTree as ET
    marker = Marker("G1", [1., 2., 3.], enabled=False)
    marker.acc = [0.01, 0.02]
    marker.projections = {"p.jpg": [10.25, 20.5, False]}
    path = tmp_path / "reference.xml"
    write_markers_xml(str(path), [marker], "EPSG:32639")
    root = ET.parse(path).getroot()
    assert root.tag == "photomesh-reference" and root.get("version") == "2.0"
    restored, crs = read_markers_xml(str(path))
    assert restored[0].ref == marker.ref and restored[0].acc == marker.acc
    assert restored[0].projections == marker.projections
    assert restored[0].enabled is False
    assert crs.zone == 39


def test_process_batches_preserve_order_and_partial_fallback(monkeypatch):
    from concurrent.futures.process import BrokenProcessPool
    from photomesh import fastpipe
    batches = []

    class Pool:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def map(self, fn, functions, inputs):
            for i, (function, batch) in enumerate(zip(functions, inputs)):
                if i == 2:
                    raise BrokenProcessPool("simulated worker loss")
                batches.append(list(batch))
                yield fn(function, batch)

    monkeypatch.setattr(fastpipe, "ProcessPoolExecutor", Pool)
    values = [-i for i in range(11)]
    assert list(fastpipe.pool_map(abs, values, workers=2, batch_size=4)) == list(range(11))
    assert batches == [values[:4], values[4:8]]
