"""CPU-native integration and timing on a deterministic, known aerial scene.

Build assets are prepared separately. No network or user dataset is used here.
A synthetic benchmark is not evidence of absolute speed on every aerial survey.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"tests"))
from photomesh import colmap as cm, colmap_io as cio, engine, fastpipe as fp


def command(exe,args,log):
    started=time.perf_counter()
    env=engine.child_env(exe)
    env.update({"HTTP_PROXY":"http://127.0.0.1:9","HTTPS_PROXY":"http://127.0.0.1:9","ALL_PROXY":"http://127.0.0.1:9"})
    result=subprocess.run([exe,*args],capture_output=True,text=True,errors="replace",timeout=240,env=env)
    log.write("> "+" ".join(args)+"\n"+result.stdout+result.stderr+"\n"); log.flush()
    if result.returncode:
        raise RuntimeError(f"Native engine exit {result.returncode}: {args[0]}\n"+(result.stderr+result.stdout)[-6000:])
    if "Downloading" in result.stdout+result.stderr:
        raise AssertionError("Native processing attempted a download")
    return time.perf_counter()-started


def make_scene(folder):
    import texsynth
    from scipy import ndimage
    rng=np.random.default_rng(2026)
    texture=np.zeros((512,512,3),float)
    for scale,weight in ((32,100),(64,60),(128,35)):
        part=rng.uniform(0,1,(scale,scale,3))
        texture+=ndimage.zoom(part,(512/scale,512/scale,1),order=1)*weight
    texture=np.clip(texture,0,255)
    previous=texsynth.albedo
    def albedo(points):
        x=np.clip(points[:,0]/20*511,0,511); y=np.clip(points[:,1]/20*511,0,511)
        return np.stack([ndimage.map_coordinates(texture[...,c],[y,x],order=1) for c in range(3)],1)
    texsynth.albedo=albedo
    try: return texsynth.make_scene(str(folder),n_mesh=60)
    finally: texsynth.albedo=previous


def measure_alignment(exe,root,scene,method,mapper):
    from photomesh.georef import umeyama
    folder=root/(method.replace(" ","_").replace("+","_")+"-"+mapper); folder.mkdir()
    database=str(folder/"database.db"); out=folder/"sparse"; out.mkdir()
    photos=os.path.dirname(next(iter(scene["photos"].values())))
    settings={"feature_method":method,"key_point_limit":2048,"use_gpu":False}
    truth_images=cio.read_images(os.path.join(scene["model"],"images.bin"))
    truth_cameras=cio.read_cameras(os.path.join(scene["model"],"cameras.bin"))
    times={}
    with (folder/"native.log").open("w",encoding="utf-8") as log:
        extract=["feature_extractor","--database_path",database,"--image_path",photos]
        extract+=engine.matching_arguments(exe,"feature_extractor",settings,True)
        extract+=cm.opt(exe,"feature_extractor",["SiftExtraction.max_num_features"],2048)
        times["extract"]=command(exe,extract,log)
        # Known camera calibration is the controlled input for this numerical benchmark.
        by_name={im.name:truth_cameras[im.camera_id] for im in truth_images.values()}
        with closing(sqlite3.connect(database)) as con:
            rows=list(con.execute("SELECT name,camera_id FROM images"))
            for name,cid in rows:
                camera=by_name[name]
                con.execute("UPDATE cameras SET model=?,params=?,prior_focal_length=1 WHERE camera_id=?",
                            (camera.model,np.asarray(camera.params,np.float64).tobytes(),cid))
            con.commit()
        fp.merge_identical_cameras(database)
        match=["exhaustive_matcher","--database_path",database]
        match+=engine.matching_arguments(exe,"exhaustive_matcher",settings)
        times["match"]=command(exe,match,log)
        if mapper=="global":
            mapping=engine.global_arguments(exe,settings,database,photos,str(out))
            if mapping is None: raise AssertionError("Pinned engine has no global mapper")
            mapping+=cm.opt(exe,"global_mapper",["GlobalMapper.min_model_size"],3)
            mapping+=cm.opt(exe,"global_mapper",["GlobalMapper.multiple_models"],0)
        else:
            mapping=["mapper","--database_path",database,"--image_path",photos,"--output_path",str(out)]
            mapping+=cm.opt(exe,"mapper",["Mapper.min_model_size"],3)
            mapping+=cm.opt(exe,"mapper",["Mapper.multiple_models"],0)
        times["map"]=command(exe,mapping,log)
        models=[p for p in out.iterdir() if p.is_dir() and (p/"images.bin").is_file()]
        if not models: raise AssertionError("Engine produced no reconstruction")
        model=max((engine.validate_model(str(path)) for path in models),key=lambda value:len(value.images))
        truth={im.name:im for im in truth_images.values()}
        src=np.array([im.center() for im in model.images.values()])
        dst=np.array([truth[im.name].center() for im in model.images.values()])
        scale,R,t=umeyama(src,dst)
        error=float(np.sqrt(np.mean(np.sum((src@R.T*scale+t-dst)**2,1))))
        pixels=cio.observation_errors(model)[0]
        reprojection=float(np.sqrt(np.mean(pixels**2)))
        if len(model.images)<12 or len(model.points)<100 or error>.5 or reprojection>2.:
            raise AssertionError(f"Geometry regression: {len(model.images)} cameras, {len(model.points)} points, {error} m center RMS, {reprojection} px RMS")
        # Exercise the actual native reader after changing the model frame.
        from photomesh.georef import transform_model
        transform_model(model,2.5,np.eye(3),np.array([100.,200.,30.]))
        changed=folder/"changed"; cio.write_model(str(changed),model)
        reread=folder/"reread"; reread.mkdir()
        command(exe,["model_converter","--input_path",str(changed),"--output_path",str(reread),"--output_type","BIN"],log)
        native=cio.read_model(str(reread))
        for iid,im in model.images.items():
            np.testing.assert_allclose(native.images[iid].center(),im.center(),atol=1e-7)
        np.testing.assert_allclose(native.points.xyz,model.points.xyz,atol=1e-7)
    return {"method":method,"mapper":mapper,"cameras":len(model.images),"points":len(model.points),
            "camera_rms_m":error,"reprojection_rms_px":reprojection,"seconds":times,
            "total_seconds":sum(times.values())}


def measure_fast_pipeline(exe,root,scene):
    from photomesh.georef import umeyama
    from PIL import Image
    folder=root/"fast-coarse-fine"; folder.mkdir()
    names=list(scene["photos"])
    photos=os.path.dirname(next(iter(scene["photos"].values())))
    (folder/"image_root.txt").write_text(photos,encoding="utf-8")
    (folder/"image_list.txt").write_text("\n".join(names)+"\n",encoding="utf-8")
    infos=[]
    for path in scene["photos"].values():
        with Image.open(path) as image: infos.append({"width":image.width,"height":image.height})
    settings={"feature_method":"SIFT","key_point_limit":2048,"use_gpu":False,"accuracy":"High",
              "coarse_to_fine":True,"mapper":"Incremental","single_camera":True,
              "generic":False,"reference":False,"min_shared":8}
    # A smaller coarse threshold exercises both stages on the small known scene.
    previous=fp.COARSE_MAX_SIZE; fp.COARSE_MAX_SIZE=256
    try: steps=fp.fast_align_steps(exe,str(folder),names,infos,settings)
    finally: fp.COARSE_MAX_SIZE=previous
    # Two database generations, native triangulation and modern BA flags are exercised.
    timing=fp.run_steps(exe,steps,log=lambda *_:None,logfile=str(folder/"native.log"))
    model=engine.validate_model(str(folder/"sparse"/"0"))
    truth=cio.read_images(os.path.join(scene["model"],"images.bin")); truth={im.name:im for im in truth.values()}
    src=np.array([im.center() for im in model.images.values()])
    dst=np.array([truth[im.name].center() for im in model.images.values()])
    scale,R,t=umeyama(src,dst)
    error=float(np.sqrt(np.mean(np.sum((src@R.T*scale+t-dst)**2,1))))
    reprojection=float(np.sqrt(np.mean(cio.observation_errors(model)[0]**2)))
    if len(model.images)<12 or len(model.points)<100 or reprojection>2. or error>.5:
        raise AssertionError(f"Fast pipeline geometry regression: {len(model.images)} cameras, {len(model.points)} points, {error} m, {reprojection} px")
    return {"method":"SIFT","mapper":"fast-coarse-fine","cameras":len(model.images),"points":len(model.points),
            "camera_rms_m":error,"reprojection_rms_px":reprojection,"stages":timing,
            "total_seconds":sum(item[1] for item in timing)}


def measure_cloud_mesh(root,scene):
    import open3d as o3d
    from photomesh import pcfilter,mesh
    o3d.utility.random.seed(17)
    source=o3d.io.read_triangle_mesh(scene["mesh"]); source.compute_vertex_normals()
    cloud=source.sample_points_uniformly(30000)
    original=np.asarray(cloud.points); normals=np.asarray(cloud.normals)
    start=time.perf_counter()
    filtered,stats=pcfilter.filter_cloud({"xyz":original,"normals":normals},
        {"statistical":True,"radius":True,"elevation":False,"local_ratio":3},log=lambda *_:None)
    filter_seconds=time.perf_counter()-start
    path=root/"mesh-input.ply"
    pcfilter.write_cloud(str(path),filtered["xyz"],normals=filtered.get("normals"))
    start=time.perf_counter()
    result=mesh.build_mesh({"source":"Point cloud","cloud":str(path),"out":str(root/"mesh.ply"),
        "tmp":str(root/"mesh.building.ply"),"face_count":"Medium","max_points":30000},log=lambda *_:None)
    mesh_seconds=time.perf_counter()-start
    actual=o3d.io.read_triangle_mesh(str(root/"mesh.ply"))
    surface=o3d.t.geometry.RaycastingScene()
    surface.add_triangles(o3d.core.Tensor(np.asarray(source.vertices,np.float32)),
                          o3d.core.Tensor(np.asarray(source.triangles,np.uint32)))
    distance=surface.compute_distance(o3d.core.Tensor(np.asarray(actual.vertices,np.float32))).numpy()
    if not result["faces"] or not np.isfinite(distance).all() or np.median(distance)>.25:
        raise AssertionError("Mesh geometry regression")
    return {"input_points":30000,"filtered_points":len(filtered["xyz"]),"filter_seconds":filter_seconds,
            "mesh":result,"mesh_seconds":mesh_seconds,"median_surface_distance":float(np.median(distance)),"filters":stats}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe",required=True)
    parser.add_argument("--output",default="engine-benchmark.json")
    args=parser.parse_args()
    if not engine.has_global(args.exe): raise AssertionError("Expected integrated global mapper")
    with tempfile.TemporaryDirectory(prefix="engine-benchmark-") as temp:
        root=Path(temp); scene=make_scene(root/"scene")
        results=[]
        for method,mapper in (("SIFT","incremental"),("SIFT","global"),("ALIKED + LightGlue","global")):
            result=measure_alignment(args.exe,root,scene,method,mapper)
            results.append(result); print(json.dumps(result),flush=True)
        fast=measure_fast_pipeline(args.exe,root,scene)
        results.append(fast); print(json.dumps(fast),flush=True)
        cloud_mesh=measure_cloud_mesh(root,scene)
        print(json.dumps(cloud_mesh),flush=True)
        # SIFT + LightGlue has distinct weights/options and gets its own real native probe.
        engine.execution_settings(args.exe,{"feature_method":"SIFT + LightGlue","key_point_limit":2048,
                                           "use_gpu":False},str(root),print)
    payload={"engine":engine.PINNED_VERSION,"dataset":"deterministic synthetic calibrated aerial block",
             "results":results,"cloud_mesh":cloud_mesh,"gpu_reconstruction_tested":False}
    Path(args.output).write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(json.dumps(payload,indent=2),flush=True)


if __name__=="__main__":
    main()
