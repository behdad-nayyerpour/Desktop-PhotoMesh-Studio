"""Numerical and isolation regressions for offline engine modernization."""
import json
import os
import sqlite3
import struct
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from photomesh import engine


@pytest.fixture(autouse=True)
def clear_probes(monkeypatch):
    monkeypatch.setattr(engine, "_GPU", None)
    engine._PROBES.clear()
    engine._PREFLIGHT.clear()
    engine._MODEL_STAMPS.clear()


def test_child_environment_does_not_change_host(tmp_path,monkeypatch):
    exe=tmp_path/"engine"/"bin"/"colmap.exe"; exe.parent.mkdir(parents=True)
    (exe.parent.parent/"plugins").mkdir()
    monkeypatch.setenv("QT_PLUGIN_PATH","host-pyside")
    monkeypatch.setenv("PATH","host-path")
    result=engine.child_env(str(exe))
    assert os.environ["QT_PLUGIN_PATH"]=="host-pyside" and os.environ["PATH"]=="host-path"
    assert result["QT_PLUGIN_PATH"]==str(exe.parent.parent/"plugins")
    assert result["PATH"].startswith(str(exe.parent))


@pytest.mark.parametrize("driver,cc,memory,expected",[(13020,75,4*1024**3,True),
    (12000,89,8*1024**3,False),(13020,61,8*1024**3,False),(13020,89,512*1024**2,False)])
def test_bundle_hardware_gate(monkeypatch,driver,cc,memory,expected):
    monkeypatch.setattr(engine,"run_help",lambda *_:"COLMAP 4.2.1 with CUDA")
    monkeypatch.setattr(engine,"bundle_manifest",lambda *_:{"cuda":True,"minimum_driver":13020,"minimum_cc":75})
    monkeypatch.setattr(engine,"hardware",lambda:{"driver":driver,"devices":[{"index":0,"cc":cc,"memory":memory,"name":"test"}]})
    assert bool(engine.gpu_device("engine"))==expected


def test_no_gpu_preference_is_honored(monkeypatch):
    monkeypatch.setattr(engine,"hardware",lambda:pytest.fail("GPU must not be probed when disabled"))
    assert engine.gpu_device("engine",False) is None


def test_failed_native_probe_is_not_cached_as_gpu(monkeypatch,tmp_path):
    from photomesh import colmap
    monkeypatch.setattr(engine,"gpu_device",lambda *_:{"index":0,"memory":4*1024**3,"name":"GPU"})
    monkeypatch.setattr(engine,"matching_arguments",lambda *a,**k:[])
    monkeypatch.setattr(colmap,"opt",lambda *a,**k:[])
    calls=[]
    def run(command,**kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1 if len(calls)==1 else 0,stdout="",stderr="GPU rejected")
    monkeypatch.setattr(engine.subprocess,"run",run)
    first=engine.execution_settings("engine",{"use_gpu":True},str(tmp_path),lambda *_:None)
    second=engine.execution_settings("engine",{"use_gpu":True},str(tmp_path),lambda *_:None)
    assert not first["use_gpu"] and not second["use_gpu"]
    assert len(calls)==3


def test_missing_offline_weights_never_download(tmp_path):
    with pytest.raises(ValueError,match="Offline model missing"):
        engine.verified_model(str(tmp_path/"bin"/"colmap.exe"),"aliked-n16rot.onnx")


def test_model_hash_and_changed_file_revalidated(tmp_path,monkeypatch):
    import hashlib
    root=tmp_path/"engine"; path=root/"models"/"model.onnx"; path.parent.mkdir(parents=True)
    path.write_bytes(b"model")
    expected=hashlib.sha256(b"model").hexdigest()
    monkeypatch.setattr(engine,"bundle_manifest",lambda *_:{"models":{"model.onnx":expected}})
    assert engine.verified_model(str(root/"bin"/"colmap.exe"),"model.onnx")==str(path)
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError,match="checksum mismatch"):
        engine.verified_model(str(root/"bin"/"colmap.exe"),"model.onnx")


def test_integrated_global_does_not_assume_cuda_means_ceres_cuda(monkeypatch):
    from photomesh import colmap
    options={"GlobalMapper.gp_use_gpu","GlobalMapper.ba_ceres_use_gpu"}
    monkeypatch.setattr(colmap,"colmap_options",lambda *_:options)
    monkeypatch.setattr(engine,"has_global",lambda *_:True)
    monkeypatch.setattr(engine,"gpu_device",lambda *_:{"memory":8*1024**3})
    monkeypatch.setattr(engine,"bundle_manifest",lambda *_:{"cuda":True,"ceres_cuda":False})
    args=engine.global_arguments("engine",{"use_gpu":True},"db","photos","out")
    assert args[0]=="global_mapper"
    assert args[args.index("--GlobalMapper.gp_use_gpu")+1]=="0"
    assert args[args.index("--GlobalMapper.ba_ceres_use_gpu")+1]=="0"


def test_neural_feature_and_matcher_types_are_consistent(monkeypatch):
    from photomesh import colmap
    options={"FeatureExtraction.type","FeatureExtraction.use_gpu","FeatureMatching.type",
             "FeatureMatching.use_gpu","AlikedExtraction.n16rot_model_path",
             "AlikedExtraction.max_num_features","AlikedMatching.lightglue_model_path"}
    monkeypatch.setattr(colmap,"colmap_options",lambda *_:options)
    monkeypatch.setattr(engine,"gpu_device",lambda *_:None)
    monkeypatch.setattr(engine,"verified_model",lambda exe,name:"/offline/"+name)
    cfg={"feature_method":"ALIKED + LightGlue","key_point_limit":2048,"use_gpu":False}
    extract=engine.matching_arguments("engine","feature_extractor",cfg,True)
    match=engine.matching_arguments("engine","matches_importer",cfg)
    assert "ALIKED_N16ROT" in extract and "ALIKED_LIGHTGLUE" in match
    assert not any("http" in value for value in extract+match)


def test_neural_rejects_implicit_or_unbounded_feature_count(monkeypatch):
    from photomesh import colmap
    monkeypatch.setattr(colmap,"colmap_options",lambda *_:set())
    monkeypatch.setattr(engine,"gpu_device",lambda *_:None)
    for count in (0,100000):
        with pytest.raises(ValueError,match="explicit feature limit"):
            engine.matching_arguments("engine","matches_importer",{"feature_method":"ALIKED + LightGlue","key_point_limit":count})


def test_frame_binary_poses_follow_model_rewrite(tmp_path):
    from tests.test_dense_mesh_gcp import synthetic_model
    from photomesh import colmap_io as cio
    from photomesh.georef import transform_model
    model=synthetic_model()
    transform_model(model,2.,np.eye(3),np.array([100.,200.,30.]))
    cio.write_model(str(tmp_path),model)
    data=(tmp_path/"frames.bin").read_bytes()
    assert struct.unpack_from("<Q",data)[0]==len(model.images)
    offset=8
    for iid in sorted(model.images):
        frame,rig,*rest=struct.unpack_from("<II7dI",data,offset); offset+=68
        kind,camera,photo=struct.unpack_from("<iIQ",data,offset); offset+=16
        im=model.images[iid]
        assert frame==photo==iid and rig==camera==im.camera_id and kind==0 and rest[-1]==1
        assert np.allclose(rest[:7],np.r_[im.qvec,im.tvec])


def test_database_calibration_merge_updates_modern_frames(tmp_path):
    from photomesh.fastpipe import merge_identical_cameras
    db=str(tmp_path/"database.db")
    with sqlite3.connect(db) as con:
        con.executescript("""
        CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY,model INTEGER,width INTEGER,height INTEGER,params BLOB,prior_focal_length INTEGER);
        CREATE TABLE images(image_id INTEGER PRIMARY KEY,name TEXT,camera_id INTEGER);
        CREATE TABLE rigs(rig_id INTEGER PRIMARY KEY,ref_sensor_id INTEGER,ref_sensor_type INTEGER);
        CREATE TABLE rig_sensors(rig_id INTEGER,sensor_id INTEGER,sensor_type INTEGER,sensor_from_rig BLOB);
        CREATE TABLE frames(frame_id INTEGER PRIMARY KEY,rig_id INTEGER);
        CREATE TABLE frame_data(frame_id INTEGER,data_id INTEGER,sensor_id INTEGER,sensor_type INTEGER);
        CREATE TABLE pose_priors(pose_prior_id INTEGER PRIMARY KEY,corr_data_id INTEGER,corr_sensor_id INTEGER,corr_sensor_type INTEGER);
        """)
        for cid in (1,2):
            con.execute("INSERT INTO cameras VALUES(?,?,?,?,?,?)",(cid,2,1000,800,np.array([800.,500.,400.,0.]).tobytes(),1))
            con.execute("INSERT INTO images VALUES(?,?,?)",(cid,str(cid)+".jpg",cid))
            con.execute("INSERT INTO pose_priors VALUES(?,?,?,0)",(cid,cid,cid))
    merge_identical_cameras(db)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM rigs").fetchone()[0]==1
        assert con.execute("SELECT COUNT(*) FROM frames").fetchone()[0]==2
        assert con.execute("SELECT COUNT(DISTINCT sensor_id) FROM frame_data").fetchone()[0]==1
        assert con.execute("SELECT COUNT(DISTINCT corr_sensor_id) FROM pose_priors").fetchone()[0]==1
        assert not list(con.execute("PRAGMA foreign_key_check"))


def test_alignment_dialog_explains_gps_and_has_explicit_neural_limit(window):
    from photomesh.dialogs import AlignPhotosDialog
    d=AlignPhotosDialog(window)
    assert not d.gps_frame.isEnabled()
    d.feature_method.setCurrentText("ALIKED + LightGlue")
    assert d.key_limit.value()==2048 and d.key_limit.maximum()==4096 and not d.c2f.isEnabled()


def test_gps_requires_a_spread_footprint():
    from photomesh.project import Camera
    def cameras(coords):
        return [Camera(str(i)+".jpg",lon=lon,lat=lat,alt=100.,use_reference=True)
                for i,(lon,lat) in enumerate(coords)]
    line=cameras([(44.,40.),(44.,40.001),(44.,40.002)])
    assert not engine.gps_frame_available(line)[0]
    block=cameras([(44.,40.),(44.001,40.),(44.,40.001)])
    assert engine.gps_frame_available(block)[0]
    assert not engine.gps_frame_available(block,existing_alignment=True)[0]
    block[0].use_reference=False
    assert not engine.gps_frame_available(block)[0]


def test_publication_failure_restores_model_and_cloud(tmp_path,monkeypatch):
    from photomesh.workflow import publish_outputs
    model=tmp_path/"model"; model.mkdir(); (model/"pose").write_text("old")
    stage=tmp_path/"model-stage"; stage.mkdir(); (stage/"pose").write_text("new")
    cloud=tmp_path/"cloud.ply"; cloud.write_text("old-cloud")
    staged_cloud=tmp_path/"cloud-stage.ply"; staged_cloud.write_text("new-cloud")
    real=os.replace
    def replace(source,destination):
        if source==str(staged_cloud): raise PermissionError("injected publication failure")
        return real(source,destination)
    monkeypatch.setattr(os,"replace",replace)
    with pytest.raises(PermissionError):
        publish_outputs([(str(stage),str(model)),(str(staged_cloud),str(cloud))])
    assert (model/"pose").read_text()=="old" and cloud.read_text()=="old-cloud"


def test_gps_similarity_and_modern_frame_publication_are_consistent(tmp_path):
    from tests.test_dense_mesh_gcp import synthetic_model
    from photomesh import colmap_io as cio,georef as g
    model=synthetic_model(n_img=8,two_cameras=False)
    for i,image in enumerate(model.images.values()):
        center=image.center(); center[1]=(i%2)*15.
        image.tvec=-image.R()@center
        image.xys=cio.project(model.cameras[image.camera_id],image.R(),image.tvec,
                             model.points.xyz[np.maximum(image.point3D_ids,0)])[0]
    points=model.points.xyz.copy()
    original={im.name:im.center().copy() for im in model.images.values()}
    angle=.3
    R=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1.]])
    scale=2.5; translation=np.array([500000.,4400000.,1000.])
    world={name:scale*R@center+translation for name,center in original.items()}
    gps={}
    for name,value in world.items():
        lat,lon=g.utm_inverse(value[0],value[1],38,False)
        gps[name]=[float(lon),float(lat),value[2]]
    folder=tmp_path/"model"; cio.write_model(str(folder),model)
    result=g.run_task({"model":str(folder),"markers":[],"crs":"EPSG:32638","camera_gps":gps,
                       "use_markers":False,"use_cameras":True,"bundle":False},log=lambda *_:None)
    actual=cio.read_model(str(folder)); offset=np.asarray(result["offset"])
    for image in actual.images.values():
        np.testing.assert_allclose(image.center()+offset,world[image.name],atol=1e-4)
    np.testing.assert_allclose(actual.points.xyz+offset,points@R.T*scale+translation,atol=1e-4)
    assert (folder/"frames.bin").is_file() and (folder/"rigs.bin").is_file()


def test_safe_builder_rejects_traversal(tmp_path):
    import zipfile
    from tools.prepare_engine import safe_extract
    archive=tmp_path/"bad.zip"
    with zipfile.ZipFile(archive,"w") as output: output.writestr("../escape","bad")
    with pytest.raises(ValueError,match="Unsafe"):
        safe_extract(archive,tmp_path/"stage")
    assert not (tmp_path/"escape").exists()


def test_validation_rejects_broken_track_links(tmp_path):
    from tests.test_dense_mesh_gcp import synthetic_model
    from photomesh import colmap_io as cio
    model=synthetic_model()
    model.points.track_img[0]=999999
    cio.write_model(str(tmp_path),model)
    with pytest.raises(ValueError,match="missing image"):
        engine.validate_model(str(tmp_path))


def test_geographic_zone_handles_dateline_and_rejects_invalid_regions():
    from photomesh.georef import geographic_zone,valid_gps
    zone,south=geographic_zone([[179.99,10,100],[-179.99,10.001,100],[179.98,10.002,100]])
    assert zone in (1,60) and not south
    assert valid_gps([float("nan"),40,100]) is None
    assert valid_gps([44,89,100]) is None
    with pytest.raises(ValueError,match="projection regions"):
        geographic_zone([[0,40,100],[44,40,100],[45,40,100]])


def test_delaunay_does_not_require_gpu_for_existing_fusion(window,tmp_path,monkeypatch):
    from photomesh import dialogs,mesh_steps
    from photomesh.project import Camera
    window.project.path=str(tmp_path/"project.pmsx")
    window.chunk.cameras=[Camera(str(tmp_path/"a.jpg"),aligned=True,est=[0,0,10])]
    monkeypatch.setattr(window,"_need_colmap",lambda:"engine")
    monkeypatch.setattr(window,"_cuda_available",lambda *_:pytest.fail("Delaunay meshing is a CPU task"))
    monkeypatch.setattr(dialogs.BuildModelDialog,"exec",lambda *_:1)
    original=dialogs.BuildModelDialog.settings
    monkeypatch.setattr(dialogs.BuildModelDialog,"settings",lambda d:dict(original(d),source="Depth maps"))
    monkeypatch.setattr(mesh_steps,"mesh_steps",lambda *a,**k:([("mesh",["delaunay_mesher"],1)],str(tmp_path/"model.ply")))
    calls=[]
    monkeypatch.setattr(window,"_run",lambda *a,**k:calls.append(a))
    window.build_model()
    assert calls and calls[0][0]=="Build Model"


def test_startup_locator_does_not_run_native_capability_probe(tmp_path,monkeypatch):
    from photomesh import colmap
    exe=tmp_path/"bin"/"colmap.exe"; exe.parent.mkdir(); exe.write_bytes(b"fixture"); exe.chmod(0o755)
    monkeypatch.setattr(colmap,"_bundled_candidates",lambda:iter([str(exe)]))
    monkeypatch.setattr(engine,"select_bundled",lambda *_:pytest.fail("Startup must not probe a native executable"))
    assert colmap.locate_colmap()==str(exe)


def test_coarse_pose_reuse_requires_focal_priors(tmp_path,monkeypatch):
    from photomesh import fastpipe as fp,colmap
    monkeypatch.setattr(colmap,"colmap_options",lambda *_:set())
    settings={"accuracy":"High","key_point_limit":2048,"use_gpu":False,
              "coarse_to_fine":True,"decode_cache":False,"mapper":"Incremental"}
    steps=fp.fast_align_steps("missing-engine",str(tmp_path),["a.jpg","b.jpg"],
                              [{"width":4000,"height":3000}]*2,settings)
    with sqlite3.connect(str(tmp_path/"coarse.db")) as database:
        database.execute("CREATE TABLE cameras(camera_id INTEGER,prior_focal_length INTEGER)")
        database.execute("INSERT INTO cameras VALUES(1,0)")
    check=next(action for label,action,_ in steps if label=="Checking coarse calibration")
    assert "disabled" in check()[0][1]
    fine=next(action for label,action,_ in steps if label=="Planning fine matching")
    (tmp_path/"pairs.txt").write_text("a.jpg b.jpg\n")
    selected=fine()
    assert any(isinstance(args,list) and args and args[0]=="mapper" for _,args,_ in selected)
    assert not any(isinstance(args,list) and args and args[0]=="point_triangulator" for _,args,_ in selected)


def test_older_driver_keeps_compatible_legacy_gpu_sift(monkeypatch):
    monkeypatch.setattr(engine,"bundle_manifest",lambda exe:{"cuda":True} if exe=="modern" else {})
    monkeypatch.setattr(engine,"gpu_device",lambda exe,*_:{"name":"GPU"} if exe=="legacy" else None)
    monkeypatch.setattr(engine,"sibling_engine",lambda exe,name:"legacy" if name=="colmap-legacy" else "cpu")
    assert engine._select_bundled("modern")=="legacy"


def test_neural_commands_route_to_modern_cpu_without_new_flags_on_legacy(monkeypatch):
    from photomesh import colmap
    monkeypatch.setattr(engine,"sibling_engine",lambda exe,name:"cpu" if name=="colmap-cpu" else None)
    monkeypatch.setattr(colmap,"colmap_options",lambda exe,*_:{"FeatureExtraction.type"} if exe=="cpu" else set())
    assert engine.feature_executable("legacy",{"feature_method":"ALIKED + LightGlue"})=="cpu"
    assert engine.feature_executable("legacy",{"feature_method":"SIFT"})=="legacy"


def test_dynamic_command_binding_preserves_python_and_native_fallback():
    from photomesh.colmap import Try,PYTHON,resolve_cmd
    native=Try(["global_mapper"],fallback=lambda:[("fallback",["mapper"],1)])
    bound=engine.bind_steps("modern-cpu",[("plan",lambda:[("native",native,1)],0),
                                         ("python",[PYTHON,"validate_model","cfg"],1)])
    dynamic=bound[0][1]()
    assert resolve_cmd("legacy",dynamic[0][1])[0]=="modern-cpu"
    fallback=dynamic[0][1].fallback()
    assert resolve_cmd("legacy",fallback[0][1])[0]=="modern-cpu"
    assert bound[1][1][0]==PYTHON and not hasattr(bound[1][1],"executable")


def test_disabling_preselection_matches_all_pairs():
    from photomesh.fastpipe import select_pairs
    names=[f"photo{i}.jpg" for i in range(16)]
    pairs=select_pairs(names,[{}]*16,use_desc=False,use_gps=False)
    assert len(pairs)==120 and ("photo0.jpg","photo15.jpg") in pairs


def test_headless_native_environment_is_isolated_without_logfile(monkeypatch):
    from photomesh import fastpipe as fp
    monkeypatch.setattr(fp,"child_env",lambda *_:{"ENGINE":"isolated"})
    calls=[]
    monkeypatch.setattr(fp.subprocess,"run",lambda *a,**k:calls.append(k) or SimpleNamespace(returncode=0))
    fp._run_logged("colmap",["mapper"],"mapping",None)
    assert calls[0]["env"]=={"ENGINE":"isolated"}


def test_working_size_collision_does_not_merge_different_original_sensors(tmp_path,monkeypatch):
    from photomesh import fastpipe as fp,colmap
    monkeypatch.setattr(colmap,"colmap_options",lambda *_:set())
    steps=fp.fast_align_steps("engine",str(tmp_path),["a.jpg","b.jpg"],
        [{"width":3200,"height":2400},{"width":4000,"height":3000}],
        {"accuracy":"High","key_point_limit":2048,"coarse_to_fine":True,"use_gpu":False})
    labels=[label for label,*_ in steps]
    assert labels.index("Rescaling key points")<labels.index("Grouping cameras")
    db=str(tmp_path/"mixed.db")
    with sqlite3.connect(db) as con:
        con.executescript("CREATE TABLE cameras(camera_id INTEGER PRIMARY KEY,model INTEGER,width INTEGER,height INTEGER,params BLOB,prior_focal_length INTEGER); CREATE TABLE images(image_id INTEGER PRIMARY KEY,name TEXT,camera_id INTEGER); CREATE TABLE keypoints(image_id INTEGER,rows INTEGER,cols INTEGER,data BLOB);")
        for cid,name in [(1,"a.jpg"),(2,"b.jpg")]:
            con.execute("INSERT INTO cameras VALUES(?,?,256,192,?,0)",(cid,2,np.array([307.2,128.,96.,0.]).tobytes()))
            con.execute("INSERT INTO images VALUES(?,?,?)",(cid,name,cid))
    dims={"a.jpg":{"orig":(3200,2400),"work":(256,192)},
          "b.jpg":{"orig":(4000,3000),"work":(256,192)}}
    fp.rescale_db_to_original(db,dims,"work")
    groups=fp.merge_identical_cameras(db)
    assert len(groups)==2
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT width,height FROM cameras ORDER BY camera_id").fetchall()==[(3200,2400),(4000,3000)]
