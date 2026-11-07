"""Added-photo registration UI, collecting only measured, usable controls."""
import os, uuid
import numpy as np
from PySide6.QtWidgets import QMessageBox, QInputDialog
from .georef import _stem


class RegistrationMixin:
    def register_selected_photos(self, indices=None):
        if not self._require_saved("Align Selected Photos"):
            return
        ch=self.dataset
        if indices is None:
            indices=[item.data(256) for item in self.photos.selectedItems()]
        indices=sorted(set(int(i) for i in indices or []))
        indices=[i for i in indices if 0<=i<len(ch.cameras) and not ch.cameras[i].aligned]
        if not indices:
            QMessageBox.information(self,"Align Selected Photos","Select new, unaligned photos first."); return
        if not ch.aligned_count():
            QMessageBox.information(self,"Align Selected Photos","Align the original project first."); return
        from . import colmap_io as cio
        from .registration import validate_controls
        from .bgjob import run_modal
        model_dir=self._model_dir()
        model=cio.read_model(model_dir)
        from . import georef as g
        from .photonames import photo_dimensions
        g.validate_projection_dimensions(model,photo_dimensions(ch))
        positions={}
        for marker in self._marker_objs():
            if marker.disabled or not marker.enabled:
                continue
            if marker.ref is not None and ch.georef:
                positions[marker.label] = (g.CRS.parse(ch.crs).to_metric(
                    np.atleast_2d(marker.ref),ch.georef.get("zone"))[0] -
                    np.asarray(ch.georef.get("offset") or [0,0,0],float))
            else:
                point,_n=g.triangulate_marker(model,marker.projections,measured_only=True)
                if point is not None:
                    positions[marker.label]=point
        photos=[]
        for index in indices:
            camera=ch.cameras[index]
            if not camera.width or not camera.height:
                from PIL import Image
                with Image.open(camera.path) as image: camera.width,camera.height=image.size
            marker_key = self._photo_marker_key(index)
            if marker_key is None:
                QMessageBox.information(self,"Align Selected Photos",f"{camera.label}: ambiguous photo identity; repair aliases first."); return
            xyz,xy=[],[]
            for marker in ch.markers:
                if marker.get("disabled") or not marker.get("enabled",True) or marker["label"] not in positions:
                    continue
                for name,projection in marker.get("projections",{}).items():
                    if _stem(name)==marker_key and (len(projection)<3 or projection[2]):
                        xyz.append(positions[marker["label"]]); xy.append(projection[:2]); break
            try: validate_controls(xyz,xy,camera.width,camera.height)
            except ValueError as error:
                QMessageBox.information(self,"Align Selected Photos",f"{camera.label}: {error}"); return
            groups={(cam.model,cam.params.tobytes()):cid for cid,cam in model.cameras.items()
                    if cam.width==camera.width and cam.height==camera.height}
            candidates=list(groups.values())
            if not candidates:
                QMessageBox.information(self,"Align Selected Photos",f"{camera.label}: no calibrated camera with matching dimensions"); return
            cid=candidates[0]
            if len(candidates)>1:
                selected,ok=QInputDialog.getItem(self,"Calibration",f"Calibration for {camera.label}:",
                    [str(i) for i in candidates],0,False)
                if not ok: return
                cid=int(selected)
            name=camera.colmap_name or os.path.basename(camera.path)
            occupied={im.name for im in model.images.values()} | {p["name"] for p in photos}
            base,ext=os.path.splitext(name); suffix=1
            while name in occupied:
                name=f"{base}_{suffix}{ext}"; suffix+=1
            photos.append({"index":index,"name":name,"width":camera.width,"height":camera.height,
                           "camera_id":cid,"xyz":np.asarray(xyz).tolist(),"xy":xy})
        wd=self.project.default_workdir(ch)
        generation=os.path.join(wd,"registration-"+uuid.uuid4().hex[:12])
        destination=os.path.join(generation,"sparse","0")
        expose_registration_photos(ch,generation,photos)
        cfg={"model":model_dir,"output":destination,"photos":photos}
        from .registration import register
        messages=[]
        result,cancelled,error=run_modal(self,"Align Selected Photos","Solving camera poses from measured controls...",
            lambda report,stop: register(cfg,log=messages.append,progress=lambda i,n:report(i,n),cancel=stop),len(photos))
        if cancelled or error:
            if error: self.show_error("Align Selected Photos",error)
            return
        # Complete all poses first; no partial UI registration on a failed batch.
        for message in messages: self.log(message)
        ch.workdir=generation
        for item in result["added"]:
            camera=ch.cameras[item["index"]]
            camera.aligned=True; camera.est=item["center"]; camera.rot=item["rotation"]; camera.colmap_name=item["name"]
        self._invalidate_camera_products(ch)
        self.set_modified(); self.refresh_all(); self.reload_view()
        if result["added"]:
            self.open_photo(result["added"][0]["index"])
            self._update_photo_shapes()


def expose_registration_photos(dataset,folder,photos):
    """Stable aliases: adding a duplicate basename never renames an existing camera."""
    selected={p["index"]:p["name"] for p in photos}
    aliases={}
    for index,camera in enumerate(dataset.cameras):
        name=selected.get(index) or camera.colmap_name
        if name:
            if name in aliases and os.path.normcase(aliases[name])!=os.path.normcase(camera.path):
                raise ValueError("Ambiguous camera aliases; repair photo paths before registration")
            aliases[name]=camera.path
    roots={os.path.dirname(os.path.abspath(path)) for path in aliases.values()}
    direct=len(roots)==1 and all(name==os.path.basename(path) for name,path in aliases.items())
    if direct:
        root=next(iter(roots))
    else:
        import shutil
        root=os.path.join(folder,"images"); os.makedirs(root,exist_ok=True)
        for name,path in aliases.items():
            destination=os.path.abspath(os.path.join(root,name))
            if os.path.commonpath([destination,os.path.abspath(root)])!=os.path.abspath(root):
                raise ValueError("Invalid image alias")
            os.makedirs(os.path.dirname(destination),exist_ok=True)
            try: os.link(path,destination)
            except OSError:
                try: os.symlink(path,destination)
                except OSError: shutil.copy2(path,destination)
    os.makedirs(folder,exist_ok=True)
    with open(os.path.join(folder,"image_root.txt"),"w",encoding="utf-8") as fh:
        fh.write("images" if not direct else root)
    with open(os.path.join(folder,"image_list.txt"),"w",encoding="utf-8") as fh:
        fh.write("\n".join(sorted(aliases))+"\n")
