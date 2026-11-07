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
