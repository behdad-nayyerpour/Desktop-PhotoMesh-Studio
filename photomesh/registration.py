"""GCP resection for added photographs; existing camera poses never move."""
import copy, json, os
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation
from . import colmap_io as cio
from .workflow import publish_directory


def validate_controls(xyz, xy, width, height):
    xyz,xy=np.asarray(xyz,float),np.asarray(xy,float)
    if len(xyz)<6:
        raise ValueError(f"At least 6 measured controls with known 3D positions are required; found {len(xyz)}")
    if not np.isfinite(xyz).all() or not np.isfinite(xy).all():
        raise ValueError("Non-finite control coordinates")
    if np.linalg.matrix_rank(xyz-xyz.mean(0))<2:
        raise ValueError("Control points are collinear in 3D")
    if np.linalg.matrix_rank(xy-xy.mean(0))<2:
        raise ValueError("Image controls are collinear")
    if ConvexHull(xy).volume < .01*width*height:
        raise ValueError("Controls cover less than 1% of the photo; spread them over the image")
    if np.any(xy<0) or np.any(xy[:,0]>=width) or np.any(xy[:,1]>=height):
        raise ValueError("Control projection lies outside the photo")


def solve_pose(camera, xyz, xy, initial_images, max_error=5.0):
    xyz,xy=np.asarray(xyz,float),np.asarray(xy,float)
    validate_controls(xyz,xy,camera.width,camera.height)
    origin=xyz.mean(0); scale=max(float(np.linalg.norm(xyz-origin,axis=1).mean()),1e-6)
    local=(xyz-origin)/scale
    # Translation is normalized for stable derivatives in engineering coordinate systems.
    def residual(p):
        R=Rotation.from_rotvec(p[:3]).as_matrix()
        uv,z=cio.project(camera,R,p[3:],local)
        return (uv-xy).ravel()
    seeds=sorted(initial_images,key=lambda im:np.linalg.norm(im.center()-origin))[:12]
    best=None
    for im in seeds:
        R=im.R()
        p=np.r_[Rotation.from_matrix(R).as_rotvec(),(R@origin+im.tvec)/scale]
        fit=least_squares(residual,p,loss="soft_l1",f_scale=2,max_nfev=200,method="trf")
        R=Rotation.from_rotvec(fit.x[:3]).as_matrix()
        uv,z=cio.project(camera,R,fit.x[3:],local)
        error=np.linalg.norm(uv-xy,axis=1)
        if np.all(z>0) and np.max(error)<=max_error:
            score=float(np.sqrt(np.mean(error**2)))
            if best is None or score<best[0]:
                best=(score,R,scale*fit.x[3:]-R@origin)
    if best is None:
        raise ValueError("No stable pose satisfies all controls within 5 pixels; check marking/calibration")
    score,R,t=best
    return R,t,score


def register(cfg,log=print,progress=None,cancel=None):
    model=cio.read_model(cfg["model"])
    added=[]
    for index,photo in enumerate(cfg["photos"]):
        if cancel and cancel(): raise ValueError("Registration cancelled; previous alignment kept")
        candidates=[(cid,cam) for cid,cam in model.cameras.items()
                    if cam.width==photo["width"] and cam.height==photo["height"]]
        if photo.get("camera_id") is not None:
            candidates=[v for v in candidates if v[0]==photo["camera_id"]]
        unique={}
        for cid,cam in candidates: unique[(cam.model,cam.params.tobytes())]=(cid,cam)
        if len(unique)!=1:
            raise ValueError(f"{photo['name']}: select one known calibration group with matching image dimensions")
        cid,cam=next(iter(unique.values()))
        R,t,error=solve_pose(cam,photo["xyz"],photo["xy"],list(model.images.values()))
        if any(im.name==photo["name"] for im in model.images.values()):
            raise ValueError("This photo is already registered")
        iid=max(model.images,default=0)+1
        model.images[iid]=cio.Image(photo["name"],cid,cio.rot_to_qvec(R),t,
                                   np.empty((0,2)),np.empty(0,dtype=np.int64))
        added.append({"index":photo["index"],"name":photo["name"],"center":(-R.T@t).tolist(),
                      "rotation":R.tolist(),"rmse":error})
        log(f"Registered {photo['name']}: {len(photo['xyz'])} controls, {error:.3f} pixel RMSE")
        if progress: progress(index+1,len(cfg["photos"]))
    # Write a complete model generation; publication never edits the original model files in place.
    import tempfile
    destination=cfg["output"]
    os.makedirs(os.path.dirname(destination),exist_ok=True)
    temporary=tempfile.mkdtemp(prefix="registered-",dir=os.path.dirname(destination))
    try:
        cio.write_model(temporary,model)
        if cancel and cancel(): raise ValueError("Registration cancelled; previous alignment kept")
        publish_directory(temporary,destination)
    finally:
        if os.path.isdir(temporary):
            import shutil
            shutil.rmtree(temporary)
    return {"added":added,"model":destination}
