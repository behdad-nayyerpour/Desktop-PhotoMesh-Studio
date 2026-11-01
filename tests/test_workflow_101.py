"""1.0.1 integrated regression tests: user scope, numeric behaviour and rollback."""
import json, os
import numpy as np
import pytest
from photomesh import workflow as w


def test_product_publication_rolls_back_and_remaps(tmp_path):
    target=tmp_path/"product"; target.mkdir(); (target/"old").write_text("healthy")
    @w.product_transaction
    def failing(cfg):
        open(os.path.join(cfg["out_dir"],"new"),"w").write("partial")
        raise ValueError("stopped")
    with pytest.raises(ValueError): failing({"out_dir":str(target)})
    assert (target/"old").read_text()=="healthy"
    @w.product_transaction
    def successful(cfg):
        result={"dir":cfg["out_dir"],"files":[os.path.join(cfg["out_dir"],"new")]}
        open(result["files"][0],"w").write("complete")
        with open(os.path.join(cfg["out_dir"],"info.json"),"w") as fh: json.dump(result,fh)
        return result
    result=successful({"out_dir":str(target)})
    assert result["dir"]==str(target) and result["files"]==[str(target/"new")]
    assert json.loads((target/"info.json").read_text())["dir"]==str(target)
    assert not (target/"old").exists()


def test_region_never_silently_becomes_full_extent(qtbot):
    from photomesh.dialogs import _RegionBox
    box=_RegionBox([10,10,5,5]); qtbot.addWidget(box); box.setChecked(True)
    with pytest.raises(ValueError,match="maximum"): box.region()


def test_mesh_count_visible_and_effective_controls(window):
    from photomesh.dialogs import BuildModelDialog
    window.chunk.point_count=15_000_000
    dialog=BuildModelDialog(window)
    assert dialog.custom.value()==1_000_000 and not dialog.custom.isEnabled()
    dialog.face_count.setCurrentText("High")
    assert dialog.custom.value()==3_000_000
    dialog.source.setCurrentIndex(1)
    assert not dialog.voxel.isEnabled() and not dialog.interp.isEnabled()
    assert not dialog.max_pts.isEnabled()


def test_texture_size_and_keep_count_validation(window):
    from photomesh.dialogs import BuildTextureDialog
    d=BuildTextureDialog(window)
    d.size.setCurrentText("oops")
    with pytest.raises(ValueError): d.validate_settings()
    d.size.setCurrentText("40000")
    with pytest.raises(ValueError): d.validate_settings()


def test_point_tiles_controls_have_no_hidden_multiplier(window):
    from photomesh.dialogs import BuildTiledModelDialog
    d=BuildTiledModelDialog(window,("Model","Point cloud"))
    d.source.setCurrentText("Point cloud"); d.tile_faces.setValue(12345)
    result=d.settings()
    assert result["tile_points"]==12345 and result["format"]=="pnts"
    assert not d.pixel.isEnabled() and not d.max_tex.isEnabled()


def test_isolation_and_terrain_defaults(window):
    from photomesh.dialogs import BuildPointCloudDialog
    d=BuildPointCloudDialog(window)
    assert not d.elev.isChecked()
    assert d.settings()["filters"]["local_ratio"]==3


def test_alignment_has_four_resolutions_and_explicit_default(window):
    from photomesh.dialogs import AlignPhotosDialog
    d=AlignPhotosDialog(window)
    assert d.accuracy.count()==4 and d.key_limit.value()==24000
    assert not d.reference.isEnabled()
    assert "One stage" in d.summary.text()
    assert "Engine default" in d.key_limit.specialValueText()


def test_ortho_only_effective_controls_active(window):
    from photomesh.dialogs import BuildOrthomosaicDialog
    d=BuildOrthomosaicDialog(window)
    assert d.pixel.isEnabled() and not d.maxdim.isEnabled()
    d.r_max.setChecked(True)
    assert d.maxdim.isEnabled() and not d.pixel.isEnabled()
    d.blending.setCurrentText("Average")
    assert not d.seams.isEnabled()
    d.res.setCurrentIndex(1)
    assert d.settings()["photo_scale"]==.5


def test_degenerate_tiles_obey_count_limit():
    from photomesh.tiles import quadtree,walk
    tree=quadtree(np.zeros((101,2)),7,1)
    assert all(len(node.items)<=7 for node in walk(tree) if not node.children)


def test_tile_fallback_cannot_exceed_texture_limit():
    from photomesh.tiles import face_grid_atlas
    with pytest.raises(ValueError,match="capacity"):
        face_grid_atlas(np.zeros((1000,3,2)),32,.1)


def test_global_transform_places_the_center_once():
    from photomesh.tiles import _root_transform
    from photomesh.georef import utm_inverse,geodetic_to_ecef
    center=np.array([100.,200.,30.])
    g={"crs_kind":"utm","zone":[38,False],"offset":[500000,4400000,1000]}
    transform,location=_root_transform(g,center)
    M=np.array(transform).reshape(4,4).T
    actual=(M@np.r_[center,1])[:3]
    expected=geodetic_to_ecef(*location)
    assert np.allclose(actual,expected,atol=1e-6)


def test_registration_preserves_calibration_and_recovers_known_pose():
    from photomesh.registration import solve_pose,validate_controls
    from photomesh.colmap_io import Camera,Image,project,rot_to_qvec
    from scipy.spatial.transform import Rotation
    cam=Camera(1,1000,800,np.array([800.,800.,500.,400.]))
    X=np.array([[-3,-2,0],[3,-2,.4],[3,2,0],[-3,2,.2],[0,0,1],[-2,1,.7],[2,-1,.3]])
    R=np.diag([1.,-1.,-1.]); C=np.array([.5,.3,10.]); t=-R@C
    xy,z=project(cam,R,t,X)
    initial=Image("old.jpg",1,rot_to_qvec(R),-R@np.array([0.,0.,11.]),
                  np.empty((0,2)),np.empty(0,dtype=np.int64))
    recovered,translation,error=solve_pose(cam,X,xy,[initial])
    assert error<1e-4 and np.allclose(-recovered.T@translation,C,atol=1e-4)
    with pytest.raises(ValueError,match="6 measured"):
        validate_controls(X[:3],xy[:3],1000,800)
    with pytest.raises(ValueError,match="collinear"):
        validate_controls(np.column_stack([np.arange(6),np.zeros((6,2))]),np.column_stack(
            [np.arange(6)*100,np.arange(6)*50]),1000,800)


def test_mesh_dem_uses_triangle_interior(tmp_path):
    from photomesh.plyio import save_ply
    from photomesh.ortho import build_dem
    from photomesh.geotiff import TiffReader
    V=np.array([[0,0,0],[10,0,10],[0,10,20],[10,10,30]],float)
    F=np.array([[0,1,2],[1,3,2]])
    path=tmp_path/"plane.ply"; save_ply(str(path),V,None,F)
    result=build_dem({"source":"Mesh","mesh":str(path),"out_dir":str(tmp_path/"dem"),
                      "pixel_size":1.,"interpolation":"Disabled"},log=lambda *_:None)
    with TiffReader(result["path"]) as r: grid=r.read_level(0)[...,0]
    # Exact sloping triangle at pixel centres; sparse vertices alone cannot supply these cells.
    assert grid[4,4]==pytest.approx(4.5+2*5.5,abs=1e-4)
    assert result["measured_cells"]>=90 and result["filled_cells"]==0
    assert os.path.exists(result["coverage_path"])


def test_confidence_cannot_silently_skip_missing_counts():
    from photomesh.pcfilter import filter_cloud
    with pytest.raises(ValueError,match="unavailable"):
        filter_cloud({"xyz":np.zeros((10,3))},{"min_confidence":3})


def test_added_photo_registration_keeps_old_poses_and_updates_shapes(window,tmp_path,monkeypatch):
    from PIL import Image as PILImage
    from photomesh.project import Project,Camera as Photo
    from photomesh import colmap_io as cio
    project=Project(); project.path=str(tmp_path/"registered.pmsx"); ch=project.chunk
    R=np.diag([1.,-1.,-1.]); cam=cio.Camera(1,1000,800,np.array([800.,800.,500.,400.]))
    xyz=np.array([[-3,-2,0],[3,-2,.4],[3,2,0],[-3,2,.2],[0,0,1],[-2,1,.7],[2,-1,.3]])
    poses={}
    for index,center in enumerate(([-1.,0.,10.],[1.,0.,10.],[.5,.3,10.])):
        path=tmp_path/f"photo{index}.jpg"; PILImage.new("RGB",(1000,800),(100,150,200)).save(path)
        aligned=index<2
        ch.cameras.append(Photo(str(path),aligned=aligned,width=1000,height=800,
            colmap_name=path.name if aligned else "",est=center if aligned else None,
            rot=R.tolist() if aligned else None))
        if aligned: poses[index+1]=cio.Image(path.name,1,cio.rot_to_qvec(R),-R@center,
                                            np.empty((0,2)),np.empty(0,dtype=np.int64))
    points=cio.Points(np.empty(0,np.uint64),np.empty((0,3)),np.empty((0,3),np.uint8),np.empty(0),
                     np.zeros(1,np.int64),np.empty(0,np.uint32),np.empty(0,np.uint32))
    wd=project.default_workdir(ch); model=os.path.join(wd,"sparse","0")
    cio.write_model(model,cio.Model({1:cam},poses,points))
    original={name:open(os.path.join(model,name),"rb").read() for name in ("cameras.bin","images.bin","points3D.bin")}
    pixels,_=cio.project(cam,R,-R@np.array([.5,.3,10.]),xyz)
    ch.markers=[{"label":f"G{i}","enabled":True,"projections":{"photo2":[*xy.tolist(),True]}}
                for i,xy in enumerate(pixels)]
    project.save(project.path)
    window.project=project; window.refresh_all()
    monkeypatch.setattr(window,"_marker_positions",lambda:[(f"G{i}",point,True) for i,point in enumerate(xyz)])
    refreshed=[]
    monkeypatch.setattr(window,"_update_photo_shapes",lambda:refreshed.append(window.current_photo))
    window.register_selected_photos([2])
    assert ch.cameras[2].aligned and np.allclose(ch.cameras[2].est,[.5,.3,10.],atol=1e-3)
    assert ch.cameras[0].est==[-1.,0.,10.] and ch.cameras[1].est==[1.,0.,10.]
    assert all(open(os.path.join(model,name),"rb").read()==data for name,data in original.items())
    assert refreshed and refreshed[-1]==2
    published=cio.read_model(window._model_dir())
    assert len(published.images)==3 and ch.cameras[2].colmap_name=="photo2.jpg"


def test_realign_preserves_georeferenced_frame(tmp_path):
    from photomesh import colmap_io as cio
    from photomesh.registration import preserve_frame
    from photomesh.georef import transform_model
    from tests.test_dense_mesh_gcp import synthetic_model
    original=synthetic_model(); changed=synthetic_model()
    from scipy.spatial.transform import Rotation
    transform_model(changed,2.5,Rotation.from_euler("xyz",[.2,-.1,.5]).as_matrix(),np.array([100.,200.,30.]))
    path=str(tmp_path/"model"); cio.write_model(path,changed)
    known={im.name:{"center":im.center().tolist(),"rotation":im.R().tolist()} for im in original.images.values()}
    preserve_frame({"model":path,"cameras":known},log=lambda *_:None)
    restored=cio.read_model(path)
    assert np.allclose(restored.points.xyz,original.points.xyz,atol=1e-6)
    for key,im in original.images.items():
        assert np.allclose(restored.images[key].center(),im.center(),atol=1e-6)
        assert np.allclose(restored.images[key].R(),im.R(),atol=1e-6)


def test_changed_photo_invalidates_undistortion_and_changed_depth_setting_only_depth(tmp_path):
    from photomesh.dense import workspace_reuse
    marker=tmp_path/"workspace.json"
    cfg={"model":"model","image_root":"photos","dense":"dense","quality":"Medium","max_sources":8,
         "camera_stamp":[1,2],"photo_stamps":[["a",1]],"depth_parameters":{"num_iterations":3}}
    marker.write_text(json.dumps(cfg))
    assert workspace_reuse(str(marker),cfg,True)==(True,True)
    changed=dict(cfg,photo_stamps=[["a",2]])
    assert workspace_reuse(str(marker),changed,True)==(False,False)
    changed=dict(cfg,depth_parameters={"num_iterations":4})
    assert workspace_reuse(str(marker),changed,True)==(True,False)


def test_metric_raster_crs_does_not_label_eastings_as_longitude():
    from photomesh.workflow import processing_crs
    assert processing_crs({"crs":"EPSG:4326","crs_kind":"wgs84","zone":[38,False]})=="EPSG:32638"
    assert processing_crs({"crs":"EPSG:4326","zone":[38,True]})=="EPSG:32738"
    assert processing_crs({})==""
    with pytest.raises(ValueError,match="zone"): processing_crs({"crs":"EPSG:4326"})
