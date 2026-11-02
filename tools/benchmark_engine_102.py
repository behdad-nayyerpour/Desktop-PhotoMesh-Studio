"""CPU-native integration and timing on a deterministic, known aerial scene.

Build assets are prepared separately. No network or user dataset is used here.
A synthetic benchmark is not evidence of absolute speed on every aerial survey.
"""
from __future__ import annotations
import argparse
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
        with sqlite3.connect(database) as con:
            rows=list(con.execute("SELECT name,camera_id FROM images"))
            for name,cid in rows:
                camera=by_name[name]
                con.execute("UPDATE cameras SET model=?,params=?,prior_focal_length=1 WHERE camera_id=?",
                            (camera.model,np.asarray(camera.params,np.float64).tobytes(),cid))
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
        # SIFT + LightGlue has distinct weights/options and gets its own real native probe.
        engine.execution_settings(args.exe,{"feature_method":"SIFT + LightGlue","key_point_limit":2048,
                                           "use_gpu":False},str(root),print)
    payload={"engine":engine.PINNED_VERSION,"dataset":"deterministic synthetic calibrated aerial block",
             "results":results,"gpu_reconstruction_tested":False}
    Path(args.output).write_text(json.dumps(payload,indent=2),encoding="utf-8")
    print(json.dumps(payload,indent=2),flush=True)


if __name__=="__main__":
    main()
