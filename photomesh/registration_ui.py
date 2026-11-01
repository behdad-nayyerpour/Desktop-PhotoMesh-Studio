"""Added-photo registration UI, collecting only measured, usable controls."""
import json, os, tempfile, uuid
import numpy as np
from PySide6.QtWidgets import QMessageBox, QInputDialog
from .georef import _stem


class RegistrationMixin:
    def register_selected_photos(self, indices=None):
        ch=self.chunk
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
        positions={label:np.asarray(X,float) for label,X,_ctl in self._marker_positions()}
        photos=[]
        for index in indices:
            camera=ch.cameras[index]
            if not camera.width or not camera.height:
                from PIL import Image
                with Image.open(camera.path) as image: camera.width,camera.height=image.size
            xyz,xy=[],[]
            for marker in ch.markers:
                if marker.get("disabled") or not marker.get("enabled",True) or marker["label"] not in positions:
                    continue
                for name,projection in marker.get("projections",{}).items():
                    if _stem(name)==_stem(camera.label) and (len(projection)<3 or projection[2]):
                        xyz.append(positions[marker["label"]]); xy.append(projection[:2]); break
            try: validate_controls(xyz,xy,camera.width,camera.height)
            except ValueError as error:
                QMessageBox.information(self,"Align Selected Photos",f"{camera.label}: {error}"); return
            candidates=[cid for cid,cam in model.cameras.items() if cam.width==camera.width and cam.height==camera.height]
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
        from .colmap import prepare_images
        mapping=prepare_images(ch,generation)
        for photo in photos:
            photo["name"]=mapping[ch.cameras[photo["index"]].path]
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
