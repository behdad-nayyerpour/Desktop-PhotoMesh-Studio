"""Direct, thread-safe DEM sampling without decimating its cell grid."""
import json, os, threading
from collections import OrderedDict
import numpy as np
import math
from . import geotiff as gt


class RasterSurface:
    def __init__(self, path, offset=(0,0,0), rotation=None, crs=None):
        self.reader=gt.TiffReader(path)
        self.offset=np.asarray(offset,float)
        if not self.reader.geo:
            self.reader.close()
            raise ValueError("DEM has no spatial grid; rebuild or georeference the DEM first")
        x0,y1,px,py=self.reader.geo
        self.x0,self.y1,self.px,self.py=x0-self.offset[0],y1-self.offset[1],px,py
        self.width,self.height=self.reader.width,self.reader.height
        self.cache=OrderedDict(); self.lock=threading.Lock(); self.tile=512
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

    def _values(self,row,col):
        result=np.empty(len(row),np.float64)
        cols=math.ceil(self.width/self.tile)
        keys=(row//self.tile)*cols+col//self.tile
        order=np.argsort(keys,kind="stable")
        unique,starts=np.unique(keys[order],return_index=True)
        ends=np.r_[starts[1:],len(order)]
        for key,start,end in zip(unique,starts,ends):
            ids=order[start:end]; tr,tc=divmod(int(key),cols)
            with self.lock:
                data=self.cache.pop(int(key),None)
                if data is None:
                    data=self.reader.read_region(0,tr*self.tile,tc*self.tile,
                        min(self.tile,self.height-tr*self.tile),min(self.tile,self.width-tc*self.tile))[...,0].astype(np.float32)
                    data[~np.isfinite(data)]=np.nan
                    if self.reader.nodata is not None: data[data==self.reader.nodata]=np.nan
                self.cache[int(key)]=data
                while len(self.cache)>64: self.cache.popitem(last=False)
            result[ids]=data[row[ids]-tr*self.tile,col[ids]-tc*self.tile]
        return result

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
            r1=np.minimum(ri+1,self.height-1); c1=np.minimum(ci+1,self.width-1)
            values=self._values(np.r_[ri,ri,r1,r1],np.r_[ci,c1,ci,c1]).reshape(4,-1)
            fx,fy=cc-ci,rr-ri
            weights=np.stack([(1-fx)*(1-fy),fx*(1-fy),(1-fx)*fy,fx*fy])
            # Zero-weight nodata neighbours must not invalidate an exact cell centre.
            valid=np.all(np.isfinite(values)|(weights<1e-12),axis=0)
            sample=np.where(weights>1e-12,values,0)*weights
            heights=sample.sum(0)-self.offset[2]
            out[sel]=np.where(valid,heights,np.nan)
        return out

    def occluded(self,X,C,eps):
        X=np.asarray(X); C=np.broadcast_to(C,X.shape); D=C-X
        blocked=np.zeros(len(X),bool)
        # Above the highest DEM cell there can be no terrain occlusion.
        distance=np.linalg.norm(D,axis=1)
        begin=np.minimum(.99,eps/np.maximum(distance,1e-9))
        end=np.where(D[:,2]>1e-9,np.clip((self.zmax-X[:,2])/np.maximum(D[:,2],1e-9),0,.999),.999)
        span=np.maximum(np.abs(D[:,0])/self.px,np.abs(D[:,1])/self.py)
        steps=np.ceil(2*span*np.maximum(end-begin,0)).astype(int)
        for start in range(0,len(X),10000):
            stop=min(start+10000,len(X)); active=steps[start:stop]>0
            indices=np.arange(start,stop)[active]
            if not len(indices): continue
            number=int(steps[indices].max())
            for k in range(1,number+1):
                sel=indices[(steps[indices]>=k)&~blocked[indices]]
                if not len(sel): continue
                fraction=begin[sel]+(end[sel]-begin[sel])*k/steps[sel]
                P=X[sel]+D[sel]*fraction[:,None]
                height=self.heights(P[:,0],P[:,1])
                blocked[sel] |= np.isfinite(height)&(height>P[:,2]+eps)
        return blocked

    def close(self):
        self.reader.close()
