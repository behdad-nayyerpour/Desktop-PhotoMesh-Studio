"""Direct, thread-safe DEM sampling without decimating its cell grid."""
import json, os
import numpy as np
from . import geotiff as gt


class RasterSurface:
    def __init__(self, path, offset=(0,0,0), rotation=None, crs=None):
        self.reader=gt.TiffReader(path)
        self.offset=np.asarray(offset,float)
        x0,y1,px,py=self.reader.geo
        self.x0,self.y1,self.px,self.py=x0-self.offset[0],y1-self.offset[1],px,py
        self.width,self.height=self.reader.width,self.reader.height
        info_path=os.path.join(os.path.dirname(path),"info.json")
        info={}
        if os.path.isfile(info_path):
            with open(info_path,encoding="utf-8") as fh: info=json.load(fh)
        if rotation is not None and info.get("rotation") is not None:
            if not np.allclose(info["rotation"],rotation,atol=1e-7):
                raise ValueError("DEM and cameras use different projection frames; rebuild DEM")
        if crs and info.get("crs") and crs != info["crs"]:
            raise ValueError("DEM and cameras use different coordinate systems")
        zr=info.get("z_range") or [-1e4,1e4]
        self.zmin=float(zr[0] or 0)-self.offset[2]
        self.zmax=float(zr[1] or 0)-self.offset[2]
        self.lo=np.array([self.x0,self.y1-self.height*py,self.zmin])
        self.hi=np.array([self.x0+self.width*px,self.y1,self.zmax])

    def heights(self,x,y):
        x,y=np.asarray(x),np.asarray(y)
        col=(x-self.x0)/self.px-.5; row=(self.y1-y)/self.py-.5
        out=np.full(x.shape,np.nan)
        ok=(col>=-.5)&(row>=-.5)&(col<self.width-.5)&(row<self.height-.5)
        idx=np.flatnonzero(ok)
        for start in range(0,len(idx),100000):
            sel=idx[start:start+100000]
            cc=np.clip(col[sel],0,self.width-1); rr=np.clip(row[sel],0,self.height-1)
            ci=np.floor(cc).astype(int); ri=np.floor(rr).astype(int)
            a,b=int(ri.min()),int(ci.min())
            h=min(self.height,int(ri.max())+2)-a; w=min(self.width,int(ci.max())+2)-b
            data=self.reader.read_region(0,a,b,h,w)[...,0].astype(float)
            invalid=~np.isfinite(data)
            if self.reader.nodata is not None: invalid |= data==self.reader.nodata
            data[invalid]=np.nan
            r=ri-a; c=ci-b; r1=np.minimum(r+1,h-1); c1=np.minimum(c+1,w-1)
            fx,fy=cc-ci,rr-ri
            out[sel]=(data[r,c]*(1-fx)*(1-fy)+data[r,c1]*fx*(1-fy)+
                      data[r1,c]*(1-fx)*fy+data[r1,c1]*fx*fy)-self.offset[2]
        return out

    def occluded(self,X,C,eps):
        X=np.asarray(X); C=np.broadcast_to(C,X.shape)
        blocked=np.zeros(len(X),bool)
        # Test the segment against the height field; zero-distance end samples are excluded.
        for fraction in np.linspace(.03,.97,20):
            P=X+(C-X)*fraction
            height=self.heights(P[:,0],P[:,1])
            blocked |= np.isfinite(height)&(height>P[:,2]+eps)
        return blocked

    def close(self):
        self.reader.close()
