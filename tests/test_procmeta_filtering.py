"""Compatibility for the Properties exception reported on 2026-11-02."""
import copy
import json
import pytest
from photomesh import procmeta
from photomesh.project import Project


@pytest.mark.parametrize("raw",[
    [["statistical (local)",1234],["radius (local)",56]],
    [("statistical (local)",1234),("radius (local)",56)],
    [{"filter":"statistical (local)","removed":1234},{"filter":"radius (local)","removed":56}],
    {"statistical (local)":1234,"radius (local)":56},
])
def test_cloud_properties_read_old_and_new_statistics(raw):
    project=Project(); chunk=project.chunk
    chunk.meta={"point_cloud":{"filtering":raw}}
    before=copy.deepcopy(chunk.meta)
    values=dict(procmeta.properties(chunk,"cloud"))
    assert values["Filter: statistical (local)"]=="1,234 points removed"
    assert values["Filter: radius (local)"]=="56 points removed"
    assert chunk.meta==before


@pytest.mark.parametrize("value",[None,"broken",3,[],[None,3,["only-name"],{"removed":5}]])
def test_unreadable_statistics_show_unknown_without_crash(value):
    project=Project(); project.chunk.meta={"point_cloud":{"filtering":value}}
    values=dict(procmeta.properties(project.chunk,"cloud"))
    assert values["Filtering steps"]=="unknown"


@pytest.mark.parametrize("value",[-1,True,"not a count",None,1.5,float("nan"),float("inf")])
def test_invalid_counts_are_not_fabricated(value):
    project=Project(); project.chunk.meta={"point_cloud":{"filtering":[["radius",value]]}}
    values=dict(procmeta.properties(project.chunk,"cloud"))
    assert values["Filter: radius"]=="unknown"


def test_record_and_project_roundtrip_store_canonical_statistics(tmp_path):
    project=Project(); chunk=project.chunk
    procmeta.record(chunk,"point_cloud",filtering=[("statistical (local)",1234),("radius",56)])
    path=str(tmp_path/"project.pmsx"); project.save(path)
    # Verify persisted JSON, then reopen through the normal project loader.
    raw=json.loads(open(path,encoding="utf-8").read())
    assert raw["chunks"][0]["meta"]["point_cloud"]["filtering"][0]=={"filter":"statistical (local)","removed":1234}
    loaded=Project.load(path)
    values=dict(procmeta.properties(loaded.chunk,"cloud"))
    assert values["Filter: statistical (local)"]=="1,234 points removed"
