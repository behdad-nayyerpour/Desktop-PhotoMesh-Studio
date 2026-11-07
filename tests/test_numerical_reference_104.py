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


def test_marker_residual_does_not_hide_off_image_errors():
    model = synthetic_model(n_img=4,n_pts=100,two_cameras=False)
    # Pinhole remains invertible beyond the image; radial models can fold there.
    model.cameras[1] = cio.Camera(1,600,450,np.array([500.,500.,300.,225.]))
    X = np.array([400.,20.,1.])
    projections = {}
    for image in model.images.values():
        uv,_ = cio.project(model.cameras[image.camera_id],image.R(),image.tvec,X[None])
        projections[image.name] = [float(uv[0,0]),float(uv[0,1])]
    marker = g.Marker("outside",[400.,20.,1.],projections=projections)
    estimate,pixel,count = g.marker_observation_diagnostic(model,marker)
    assert np.allclose(estimate,X,atol=1e-6)
    assert pixel < 1e-6 and count == 4


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
    for k,X in enumerate(model.points.xyz[:2]):
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
    for k,X in enumerate(model.points.xyz[:4]):
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
