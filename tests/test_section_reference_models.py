"""Known-answer survey models through file I/O, geometry and the actual Qt tool."""
from pathlib import Path

import numpy as np
import pytest

from tools.verify_section_reference import reference_models, run_checks, write_mesh

ROOT=Path(__file__).resolve().parents[1]


def test_reference_models_match_closed_form_geometry(tmp_path):
    report=run_checks(ROOT,tmp_path)
    assert len(report['checks'])==46
    assert report['passed'],[row for row in report['checks'] if not row['passed']]


def test_reference_audit_detects_wrong_height_sign(tmp_path,monkeypatch):
    from photomesh import survey_geometry
    original=survey_geometry.distance_components

    def incorrect(*args):
        result=original(*args);result['height']=-result['height'];return result

    monkeypatch.setattr(survey_geometry,'distance_components',incorrect)
    report=run_checks(ROOT,tmp_path)
    assert not report['passed']
    assert any(not row['passed'] and 'signed height' in row['name'] for row in report['checks'])


@pytest.mark.parametrize('name,start,end,horizontal,height,distance,surface_length',[
    ('plane_3_4_12',[0,0],[3,4],5,12,13,13),
    ('ramp_flat_rise_flat',[0,0],[10,0],10,4,np.sqrt(116),12),
])
def test_reference_section_ui_uses_surface_and_reports_endpoint_chord(
        window,tmp_path,qtbot,name,start,end,horizontal,height,distance,surface_length):
    vertices,faces=reference_models()[name]
    path=tmp_path/(name+'.ply');write_mesh(path,vertices,faces)
    window.project.path=str(tmp_path/'reference.pmsx')
    window.dataset.model_ply=str(path);window.dataset.face_count=len(faces)
    window.set_layer_visible('mesh',True)
    window.show_cross_section()
    window._survey_set_point(start)
    window._survey_set_point(end)
    qtbot.waitUntil(lambda: window._survey_profile is not None and not window._survey_busy,timeout=15000)
    panel=window._survey_dialog
    metrics=window.measure_points(*window._survey_endpoints_model)
    np.testing.assert_allclose([metrics['horizontal'],metrics['height'],metrics['distance']],
                               [horizontal,height,distance],rtol=0,atol=1e-8)
    text=panel.result.text()
    assert f'Horizontal: {horizontal:.6g}' in text
    assert f'3D distance: {distance:.6g}' in text
    assert f'ΔZ: {height:.6g}' in text
    along,z=window._survey_profile
    valid=np.isfinite(along)&np.isfinite(z)
    section=np.column_stack([along[valid],z[valid]]).reshape(-1,2,2)
    length=np.linalg.norm(np.diff(section,axis=1),axis=2).sum()
    assert length==pytest.approx(surface_length,rel=0,abs=1e-8)
    panel.close()
