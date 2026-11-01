"""Block-capable DSM generation, retaining vectorized fast paths for small clouds."""
from __future__ import annotations
import json, math, os, tempfile, time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from .workflow import product_transaction, require_points, region_checked, raster_budget, vertex_blocks


@product_transaction
def build_dem(cfg, log=print, progress=None, cancel=None):
    from . import ortho as o, geotiff as gt
    from .memguard import available_bytes
    c = dict(o.DEM_DEFAULTS); c.update({k:v for k,v in cfg.items() if v is not None})
    started = time.perf_counter(); stages = {}
    def check():
        if cancel and cancel(): raise o.Cancelled("cancelled")
    def prog(n):
        if progress: progress(n,100)
        check()
    georef = c.get("georef") or {}
    off = o.georef_offset(georef)
    R = np.eye(3)
    if not georef and c.get("model") and c.get("photos"):
        from .texture import load_views
        R = o.projection_rotation(load_views(c["model"], c["photos"], lambda m:None), False)
    out = c["out_dir"]; os.makedirs(out, exist_ok=True)
    scratch = tempfile.TemporaryDirectory(prefix="dem-work-", dir=out)
    mapped = []
    try:
        def array(name, shape, dtype, fill=0):
            size = math.prod(shape)*np.dtype(dtype).itemsize
            if size > available_bytes()*.12:
                a = np.memmap(os.path.join(scratch.name,name), mode="w+", dtype=dtype, shape=shape)
                mapped.append(a)
            else: a = np.empty(shape,dtype)
            a[:] = fill
            return a
        P = F = surface = None
        source = c.get("source","Point cloud")
        if source == "Mesh":
            from .texture import read_mesh
            from .plyio import ply_counts
            vertices,faces=ply_counts(c["mesh"])
            if vertices*200+faces*300 > available_bytes()*.7:
                raise ValueError("Mesh DSM working arrays exceed available RAM; simplify the mesh or use a point-cloud source")
            P,F = read_mesh(c["mesh"])
            from .workflow import require_mesh
            require_mesh(P,F)
            if not len(F): raise ValueError("Mesh has no triangles")
            P = P @ R.T
            surface = o.Surface(P,F)
            npoints = len(P); lo,hi = P.min(0),P.max(0)
            # Mesh resolution follows surface area/triangle count, not vertex occupancy.
            q = P[F]
            area = float(np.linalg.norm(np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0]),axis=1).sum()/2)
            auto = o.nice(math.sqrt(max(area,1e-12)/max(len(F),1)))
        else:
            from .plyio import ply_counts, read_fast
            npoints = ply_counts(c["cloud"])[0]
            if not npoints: raise ValueError("Point cloud is empty")
            if c.get("aggregation")=="median" and npoints*64>available_bytes()*.5:
                raise ValueError("Exact median needs more RAM for this cloud; choose Mean/Highest or a smaller source")
            if npoints*80 < available_bytes()*.4:
                data = read_fast(c["cloud"])
                if data is not None:
                    v=data["vertex"]; P=np.column_stack([v["x"],v["y"],v["z"]]).astype(float) @ R.T
                    del data,v
                    require_points(P)
            lo,hi=np.full(3,np.inf),np.full(3,-np.inf)
            sample = []
            sample_stride=max(1,math.ceil(npoints/100000))
            def blocks():
                if P is not None:
                    yield P; return
                for v in vertex_blocks(c["cloud"]):
                    yield np.column_stack([v["x"],v["y"],v["z"]]).astype(float) @ R.T
            for xyz in blocks():
                require_points(xyz)
                lo,hi=np.minimum(lo,xyz.min(0)),np.maximum(hi,xyz.max(0))
                if P is None: sample.append(xyz[::sample_stride].copy())
            # Occupied-area estimate from a bounded sample; exact small-cloud path retained.
            samples = P if P is not None else np.concatenate(sample)
            g=max(float(np.ptp(hi[:2]-lo[:2])),float(np.max(hi[:2]-lo[:2])))/512 or 1.
            cells=np.floor((samples[:,:2]-lo[:2])/g).astype(np.int64)
            occupied=len(np.unique(cells[:,0]*100000+cells[:,1]))
            auto=o.nice(2*math.sqrt(occupied*g*g/npoints))
        region=region_checked(c.get("region"))
        if region:
            b=np.asarray(region)-np.array([off[0],off[1],off[0],off[1]])
            if b[2]<=lo[0] or b[0]>=hi[0] or b[3]<=lo[1] or b[1]>=hi[1]:
                raise ValueError("Region does not overlap the selected source")
            xmin,ymin,xmax,ymax=b
        else: xmin,ymin,xmax,ymax=lo[0],lo[1],hi[0],hi[1]
        px=float(c.get("pixel_size") or auto)
        if not np.isfinite(px) or px<=0: raise ValueError("Invalid raster resolution")
        x0,y1,W,H=o.make_grid(xmin,ymin,xmax,ymax,px,off[:2])
        if W*H>c["max_pixels"]: raise ValueError(f"DEM would be {W:,} x {H:,}; increase pixel size or select a region")
        budget=raster_budget(W,H,64,out)
        import shutil
        if shutil.disk_usage(out).free < W*H*48:
            raise ValueError("DEM scratch grids and TIFFs need more disk space; select a region or coarser pixels")
        log(f"DEM plan: {W:,} x {H:,}; pixel {px:.6g} {'m' if georef else 'model units'}; "
            f"~{budget['memory']/2**30:.2f} GiB working arrays; disk-backed when needed")
        dem=array("heights",(H,W),"f8",np.nan)
        measured=array("measured",(H,W),"bool",False)
        stages["read points"]=time.perf_counter()-started; prog(10)
        if surface is not None:
            # Native batched ray casting evaluates the actual mesh triangles.
            for r0 in range(0,H,256):
                rr,cc=np.meshgrid(np.arange(r0,min(r0+256,H)),np.arange(W),indexing="ij")
                z=surface.heights(x0+(cc.ravel()+.5)*px,y1-(rr.ravel()+.5)*px).reshape(rr.shape)
                dem[r0:r0+len(rr)]=z
                measured[r0:r0+len(rr)]=np.isfinite(z)
                prog(10+35*min(r0+256,H)/H)
        else:
            aggregate=c.get("aggregation","mean")
            cnt=array("counts",(W*H,),"i8",0)
            sums=array("sums",(W*H,),"f8",-np.inf if aggregate=="highest" else 0)
            med_idx=[]; med_z=[]
            for xyz in blocks():
                col=np.floor((xyz[:,0]-x0)/px).astype(np.int64)
                row=np.floor((y1-xyz[:,1])/px).astype(np.int64)
                ok=(col>=0)&(col<W)&(row>=0)&(row<H)
                idx=row[ok]*W+col[ok]; z=xyz[ok,2]
                if P is not None and aggregate=="mean":
                    cnt[:]=np.bincount(idx,minlength=W*H)
                    sums[:]=np.bincount(idx,weights=z,minlength=W*H)
                else:
                    np.add.at(cnt,idx,1)
                    if aggregate=="highest": np.maximum.at(sums,idx,z)
                    elif aggregate=="median": med_idx.append(idx); med_z.append(z)
                    else: np.add.at(sums,idx,z)
                check()
            has=cnt>0; measured[:]=has.reshape(H,W)
            if aggregate=="median":
                if npoints*32>available_bytes()*.5:
                    raise ValueError("Exact median needs more RAM for this cloud; choose Mean/Highest or a smaller region")
                idx=np.concatenate(med_idx); z=np.concatenate(med_z)
                order=np.argsort(idx,kind="stable"); keys=idx[order]
                unique,first,counts=np.unique(keys,return_index=True,return_counts=True)
                zs=z[order]
                for key,start,count in zip(unique,first,counts):
                    dem.ravel()[key]=np.median(zs[start:start+count])
            elif aggregate=="highest": dem.ravel()[has]=sums[has]
            else: dem.ravel()[has]=sums[has]/cnt[has]
        if not measured.any(): raise ValueError("No valid source data inside the output grid")
        stages["rasterize"]=time.perf_counter()-started-stages["read points"]; prog(50)
        from scipy import ndimage
        hole=~np.isfinite(dem)
        fillmask=array("filled",(H,W),"bool",False)
        maxfill=float(c.get("max_fill",10))
        smoothing=float(c.get("smooth_distance",px*3))
        # Halo depth is expressed in world units, independent of block boundaries.
        halo=max(2,math.ceil(maxfill/px),math.ceil(smoothing/px*4))
        interpolation=c.get("interpolation","Enabled")
        if interpolation!="Disabled" and hole.any():
            rows=H if interpolation=="Extrapolated" else min(H,256+2*halo)
            if W*rows*96 > available_bytes()*.65:
                raise ValueError("Interpolation halo exceeds available RAM; reduce fill/smoothing distance or use coarser pixels")
            if interpolation=="Extrapolated":
                # An exact global nearest lookup is necessary for unrestricted fill.
                # Guard it before allocation rather than failing partway through.
                if W*H*32 > available_bytes()*.65:
                    raise ValueError("Unrestricted extrapolation needs more RAM; use bounded fill, a region or coarser pixels")
                dist,(iy,ix)=ndimage.distance_transform_edt(hole,return_indices=True)
                fillmask[:]=hole
                proposed=dem[iy,ix]
                if smoothing>0:
                    valid=~hole
                    den=ndimage.gaussian_filter(valid.astype(float),smoothing/px)
                    num=ndimage.gaussian_filter(np.where(valid,dem,0),smoothing/px)
                    proposed=np.where(den>1e-3,num/np.maximum(den,1e-12),proposed)
                dem[hole]=proposed[hole]
            else:
                # Freeze measured values: neighbouring blocks must not use inferred heights as observations.
                original=dem.copy() if dem.nbytes<available_bytes()*.2 else array("original",(H,W),"f8",np.nan)
                if original is not dem: original[:]=dem
                for r0 in range(0,H,256):
                    r1=min(H,r0+256); a=max(0,r0-halo); b=min(H,r1+halo)
                    source_values=np.asarray(original[a:b])
                    valid=np.isfinite(source_values)
                    if not valid.any(): continue
                    dist,(iy,ix)=ndimage.distance_transform_edt(~valid,return_indices=True)
                    proposed=source_values[iy,ix]
                    if smoothing>0:
                        sigma=smoothing/px
                        den=ndimage.gaussian_filter(valid.astype(float),sigma)
                        num=ndimage.gaussian_filter(np.where(valid,source_values,0),sigma)
                        proposed=np.where(den>1e-3,num/np.maximum(den,1e-12),proposed)
                    center=slice(r0-a,r1-a)
                    fm=(~valid & (dist*px<=maxfill))[center]
                    dest=dem[r0:r1]; dest[fm]=proposed[center][fm]; fillmask[r0:r1]=fm
                    check()
        stages["interpolation"]=time.perf_counter()-started-sum(stages.values()); prog(70)
        from .workflow import processing_crs
        crs=processing_crs(georef) if georef else ""
        geo=(x0+off[0],y1+off[1],px,px)
        path=os.path.join(out,"dem.tif"); mask_path=os.path.join(out,"coverage.tif")
        writer=gt.TiledTiffWriter(path,gt.overview_levels(W,H),1,np.float32,int(c["tile"]),"Deflate",
                                 nodata=o.NODATA_DEM,geo=geo,crs=crs or 'LOCAL_CS["Local coordinates (model units)"]')
        maskwriter=gt.TiledTiffWriter(mask_path,gt.overview_levels(W,H),1,np.uint8,int(c["tile"]),"Deflate",
                                     nodata=0,geo=geo,crs=crs or 'LOCAL_CS["Local coordinates (model units)"]')
        zmin,zmax=np.inf,-np.inf
        try:
            with ThreadPoolExecutor(max(2,min(8,(os.cpu_count() or 4)//2))) as ex:
                for r0 in range(0,H,512):
                    z=np.asarray(dem[r0:r0+512]); valid=np.isfinite(z)
                    if valid.any(): zmin,zmax=min(zmin,float(z[valid].min()+off[2])),max(zmax,float(z[valid].max()+off[2]))
                    world=np.where(valid,z+off[2],o.NODATA_DEM).astype(np.float32)
                    mask=np.where(measured[r0:r0+512],1,np.where(fillmask[r0:r0+512],2,0)).astype(np.uint8)
                    writer.write_block(0,r0,0,world[...,None],ex)
                    maskwriter.write_block(0,r0,0,mask[...,None],ex)
                    prog(70+20*min(r0+512,H)/H)
                gt.build_overviews(writer,nodata=o.NODATA_DEM,executor=ex,cancel=cancel)
                gt.build_overviews(maskwriter,nodata=0,executor=ex,cancel=cancel)
            writer.close(); maskwriter.close()
        except BaseException:
            writer.abort(); maskwriter.abort(); raise
        info={"format":"photomesh-dem/1","surface_type":"DSM","dir":out,"path":path,"coverage_path":mask_path,
              "width":W,"height":H,"pixel_size":px,"origin":[x0+off[0],y1+off[1]],
              "bounds":[x0+off[0],y1-H*px+off[1],x0+W*px+off[0],y1+off[1]],
              "offset":off.tolist(),"rotation":R.tolist(),"georef":bool(georef),"crs":crs,"source":source,
              "interpolation":interpolation,"aggregation":c.get("aggregation","mean"),
              "z_range":[zmin,zmax],"filled_cells":int(fillmask.sum()),"measured_cells":int(measured.sum()),
              "valid_cells":int(np.isfinite(dem).sum()),"bytes":os.path.getsize(path),"nodata":o.NODATA_DEM,
              "seconds":round(time.perf_counter()-started,2),"stages":stages,"settings":cfg}
        # Close mapped arrays before the product directory can be published on Windows.
        for arr in mapped: arr.flush(); arr._mmap.close()
        mapped.clear(); scratch.cleanup()
        with open(os.path.join(out,"info.json"),"w",encoding="utf-8") as fh: json.dump(info,fh,indent=1)
        log(f"DEM: {W:,} x {H:,}, {info['measured_cells']:,} measured / {info['filled_cells']:,} inferred cells")
        prog(100)
        return info

    finally:
        for arr in mapped:
            if not arr._mmap.closed:
                arr._mmap.close()
        scratch.cleanup()
