"""Independent numerical contracts for calibration, references and marker edits."""
import copy
import numpy as np
import pytest
from photomesh import georef as g, colmap_io as cio
from test_dense_mesh_gcp import synthetic_model

PARAMS = {
0: [510.,300.,225.],
1: [520.,470.,300.,225.],
2: [510.,300.,225.,.03],
3: [510.,300.,225.,.03,-.01],
4: [520.,470.,300.,225.,.03,-.01,.001,-.002],
5: [520.,470.,300.,225.,.03,-.01,.002,-.001],
6: [520.,470.,300.,225.,.03,-.01,.001,-.002,.002,.01,.005,-.001]}


def independent_uv(kind, p, xyz):
    x, y = xyz[:,0]/xyz[:,2], xyz[:,1]/xyz[:,2]
    if kind in (0,2,3):
        fx = fy = p[0]; cx,cy = p[1:3]
    else:
        fx,fy,cx,cy = p[:4]
    r2 = x*x+y*y
    if kind == 5:
        theta = np.arctan(np.sqrt(r2))
        t2 = theta*theta
        theta_d = theta*(1+p[4]*t2+p[5]*t2**2+p[6]*t2**3+p[7]*t2**4)
        scale = np.divide(theta_d,np.sqrt(r2),out=np.ones_like(theta),where=r2>0)
        xx,yy = x*scale,y*scale
    else:
        k1 = p[3] if kind in (2,3) else p[4] if kind in (4,6) else 0.
        k2 = p[4] if kind == 3 else p[5] if kind in (4,6) else 0.
        radial = 1+k1*r2+k2*r2*r2
        if kind == 6:
            radial = (radial+p[8]*r2**3)/(1+p[9]*r2+p[10]*r2*r2+p[11]*r2**3)
        p1,p2 = p[6:8] if kind in (4,6) else (0.,0.)
        xx = x*radial+2*p1*x*y+p2*(r2+2*x*x)
        yy = y*radial+p1*(r2+2*y*y)+2*p2*x*y
    return np.column_stack((fx*xx+cx,fy*yy+cy))


@pytest.mark.parametrize("kind", list(PARAMS))
def test_projection_and_inverse_match_independent_camera_equations(kind):
    from photomesh.calibration import pack_calibrations, project_calibrations
    camera = cio.Camera(kind,600,450,np.array(PARAMS[kind]))
    xyz = np.array([[0.,0.,1.],[.2,-.15,1.],[-.65,.4,1.],[1.1,-.7,1.]])
    expected = independent_uv(kind,camera.params,xyz)
    params,models,*_ = pack_calibrations([camera])
    result = project_calibrations(np.repeat(params,len(xyz),axis=0),np.repeat(models,len(xyz)),xyz)
    assert np.allclose(result,expected,rtol=0,atol=1e-10)
    x,y = cio.undistort_points(camera,expected)
    assert np.allclose(np.column_stack((x,y)),xyz[:,:2],rtol=0,atol=1e-9)


@pytest.mark.parametrize("kind", list(PARAMS))
@pytest.mark.parametrize("fit", [False,True])
def test_bundle_preserves_exact_calibration_and_geometry(kind,fit):
    model = synthetic_model(n_img=4,n_pts=80,two_cameras=False)
    model.cameras[1] = cio.Camera(kind,600,450,np.array(PARAMS[kind]))
    for image in model.images.values():
        Xc = model.points.xyz[image.point3D_ids] @ image.R().T + image.tvec
        image.xys = independent_uv(kind,model.cameras[1].params,Xc)
    before = copy.deepcopy(model)
    result = g.gcp_bundle_adjust(model,{}, {},{"fit_intrinsics":fit,"max_iterations":4},log=lambda *_:None)
    assert model.cameras[1].model == kind
    assert np.allclose(model.cameras[1].params,before.cameras[1].params,rtol=0,atol=1e-8)
    for iid in model.images:
        assert np.allclose(model.images[iid].center(),before.images[iid].center(),rtol=0,atol=1e-8)
    errors,*_ = cio.observation_errors(model)
    assert result["tie_rms_px"] == pytest.approx(np.sqrt(np.mean(errors**2)),abs=1e-12)
    assert np.max(errors) < 1e-7


@pytest.mark.parametrize("key", ["tie_accuracy","projection_accuracy","huber"])
@pytest.mark.parametrize("value", [0.,-1.,float("nan")])
def test_invalid_weight_is_rejected_before_model_mutation(key,value):
    model = synthetic_model(n_img=3,n_pts=30,two_cameras=False)
    before = copy.deepcopy(model)
    with pytest.raises(ValueError,match="positive"):
        g.gcp_bundle_adjust(model,{}, {},{key:value},log=lambda *_:None)
    assert np.array_equal(model.points.xyz,before.points.xyz)


def test_coordinate_rmse_matches_independent_known_residuals():
    markers = [g.Marker("A",[1.,2.,3.]),g.Marker("B",[5.,6.,7.]),
               g.Marker("C",[0.,0.,0.],enabled=False)]
    rows = g.marker_errors(markers,lambda x:np.asarray(x),{
        "A":np.array([4.,6.,3.]),"B":np.array([5.,6.,19.]),"C":np.array([0.,8.,15.])})
    control = g.rmse(rows,"control"); check = g.rmse(rows,"check")
    assert control["total"] == pytest.approx(np.sqrt((25+144)/2))
    assert control["xy"] == pytest.approx(np.sqrt(25/2))
    assert check["total"] == pytest.approx(17.)


def test_marker_edit_refreshes_coordinate_pixel_errors_groups_and_undo(window,tmp_path):
    from test_markers_manual import _scene
    _scene(window,tmp_path)
    window.dataset.georef = {"offset":[0.,0.,0.],"crs":"LOCAL","rows":[]}
    label = window.add_marker_at_photo(500.,400.,k=0)
    prediction = window.dataset.markers[0]["projections"]["img_0002"]
    assert window.pin_marker(label,*prediction[:2],k=1)
    X = next(X for name,X,_ in window._marker_positions() if name == label)
    for col,value in enumerate(X,1):
        assert window.edit_marker_cell(label,col,str(value))
    original_ref = list(window.dataset.markers[0]["ref"])
    before = copy.deepcopy(window.dataset.georef["rows"][0])
    assert before["total"] < 1e-8
    assert window.pin_marker(label,510.,405.,k=0)
    changed = window.dataset.georef["rows"][0]
    assert changed["total"] > before["total"] + .001
    assert changed["pix"] > before["pix"] + .01
    assert window.dataset.markers[0]["ref"] == original_ref
    assert window.undo_markers()
    restored = window.dataset.georef["rows"][0]
    assert restored["total"] == pytest.approx(before["total"],abs=1e-8)
    assert window.redo_markers()
    window.toggle_marker(label,False)
    assert window.dataset.georef["control_rmse"] is None
    assert window.dataset.georef["check_rmse"]["n"] == 1
    window.marker_view_action("ignore",label)
    assert window.dataset.georef["rows"] == []
    assert window.dataset.georef["check_rmse"] is None


def test_marker_residual_does_not_hide_off_image_errors(monkeypatch):
    model=synthetic_model(n_img=4,n_pts=100,two_cameras=False)
    model.cameras[1]=cio.Camera(1,600,450,np.array([500.,500.,300.,225.]))
    X=np.array([400.,20.,1.])
    # Actual measurements remain inside their photos. The current estimate can
    # project outside one: that large residual must still count.
    projections={image.name:[300.,225.,True] for image in model.images.values()}
    monkeypatch.setattr(g,"triangulate_marker",lambda *args,**kwargs:(X,4))
    marker=g.Marker("outside",[400.,20.,1.],projections=projections)
    estimate,pixel,count=g.marker_observation_diagnostic(model,marker)
    expected=[]
    for image in model.images.values():
        uv=independent_uv(1,model.cameras[1].params,(image.R()@X+image.tvec)[None])
        expected.append(np.sum((uv[0]-[300.,225.])**2))
    assert np.allclose(estimate,X)
    assert count == 4 and pixel == pytest.approx(np.sqrt(np.mean(expected)))
    assert pixel > 1000.


def test_triangulation_rejects_behind_camera_intersection():
    model = synthetic_model(n_img=4,n_pts=100,two_cameras=False)
    X = np.array([10.,0.,100.])
    projections = {}
    for image in model.images.values():
        uv,_ = cio.project(model.cameras[image.camera_id],image.R(),image.tvec,X[None])
        projections[image.name] = uv[0].tolist()
    assert g.triangulate_marker(model,projections)[0] is None


def test_observation_aliases_are_not_double_weighted_or_arbitrarily_overwritten():
    model = synthetic_model(n_img=3,n_pts=50,two_cameras=False)
    photo = model.images[1].name
    stem = g._stem(photo)
    result = g.marker_image_observations(model,{photo:[10.,20.],stem:[10.,20.]})
    assert result == [(1,10.,20.)]
    with pytest.raises(ValueError,match="Conflicting"):
        g.marker_image_observations(model,{photo:[10.,20.,True],stem:[11.,20.,True]})
    assert g.marker_image_observations(model,{photo:[10.,20.,False],stem:[11.,20.,True]}) == [(1,11.,20.)]


def test_marker_keys_follow_model_aliases_for_same_named_photos():
    from photomesh.photonames import marker_camera_keys
    from photomesh.project import ProjectData,Camera
    dataset = ProjectData(cameras=[Camera("/a/photo.jpg",colmap_name="photo.jpg"),
                                  Camera("/b/photo.jpg",colmap_name="photo_1.jpg")])
    assert marker_camera_keys(dataset) == {0:"photo",1:"photo_1"}
    dataset.cameras[0].colmap_name = ""
    dataset.cameras[1].colmap_name = ""
    assert marker_camera_keys(dataset) == {}


@pytest.mark.parametrize("kind", list(PARAMS))
@pytest.mark.parametrize("fit", [False, True])
def test_noisy_bundle_reduces_independent_pixel_residuals(kind,fit):
    model = synthetic_model(n_img=5,n_pts=150,two_cameras=False)
    model.cameras[1] = cio.Camera(kind,600,450,np.array(PARAMS[kind]))
    rng = np.random.default_rng(104)
    for image in model.images.values():
        xyz = model.points.xyz[image.point3D_ids] @ image.R().T + image.tvec
        image.xys = independent_uv(kind,model.cameras[1].params,xyz) + rng.normal(0,.1,(len(xyz),2))
        image.tvec += rng.normal(0,.08,3)
    def rms():
        residuals = []
        for image in model.images.values():
            tracked = image.point3D_ids >= 0
            xyz = model.points.xyz[image.point3D_ids[tracked]] @ image.R().T + image.tvec
            residuals.extend(np.sum((independent_uv(kind,model.cameras[1].params,xyz)-image.xys[tracked])**2,axis=1))
        return np.sqrt(np.mean(residuals))
    before = rms()
    result = g.gcp_bundle_adjust(model,{}, {},{"fit_intrinsics":fit,"max_iterations":10},log=lambda *_:None)
    assert model.cameras[1].model == kind
    assert rms() < before*.5
    assert result["tie_rms_px"] == pytest.approx(rms(),abs=1e-10)


def test_predicted_placements_are_display_hints_until_measured(window,tmp_path):
    from test_markers_manual import _scene
    _scene(window,tmp_path)
    label = window.add_marker_at_photo(500.,400.,k=0)
    marker = g.Marker(**window.dataset.markers[0])
    model = window._sparse_model()
    assert g.triangulate_marker(model,marker.projections)[0] is not None
    assert g.triangulate_marker(model,marker.projections,measured_only=True)[0] is None
    assert g.marker_observation_diagnostic(model,marker) == (None,None,0)
    marker.ref = [100.,100.,0.]
    assert g.reference_status(model,[marker],g.CRS.parse("LOCAL"))["usable"] == 0
    prediction = marker.projections["img_0002"]
    window.pin_marker(label,*prediction[:2],k=1)
    marker = g.Marker(**window.dataset.markers[0])
    assert g.triangulate_marker(model,marker.projections,measured_only=True)[0] is not None
    window.project.save(window.project.path)
    from photomesh.project import Project
    saved = Project.load(window.project.path)
    assert saved.dataset.markers[0]["projections"] == window.dataset.markers[0]["projections"]


def test_two_marker_controls_still_constrain_bundle_when_gps_initializes_frame(tmp_path,monkeypatch):
    model = synthetic_model(n_img=5,n_pts=100,two_cameras=False)
    second = model.images[2]
    second.tvec = -second.R() @ np.array([8.,10.,50.])
    markers = []
    for k,X in enumerate(np.array([[10.,-4.,0.],[15.,4.,0.]])):
        projections = {}
        for image in model.images.values():
            uv,_ = cio.project(model.cameras[1],image.R(),image.tvec,X[None])
            projections[image.name] = [*uv[0],True]
        markers.append(g.Marker(str(k),(X+[400000.,4400000.,0.]).tolist(),projections=projections).to_dict())
    gps = {image.name:[44.+image.center()[0]*.0001,40.+image.center()[1]*.0001,100.] for image in model.images.values()}
    path = str(tmp_path/"model"); cio.write_model(path,model)
    class Captured(Exception): pass
    def capture(model,observations,control,*args,**kwargs):
        assert set(observations) == set(control) == {"0","1"}
        assert len(kwargs["cam_priors"]) == 5
        raise Captured()
    monkeypatch.setattr(g,"gcp_bundle_adjust",capture)
    with pytest.raises(Captured):
        g.run_task({"model":path,"crs":"EPSG:32638","markers":markers,
                    "use_markers":True,"use_cameras":True,"camera_gps":gps},log=lambda *_:None)


def test_invalid_unused_markers_do_not_enter_local_adjustment(tmp_path,monkeypatch):
    model = synthetic_model(n_img=3,n_pts=100,two_cameras=False)
    path = str(tmp_path/"model"); cio.write_model(path,model)
    marker = g.Marker("bad",projections={"img00":[float("nan"),0.],"img01":[0.,0.]}).to_dict()
    class Captured(Exception): pass
    def capture(model,observations,control,*args,**kwargs):
        assert observations == control == {}
        raise Captured()
    monkeypatch.setattr(g,"gcp_bundle_adjust",capture)
    with pytest.raises(Captured):
        g.run_task({"model":path,"local_only":True,"use_markers":False,"markers":[marker]},log=lambda *_:None)


def test_check_points_remain_independent_even_with_legacy_hidden_option(tmp_path,monkeypatch):
    model = synthetic_model(n_img=5,n_pts=100,two_cameras=False)
    markers = []
    for k,X in enumerate(np.array([[10.,-4.,0.],[15.,4.,0.],[20.,-4.,0.],[20.,4.,0.]])):
        projections = {}
        for image in model.images.values():
            uv,_ = cio.project(model.cameras[1],image.R(),image.tvec,X[None])
            projections[image.name] = [*uv[0],True]
        markers.append(g.Marker(str(k),(X+[1000.,2000.,0.]).tolist(),enabled=k<3,projections=projections).to_dict())
    path = str(tmp_path/"model"); cio.write_model(path,model)
    class Captured(Exception): pass
    def capture(model,observations,control,*args,**kwargs):
        assert set(observations) == set(control) == {"0","1","2"}
        raise Captured()
    monkeypatch.setattr(g,"gcp_bundle_adjust",capture)
    with pytest.raises(Captured):
        g.run_task({"model":path,"crs":"LOCAL","use_markers":True,"markers":markers,
                    "check_projections_in_ba":True},log=lambda *_:None)


def test_predicted_only_controls_cannot_initialize_georeferencing(tmp_path):
    model = synthetic_model(n_img=5,n_pts=100,two_cameras=False)
    markers=[]
    for k,X in enumerate(model.points.xyz[:3]):
        projections={}
        for image in model.images.values():
            uv,_=cio.project(model.cameras[1],image.R(),image.tvec,X[None])
            projections[image.name]=[*uv[0],False,"predicted"]
        markers.append(g.Marker(str(k),X.tolist(),projections=projections).to_dict())
    path=str(tmp_path/"model"); cio.write_model(path,model)
    before=(tmp_path/"model"/"images.bin").read_bytes()
    with pytest.raises(ValueError,match="Cannot georeference"):
        g.run_task({"model":path,"markers":markers,"use_markers":True},log=lambda *_:None)
    assert (tmp_path/"model"/"images.bin").read_bytes() == before


def test_gps_preselection_rejects_invalid_positions_and_handles_date_line():
    from photomesh.fastpipe import select_pairs
    names=["a.jpg","b.jpg","c.jpg","invalid.jpg","missing.jpg"]
    info=[{"lon":179.999,"lat":1.,"alt":10.},
          {"lon":-179.999,"lat":1.,"alt":10.},
          {"lon":179.99,"lat":1.,"alt":10.},
          {"lon":float("nan"),"lat":1.,"alt":10.},
          {"lat":1.}]
    result=select_pairs(names,info,k_gps=1,window=0,use_desc=False,use_gps=True)
    assert ("a.jpg","b.jpg") in result
    assert all("invalid.jpg" not in pair and "missing.jpg" not in pair for pair in result)
    assert select_pairs(names,info,window=0,use_desc=True,use_gps=False) == []


def test_realign_preserves_photo_identity_when_duplicate_names_are_removed_or_reordered(tmp_path):
    from photomesh.colmap import prepare_images
    from photomesh.photonames import assign_names
    from photomesh.project import ProjectData,Camera
    a=tmp_path/"a"; b=tmp_path/"b"; a.mkdir(); b.mkdir()
    (a/"photo.jpg").write_bytes(b"first"); (b/"photo.jpg").write_bytes(b"second")
    dataset=ProjectData(cameras=[Camera(str(a/"photo.jpg")),Camera(str(b/"photo.jpg"))])
    first=prepare_images(dataset,str(tmp_path/"work1")); assign_names(dataset,first)
    assert first[dataset.cameras[1].path] == "photo_1.jpg"
    dataset.cameras.reverse()
    second=prepare_images(dataset,str(tmp_path/"work2"))
    assert second == first
    dataset.cameras=dataset.cameras[:1]
    third=prepare_images(dataset,str(tmp_path/"work3"))
    assert third[dataset.cameras[0].path] == "photo_1.jpg"
    assert (tmp_path/"work3"/"images"/"photo_1.jpg").read_bytes() == b"second"


def test_similarity_transform_keeps_pose_projections_and_roundtrips_world_offsets():
    from scipy.spatial.transform import Rotation
    model=synthetic_model(n_img=5,n_pts=100,two_cameras=False)
    before=copy.deepcopy(model)
    R=Rotation.from_euler("xyz",[.2,-.1,.4]).as_matrix()
    scale=2.4; translation=np.array([400000.,4400000.,120.])
    g.transform_model(model,scale,R,translation)
    for iid,image in model.images.items():
        old=before.images[iid]
        assert np.allclose(image.center(),scale*R@old.center()+translation,atol=1e-8,rtol=0)
        uv,_=cio.project(model.cameras[image.camera_id],image.R(),image.tvec,model.points.xyz)
        expected,_=cio.project(before.cameras[old.camera_id],old.R(),old.tvec,before.points.xyz)
        assert np.allclose(uv,expected,atol=1e-6,rtol=0)


def test_robust_similarity_matches_final_inlier_mask():
    rng=np.random.default_rng(104)
    source=rng.normal(size=(30,3))
    target=2.3*source+[100.,200.,30.]
    target[:3]+=rng.normal(0,20,(3,3))
    scale,R,t,mask=g.robust_helmert(source,target,max_iter=1)
    ss,RR,tt=g.umeyama(source[mask],target[mask])
    assert scale == pytest.approx(ss)
    assert np.allclose(R,RR) and np.allclose(t,tt)
    with pytest.raises(ValueError,match="degenerate"):
        g.umeyama(np.ones((3,3)),np.ones((3,3)))


def test_legacy_unpinned_locations_need_photo_confirmation_or_refinement():
    model=synthetic_model(n_img=3,n_pts=50,two_cameras=False)
    locations={image.name:[300.,225.,False] for image in model.images.values()}
    assert g.marker_image_observations(model,locations,measured_only=True) == []
    assert len(g.marker_image_observations(model,locations)) == 3
    for value in locations.values(): value.append("refined")
    assert len(g.marker_image_observations(model,locations,measured_only=True)) == 3


def test_reference_xml_preserves_measurement_provenance_and_ignored_status(tmp_path):
    marker=g.Marker("A",enabled=False,disabled=True,locked=True,
                    projections={"one":[1.,2.,False,"predicted"],"two":[3.,4.,False,"refined"]})
    path=str(tmp_path/"markers.xml")
    g.write_markers_xml(path,[marker],"LOCAL")
    restored,_=g.read_markers_xml(path)
    assert restored[0].to_dict() == marker.to_dict()


def test_reference_text_report_keeps_current_pixel_error_and_actual_count(tmp_path):
    path=str(tmp_path/"report.txt")
    row={"label":"A","type":"check","ref":[1.,2.,3.],"est":[4.,6.,3.],
         "dx":3.,"dy":4.,"dz":0.,"total":5.,"pix":1.25,"n":3}
    g.write_report(path,[row],g.CRS.parse("LOCAL"))
    text=(tmp_path/"report.txt").read_text()
    assert "\t1.250\t3\n" in text


def test_mismatched_photo_and_model_pixels_are_rejected_before_adjustment(tmp_path):
    model=synthetic_model(n_img=3,n_pts=100,two_cameras=False)
    path=str(tmp_path/"model"); cio.write_model(path,model)
    before=(tmp_path/"model"/"cameras.bin").read_bytes()
    with pytest.raises(ValueError,match="original photo pixels"):
        g.run_task({"model":path,"local_only":True,
                    "photo_sizes":{"img00.jpg":[6000,4500]}},log=lambda *_:None)
    assert (tmp_path/"model"/"cameras.bin").read_bytes() == before


def test_model_context_menu_can_only_select_a_marker(window,tmp_path,monkeypatch):
    from test_markers_manual import _scene
    from PySide6 import QtWidgets
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QAction
    _scene(window,tmp_path)
    label=window.add_marker_at_photo(500.,400.,k=0)
    before=copy.deepcopy(window.dataset.markers); history=len(window._mk_undo)
    view=window.model_view
    monkeypatch.setattr(view,"marker_at",lambda *args:label)
    actions=[]
    class Menu:
        def __init__(self,parent): self.parent,self.items=parent,[]
        def addAction(self,text):
            action=QAction(text,self.parent); self.items.append(action); return action
        def exec(self,*args):
            actions.extend(action.text() for action in self.items)
            self.items[0].trigger()
    monkeypatch.setattr(QtWidgets,"QMenu",Menu)
    view._context(QPoint(10,10))
    assert actions == ["Select Marker: "+label]
    assert window.markers_pane.current_label() == label
    assert window.dataset.markers == before and len(window._mk_undo) == history


def test_reference_edit_uses_persisted_geographic_frame_if_project_crs_is_legacy_empty(window,tmp_path):
    from test_markers_manual import _scene
    _scene(window,tmp_path)
    window.dataset.crs=""
    window.dataset.georef={"crs":"EPSG:4326","offset":[400000.,4400000.,0.]}
    label=window.add_marker_at_photo(500.,400.,k=0)
    assert not window.edit_marker_cell(label,1,"1000")
    assert window.dataset.markers[0]["ref"] is None


@pytest.mark.parametrize("uv",[(-1.,400.),(1000.,400.),(500.,800.),(float("nan"),400.)])
def test_photo_margin_clicks_cannot_create_or_move_measurements(window,tmp_path,uv):
    from test_markers_manual import _scene
    _scene(window,tmp_path)
    label=window.add_marker_at_photo(500.,400.,k=0)
    before=copy.deepcopy(window.dataset.markers); history=len(window._mk_undo)
    assert window.add_marker_at_photo(*uv,k=0) is None
    assert not window.pin_marker(label,*uv,k=0)
    assert window.dataset.markers == before and len(window._mk_undo) == history


def test_imported_outside_photo_observation_cannot_enter_adjustment():
    model=synthetic_model(n_img=3,n_pts=50,two_cameras=False)
    with pytest.raises(ValueError,match="outside source photo"):
        g.triangulate_marker(model,{"img00":[-1.,225.,True],"img01":[300.,225.,True]},measured_only=True)


def test_geographic_boundaries_use_valid_utm_zone_and_reject_unsupported_latitudes():
    assert g.utm_zone(180.,0.) == 60
    assert g.utm_zone(-180.,0.) == 1
    assert g.geographic_zone([[180.,1.,0.]])[0] == 60
    assert g.geographic_zone([[180.,1.,0.],[-179.999,1.,0.]])[0] in (1,60)
    metric=g.CRS.parse("EPSG:4326").to_metric([[180.,1.,0.],[-179.999,1.,0.]])
    assert np.linalg.norm(metric[1]-metric[0]) == pytest.approx(111.3,abs=1.)
    for latitude in (-81.,85.):
        with pytest.raises(ValueError,match="latitude"):
            g.CRS.parse("EPSG:4326").to_metric([[44.,latitude,100.]])
    with pytest.raises(ValueError,match="zone"):
        g.CRS.parse("WGS 84 / UTM zone 61N")


def test_invalid_reference_errors_are_unavailable_without_hiding_valid_markers():
    markers=[g.Marker("bad",[float("nan"),2.,3.]),g.Marker("good",[1.,2.,3.])]
    rows=g.marker_errors(markers,lambda ref:g.CRS.parse("LOCAL").to_metric([ref])[0],
                         {"bad":np.array([1.,2.,3.]),"good":np.array([4.,6.,3.])})
    assert len(rows) == 1 and rows[0]["label"] == "good" and rows[0]["total"] == 5.
