"""Same-runner comparison with the last released source; no user files or network."""
import gc, json, os, statistics, subprocess, sys, tempfile, time, types
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"tests"))
from photomesh import texture, tiles
BASE="ee3e40e317b9111e3b7bd0c53ba7e174478a6b2c"


def baseline(module):
    source=subprocess.check_output(["git","show",f"{BASE}:photomesh/{module}.py"],cwd=ROOT).decode("utf-8")
    result=types.ModuleType("photomesh._baseline_"+module); result.__package__="photomesh"
    exec(compile(source,f"baseline/{module}.py","exec"),result.__dict__)
    return result


def timed(function,repeats=5):
    values=[]
    for _ in range(repeats):
        gc.collect(); start=time.perf_counter(); value=function()
        values.append(time.perf_counter()-start); del value
    return statistics.median(values)


def main():
    old=baseline("texture")
    rng=np.random.default_rng(42)
    n=12000
    base=rng.uniform(1,950,(n,1,2))
    uv=(base+np.array([[0,0],[8,0],[0,8.]])).astype(np.float32)
    pages=np.zeros(n,np.int64)
    a=old.rasterize(uv,pages,1,1024); b=texture.rasterize(uv,pages,1,1024)
    assert all(np.array_equal(x,y) for x,y in zip(a,b)), "Rasterization output differs"
    del a,b
    before=timed(lambda:old.rasterize(uv,pages,1,1024))
    after=timed(lambda:texture.rasterize(uv,pages,1,1024))
    result={"baseline":BASE,"rasterize":{"before_seconds":before,"after_seconds":after,"ratio":after/before}}
    # A real synthetic photo-texturing workload, not only a microbenchmark.
    import texsynth
    with tempfile.TemporaryDirectory() as folder:
        scene=texsynth.make_scene(os.path.join(folder,"scene"),ghost=True)
        def cfg(name):
            return dict(mesh=scene["mesh"],model=scene["model"],photos=scene["photos"],
                        out_dir=os.path.join(folder,name),size=512,max_res=0,write_glb=False)
        old.build_texture(cfg("warm-old"),log=lambda *_:None)
        texture.build_texture(cfg("warm-new"),log=lambda *_:None)
        counter=[0]
        def run(function,label):
            counter[0]+=1
            return function(cfg(label+str(counter[0])),log=lambda *_:None)
        before=timed(lambda:run(old.build_texture,"old"),3)
        after=timed(lambda:run(texture.build_texture,"new"),3)
        result["synthetic_texture"]={"before_seconds":before,"after_seconds":after,"ratio":after/before}
    Path("workflow-performance.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
    # Broad enough for shared-runner noise, strict enough to expose material regressions.
    if any(row["ratio"]>1.25 for row in result.values() if isinstance(row,dict) and "ratio" in row):
        raise SystemExit("Performance regression above 25%; investigate before release")


if __name__=="__main__": main()
