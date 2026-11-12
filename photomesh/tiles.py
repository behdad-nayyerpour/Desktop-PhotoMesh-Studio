"""Build Tiled Model: LOD hierarchy of a (textured) mesh or a dense point cloud,
written as Cesium 3D Tiles (tileset.json + b3dm / pnts, or glb for 3D Tiles
1.1) plus `photomesh_tiles.json`, the index our viewer streams from.

Mesh source: adaptive quadtree on the ground plane (faces assigned by
centroid, a node is split while it holds more than `tile_faces` faces).
Leaves keep the original faces; every parent is the union of its children,
decimated (quadric, borders locked) to ~tile_faces. Each tile gets its own
texture atlas: faces are grouped by dominant normal direction into planar
charts, packed, and baked from the source model - every texel's 3D point is
mapped to the closest point of the full-resolution model (Embree closest
point query) and its texture (or vertex colour) is sampled there. Texel size
doubles per level up; geometricError = 16 x texel size (+ decimation error),
so a tile refines when its texels get bigger than ~1 screen pixel at the
default maximum screen-space error of 16 px.
Point cloud source: same quadtree over points (pnts tiles, parents are random
subsets of their children).
"""
from __future__ import annotations

import json
import math
import os

import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from . import gltf
from .workflow import product_transaction, file_stamp, processing_crs
from .texture import (plane_basis, rasterize, pack, split_large, charts_from_labels, face_adjacency,
                      dilate, bilinear)

DEFAULTS = {"source": "Model", "tile_faces": 60000, "tile_points": 250000, "max_tex": 2048,
            "format": "b3dm", "jpeg_quality": 85, "max_depth": 12, "pixel_size": 0.0}


class Node:
    def __init__(self, key, depth, lo, hi):
        self.key, self.depth, self.lo, self.hi = key, depth, np.asarray(lo, float), np.asarray(hi, float)
        self.children = []; self.items = None
        self.mesh = None; self.error = 0.0; self.texel = 0.0; self.file = None
        self.bmin = None; self.bmax = None; self.count = 0


def quadtree(xy, limit, max_depth):
    lo, hi = xy.min(0), xy.max(0)
    side = float(max(hi - lo).max()) * 1.0001 + 1e-9
    root = Node("r", 0, lo, lo + side)
    root.items = np.arange(len(xy))
    stack = [root]
    while stack:
        n = stack.pop()
        if len(n.items) <= limit:
            continue
        if n.depth >= max_depth or np.all(np.ptp(xy[n.items], axis=0) < 1e-12):
            # Coincident centroids still obey the hard count bound.
            for start in range(0, len(n.items), limit):
                child = Node(n.key + "_" + str(start//limit), n.depth+1, n.lo, n.hi)
                child.items = n.items[start:start+limit]; n.children.append(child)
            n.items = None
            continue
        mid = (n.lo + n.hi) / 2
        p = xy[n.items]
        q = (p[:, 0] >= mid[0]).astype(int) + 2 * (p[:, 1] >= mid[1]).astype(int)
        for k in range(4):
            sel = n.items[q == k]
            if not len(sel):
                continue
            lo = np.where([k & 1, k & 2], mid, n.lo); hi = np.where([k & 1, k & 2], n.hi, mid)
            c = Node(n.key + str(k), n.depth + 1, lo, hi); c.items = sel
            n.children.append(c); stack.append(c)
        n.items = None
    return root


def rotation_to_z(up):
    """Smallest rotation taking `up` to +z (identity for z-up frames)."""
    up = np.asarray(up, float) / np.linalg.norm(up)
    z = np.array([0, 0, 1.0])
    v = np.cross(up, z); c = float(up @ z)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def walk(n):
    yield n
    for c in n.children:
        yield from walk(c)


def compact(V, F):
    used, inv = np.unique(F.ravel(), return_inverse=True)
    return V[used], inv.reshape(-1, 3), used


def decimate(V, F, target):
    import open3d as o3d
    m = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(V), o3d.utility.Vector3iVector(F.astype(np.int32)))
    m.remove_duplicated_vertices(); m.remove_degenerate_triangles()
    try:
        d = m.simplify_quadric_decimation(int(target), boundary_weight=1000.0)
    except TypeError:                                   # older Open3D: no boundary_weight
        d = m.simplify_quadric_decimation(int(target))
    d.remove_degenerate_triangles(); d.remove_unreferenced_vertices()
    return np.asarray(d.vertices), np.asarray(d.triangles).astype(np.int64)


class Baker:
    """Texture lookup on the full-resolution source model."""
    def __init__(self, V, F, uvp=None, page=None, pages=None, vcol=None):
        import open3d as o3d
        self.o3d = o3d
        self.scene = o3d.t.geometry.RaycastingScene()
        self.scene.add_triangles(o3d.core.Tensor(V.astype(np.float32)), o3d.core.Tensor(F.astype(np.uint32)))
        self.V, self.F, self.uvp, self.page, self.pages, self.vcol = V, F, uvp, page, pages, vcol

    def colours(self, P):
        r = self.scene.compute_closest_points(self.o3d.core.Tensor(P.astype(np.float32)))
        prim = r["primitive_ids"].numpy().astype(np.int64)
        uv = r["primitive_uvs"].numpy().astype(np.float64)
        b = np.stack([1 - uv[:, 0] - uv[:, 1], uv[:, 0], uv[:, 1]], 1)
        if self.pages is not None:
            q = (self.uvp[prim] * b[:, :, None]).sum(1)
            out = np.zeros((len(P), 3), np.float32)
            pg = self.page[prim]
            for k, img in enumerate(self.pages):
                s = pg == k
                if s.any():
                    out[s] = bilinear(img, q[s, 0], q[s, 1])
            return out
        if self.vcol is not None:
            f = self.F[prim]
            return (self.vcol[f] * b[:, :, None]).sum(1).astype(np.float32)
        return np.full((len(P), 3), 180.0, np.float32)


def tile_atlas(V, F, up, texel, max_tex, pad=2):
    """Planar charts by dominant normal (6 directions in the up frame), packed
    into one square page. Returns (uvp (m,3,2), size, texel)."""
    e1, e2 = plane_basis(up)
    B = np.stack([e1, e2, up / np.linalg.norm(up)])
    P = V[F]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    nl = n @ B.T
    ax = np.argmax(np.abs(nl), 1); sgn = np.sign(nl[np.arange(len(F)), ax])
    lab = ax * 2 + (sgn > 0)
    pl = {0: (1, 2), 1: (1, 2), 2: (0, 2), 3: (0, 2), 4: (0, 1), 5: (0, 1)}
    Q = P @ B.T                                     # (m,3,3) coords in up frame
    uv = np.zeros((len(F), 3, 2))
    for l, (a, b) in pl.items():
        s = lab == l
        uv[s, :, 0] = Q[s, :, a]; uv[s, :, 1] = -Q[s, :, b] if l >= 4 else -Q[s, :, b]
    nb = face_adjacency(F)
    comp = charts_from_labels(np.arange(len(F)), lab, nb)
    # chart area in world units -> atlas size for the wanted texel size.  Every
    # chart also costs a fixed border (pad + 1 px) whatever the scale, which
    # dominates for coarse levels of rough drone meshes (thousands of tiny
    # charts): count it too, otherwise the page is far too small to ever fit.
    lo = np.full((comp.max() + 1, 2), np.inf); hi = np.full((comp.max() + 1, 2), -np.inf)
    np.minimum.at(lo, comp, uv.min(1)); np.maximum.at(hi, comp, uv.max(1))
    ext = (hi - lo) / texel
    need = float(((ext[:, 0] + 2 + 2 * pad) * (ext[:, 1] + 2 + 2 * pad)).sum())
    side = math.sqrt(need / 0.6)
    size = int(min(max_tex, max(64, 2 ** math.ceil(math.log2(max(side, 1))))))
    px = uv / texel
    while True:
        for p in (pad, 1) if size >= max_tex else (pad,):
            cc = split_large(px, comp, size * 0.9)
            try:
                page, uvp, s = pack(px, cc, size, 1, p, 1.0, log=lambda m: None)
                return uvp, size, texel / s
            except RuntimeError:
                pass
        if size >= max_tex:
            break
        size = min(max_tex, size * 2)
    # Too many charts even for the largest page: give every triangle its own
    # cell (always fits; a coarse level of detail loses nothing visible).
    return face_grid_atlas(px, size, texel)


def face_grid_atlas(px, size, texel):
    """Fallback atlas: one square cell per triangle, the triangle scaled to fit
    its cell with a half-pixel border. Returns (uvp (m,3,2), size, texel)."""
    m = len(px)
    cols = max(1, math.ceil(math.sqrt(m)))
    if size // cols < 2:
        raise ValueError("Tile exceeds texture capacity; reduce triangles per tile")
    cell = size // cols
    lo = px.min(1); ext = np.maximum((px.max(1) - lo).max(1), 1e-12)
    sc = (cell - 1.0) / ext                     # uniform per triangle, keeps the shape
    i = np.arange(m)
    org = np.stack([(i % cols) * cell, (i // cols) * cell], 1) + 0.5
    uvp = (px - lo[:, None, :]) * sc[:, None, None] + org[:, None, :]
    return uvp.astype(np.float32), size, texel / float(np.median(np.minimum(sc, 1e6)))


def bake_tile(V, F, baker, up, texel, max_tex, quality):
    from io import BytesIO
    from PIL import Image
    uvp, size, texel_eff = tile_atlas(V, F, up, texel, max_tex)
    tp, ty, tx, tf, b1, b2 = rasterize(uvp, np.zeros(len(F), np.int64), 1, size)
    b0 = 1 - b1 - b2
    f = F[tf]
    P = V[f[:, 0]] * b0[:, None] + V[f[:, 1]] * b1[:, None] + V[f[:, 2]] * b2[:, None]
    img = np.zeros((size, size, 3), np.float32); mask = np.zeros((size, size), bool)
    if len(P):
        img[ty, tx] = baker.colours(P); mask[ty, tx] = True
    img, _m = dilate(img, mask, 4)
    img[~_m] = img[_m].mean(0) if _m.any() else 128
    buf = BytesIO()
    Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(buf, "JPEG", quality=quality)
    return uvp / size, buf.getvalue(), size, texel_eff


def _box(bmin, bmax):
    c = (bmin + bmax) / 2; h = (bmax - bmin) / 2 + 1e-6
    return {"box": [*c.tolist(), float(h[0]), 0, 0, 0, float(h[1]), 0, 0, 0, float(h[2])]}


def _root_transform(georef, center_model):
    """ENU -> ECEF matrix (column-major) for UTM / WGS84-georeferenced datasets."""
    if georef and georef.get('coordinate_frame'):
        from .coordinates import frame_basis, enu_to_geographic
        origin, basis = frame_basis(georef['coordinate_frame'])
        offset = np.asarray(georef.get('offset') or [0, 0, 0], float)
        matrix = np.eye(4)
        matrix[:3, :3] = basis.T
        matrix[:3, 3] = origin + basis.T @ offset
        lon, lat, height = enu_to_geographic(np.atleast_2d(center_model) + offset, georef['coordinate_frame'])[0]
        return matrix.T.ravel().tolist(), (float(lat), float(lon), float(height))
    if georef and georef.get('crs_kind') == 'proj':
        from pyproj import Transformer
        from .georef import ecef_to_geodetic
        world = np.asarray(center_model) + np.asarray(georef.get('offset') or [0, 0, 0])
        transform = Transformer.from_crs(georef['crs'], 4978, always_xy=True)
        earth = lambda xyz: np.asarray(transform.transform(*xyz), float)
        origin = earth(world)
        matrix = np.eye(4)
        for axis in range(3):
            delta = np.eye(3)[axis]
            matrix[:3, axis] = (earth(world + delta) - earth(world - delta)) / 2
        matrix[:3, 3] = origin - matrix[:3, :3] @ np.asarray(center_model)
        lat, lon, height = ecef_to_geodetic(origin)
        return matrix.T.ravel().tolist(), (float(lat[0]), float(lon[0]), float(height[0]))
    if not georef or georef.get("crs_kind") not in ("utm", "wgs84"):
        return None
    from .georef import utm_inverse, geodetic_to_ecef, enu_basis
    zone = georef.get("zone")
    if not zone:
        return None
    z, south = (zone if isinstance(zone, (list, tuple)) else (zone, False))
    E, N, h = (np.asarray(center_model) + np.asarray(georef.get("offset") or [0, 0, 0]))
    lat, lon = utm_inverse(E, N, int(z), bool(south))
    lat, lon = float(lat), float(lon)
    O = geodetic_to_ecef(lat, lon, float(h)); Bm = enu_basis(lat, lon)
    # UTM grid axes include meridian convergence and projection scale.
    # A local Jacobian preserves them rather than assuming grid north is true north.
    def earth(e,n,zheight):
        latitude,longitude=utm_inverse(e,n,int(z),bool(south))
        return geodetic_to_ecef(float(latitude),float(longitude),float(zheight))
    east=(earth(E+1,N,h)-earth(E-1,N,h))/2
    north=(earth(E,N+1,h)-earth(E,N-1,h))/2
    M = np.eye(4); M[:3, 0] = east; M[:3, 1] = north; M[:3, 2] = Bm[2]; M[:3, 3] = O - M[:3, :3] @ np.asarray(center_model, float)
    return M.T.ravel().tolist(), (lat, lon, float(h))


@product_transaction
def build_tiles(cfg, log=print, progress=None, cancel=None):
    """cfg: out_dir, source ('Model'|'Point cloud'), mesh, texture_dir (optional),
    cloud (ply), up [3], georef (dict or {}), + DEFAULTS."""
    c = dict(DEFAULTS); c.update({k: v for k, v in cfg.items() if v is not None})
    t_all = time.perf_counter(); stages = {}
    out = c["out_dir"]
    tmp = out
    os.makedirs(os.path.join(tmp, "tiles"), exist_ok=True)
    up = np.asarray(c.get("up") or [0, 0, 1.0], float); up /= np.linalg.norm(up)
    Rup = rotation_to_z(up)                # model frame -> up frame (z = up); identity when georeferenced
    georef = c.get("georef") or {}
    metric = bool(georef)
    def prog(p):
        if progress:
            progress(int(p), 100)
    if c["source"] == "Point cloud":
        c["format"] = "pnts"
        info = _build_points(c, tmp, Rup, log, prog, cancel)
    else:
        info = _build_mesh(c, tmp, Rup, up, log, prog, cancel, stages)
    root = info["root"]
    center = (root.bmin + root.bmax) / 2
    rt = _root_transform(georef, Rup.T @ center) if metric else None
    def tile_json(n):
        d = {"boundingVolume": _box(n.bmin, n.bmax), "geometricError": float(n.error), "refine": "REPLACE"}
        if n.file:
            d["content"] = {"uri": "tiles/" + n.file}
        if n.children:
            d["children"] = [tile_json(k) for k in n.children]
        return d
    rj = tile_json(root)
    if rt:
        transform = np.asarray(rt[0]).reshape(4, 4).T.copy()
        transform[:3, :3] = transform[:3, :3] @ Rup.T
        rj["transform"] = transform.T.ravel().tolist()
    ts = {"asset": {"version": "1.1" if c["format"] == "glb" else "1.0", "generator": "Lens2Mesh",
                    "tilesetVersion": time.strftime("%Y-%m-%dT%H:%M:%S")},
          "geometricError": float(root.error * 2 or 1.0), "root": rj,
          "extras": {"up_frame_rotation": Rup.tolist(), "georeferenced": metric,
                     "crs": processing_crs(georef) if georef else "local (not georeferenced)",
                     # tile vertices are in the local frame; world = Rup.T @ p + world_offset
                     # (UTM / WGS84 datasets are also placed on the globe by root.transform)
                     "world_offset": [float(x) for x in georef.get("offset")]
                     if georef and georef.get("offset") is not None else None}}
    with open(os.path.join(tmp, "tileset.json"), "w", encoding="utf-8") as fh:
        json.dump(ts, fh, indent=1)
    nodes = list(walk(root))
    levels = max(n.depth for n in nodes) + 1
    leaf_texel = min((n.texel for n in nodes if not n.children and n.texel), default=0.0)
    idx = {"format": "photomesh-tiles/1", "source": c["source"], "levels": levels, "tiles": len(nodes),
           "rotation_model_to_tiles": Rup.tolist(), "georeferenced": metric,
           "pixel_size": leaf_texel, "unit": "m" if metric else "model units",
           "faces": info.get("faces"), "points": info.get("points"),
           "root_location": rt[1] if rt else None,
           "nodes": [{"key": n.key, "depth": n.depth, "file": n.file, "error": n.error, "texel": n.texel,
                      "bmin": n.bmin.tolist(), "bmax": n.bmax.tolist(), "count": n.count,
                      "children": [k.key for k in n.children]} for n in nodes]}
    with open(os.path.join(tmp, "photomesh_tiles.json"), "w", encoding="utf-8") as fh:
        json.dump(idx, fh)
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _d, fs in os.walk(out) for f in fs)
    res = {"dir": out, "tileset": os.path.join(out, "tileset.json"), "index": os.path.join(out, "photomesh_tiles.json"),
           "levels": levels, "tiles": len(nodes), "pixel_size": leaf_texel, "georef": metric,
           "source": c["source"], "format": c["format"], "bytes": size, "faces": info.get("faces"),
           "points": info.get("points"), "seconds": round(time.perf_counter() - t_all, 2), "stages": stages}
    unit = f"{leaf_texel * 100:.2f} cm/pix" if metric else f"{leaf_texel:.4g} model units/pix (not georeferenced)"
    log(f"Tiled model: {len(nodes)} tiles in {levels} levels, pixel size {unit}, "
        f"{size / 1e6:.1f} MB, {res['seconds']:.1f} s -> {out}")
    prog(100)
    return res


def _build_mesh(c, tmp, Rup, up, log, prog, cancel, stages):
    from .texture import read_mesh
    t0 = time.perf_counter()
    from .plyio import ply_counts
    from .memguard import require_available_bytes
    vertices,faces=ply_counts(c["mesh"])
    geometry_budget=vertices*200+faces*300
    if geometry_budget>require_available_bytes()*.7:
        raise ValueError("Mesh-tile working arrays exceed available RAM; simplify the source mesh")
    V, F = read_mesh(c["mesh"])
    from .workflow import require_mesh
    require_mesh(V,F)
    baker_args = {}
    src_texel = 0.0
    tdir = c.get("texture_dir")
    if tdir and os.path.exists(os.path.join(tdir, "uv.npz")):
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        z = np.load(os.path.join(tdir, "uv.npz"))
        with open(os.path.join(tdir, "info.json"), encoding="utf-8") as fh:
            tinfo = json.load(fh)
        if len(z["uv"]) == len(F) and tinfo.get("mesh_stamp") == file_stamp(c["mesh"]):
            pages=[]; page_bytes=0
            for page_name in tinfo["pages"]:
                with Image.open(os.path.join(tdir,page_name)) as image:
                    page_bytes+=image.width*image.height*3
                    if geometry_budget+page_bytes>require_available_bytes()*.7:
                        z.close()
                        raise ValueError("Source texture pages exceed available RAM; rebuild texture with fewer/smaller pages")
                    pages.append(np.asarray(image.convert("RGB")))
            baker_args = dict(uvp=z["uv"].astype(np.float64), page=z["page"].astype(np.int64), pages=pages)
            src_texel = float(tinfo.get("texel_size") or 0)
            log(f"Tiled model: texture source {len(pages)} page(s), texel {src_texel:.4g}")
        else:
            log("Tiled model: texture does not match the model (rebuild texture) - using vertex colours")
        z.close()
    if not baker_args:
        from .plyio import load_ply
        m = load_ply(c["mesh"], max_points=0)
        if m["colors"] is not None:
            baker_args = dict(vcol=m["colors"][:, :3] * 255)
    from .memguard import require_available_bytes
    estimate=V.nbytes*6+F.nbytes*8+sum(image.nbytes for image in baker_args.get("pages",[]))
    if estimate>require_available_bytes()*.75:
        raise ValueError("Source geometry/texture exceeds the working-memory budget; simplify the source or reduce texture pages")
    baker = Baker(V, F, **baker_args)
    P = V[F]
    edge = float(np.median(np.linalg.norm(P[:, 1] - P[:, 0], axis=1)))
    if not src_texel:
        src_texel = edge / 4
    if c.get("pixel_size"):
        requested = float(c["pixel_size"])
        if requested < src_texel:
            log(f"Requested texel {requested:.6g} is finer than source {src_texel:.6g}; preserving source resolution")
        src_texel = max(src_texel, requested)
    stages["load"] = round(time.perf_counter() - t0, 2)
    log(f"Tiled model: source {len(V):,} vertices, {len(F):,} faces ({stages['load']:.1f} s)")
    Vu = V @ Rup.T                                     # up frame (x, y ground, z up)
    cent = Vu[F].mean(1)
    capacity = min(int(c["tile_faces"]), max(1, (int(c["max_tex"]) // 2) ** 2))
    root = quadtree(cent[:, :2], capacity, int(c["max_depth"]))
    nodes = list(walk(root))
    leaves = [n for n in nodes if not n.children]
    height = {}
    def h(n):
        height[n.key] = 0 if not n.children else 1 + max(h(k) for k in n.children)
        return height[n.key]
    h(root)
    log(f"Tiled model: quadtree {len(nodes)} tiles, {len(leaves)} leaves, depth {max(n.depth for n in nodes)}")
    done = [0]
    t0 = time.perf_counter()
    def write_node(n, Vt, Ft, texel):
        uvn, jpg, size, tex_eff = bake_tile(Vt, Ft, baker, up, texel, int(c["max_tex"]), int(c["jpeg_quality"]))
        pos, uvs, idx = gltf.split_corners(Vt @ Rup.T, Ft, uvn)
        n.bmin, n.bmax = pos.min(0), pos.max(0); n.count = len(Ft); n.texel = tex_eff
        glb = gltf.to_glb([{"positions": pos, "indices": idx, "uv": uvs, "image": jpg}], z_up=True)
        n.file = f"{n.key}.{'glb' if c['format'] == 'glb' else 'b3dm'}"
        with open(os.path.join(tmp, "tiles", n.file), "wb") as fh:
            fh.write(glb if c["format"] == "glb" else gltf.b3dm(glb))
        done[0] += 1
        prog(5 + 90 * done[0] / len(nodes))
        if cancel and cancel():
            raise KeyboardInterrupt
    from .memguard import cap_workers
    threads = cap_workers(max(1, min(8, (os.cpu_count() or 4) // 2)),
                          int(c["max_tex"]) ** 2 * 180 + capacity * 400)
    # leaves: original faces
    def leaf(n):
        Vt, Ft, _u = compact(V, F[n.items])
        n.mesh = (Vt, Ft); n.error = 0.0
        write_node(n, Vt, Ft, src_texel)
        n.mesh = None  # reconstruct leaves from original arrays when their parent needs them
    with ThreadPoolExecutor(threads) as ex:
        list(ex.map(leaf, leaves))
    stages["leaf tiles"] = round(time.perf_counter() - t0, 2)
    # parents bottom-up
    t0 = time.perf_counter()
    for hh in range(1, height[root.key] + 1):
        level = [n for n in nodes if n.children and height[n.key] == hh]
        def parent(n):
            Vs, Fs, off = [], [], 0
            for k in n.children:
                if k.mesh is None:
                    Vk, Fk, _ = compact(V, F[k.items])
                else:
                    Vk, Fk = k.mesh
                Vs.append(Vk); Fs.append(Fk + off); off += len(Vk)
            Vc = np.concatenate(Vs); Fc = np.concatenate(Fs)
            target = max(500, min(capacity, len(Fc) // 2))
            Vd, Fd = decimate(Vc, Fc, target)
            n.mesh = (Vd, Fd)
            # decimation error: distance of a sample of the children's vertices to the parent mesh
            import open3d as o3d
            sc = o3d.t.geometry.RaycastingScene()
            sc.add_triangles(o3d.core.Tensor(Vd.astype(np.float32)), o3d.core.Tensor(Fd.astype(np.uint32)))
            smp = Vc[:: max(1, len(Vc) // 20000)].astype(np.float32)
            dist = sc.compute_distance(o3d.core.Tensor(smp)).numpy()
            texel = src_texel * 2 ** hh
            write_node(n, Vd, Fd, texel)
            n.error = float(max(16 * n.texel, np.percentile(dist, 95) if len(dist) else 0))
            n.bmin = np.minimum(n.bmin, np.min([k.bmin for k in n.children], axis=0))
            n.bmax = np.maximum(n.bmax, np.max([k.bmax for k in n.children], axis=0))
        with ThreadPoolExecutor(threads) as ex:
            list(ex.map(parent, level))
        for n in level:
            for k in n.children:
                k.mesh = None
    stages["parent tiles"] = round(time.perf_counter() - t0, 2)
    # parent error must exceed children's
    def fix(n):
        for k in n.children:
            fix(k)
        if n.children:
            n.error = max(n.error, 1.5 * max(k.error for k in n.children))
    fix(root)
    for n in nodes:
        n.mesh = None
    return {"root": root, "faces": int(len(F))}


def _build_points(c, tmp, Rup, log, prog, cancel=None):
    from .pcfilter import read_cloud
    from .plyio import ply_counts
    from .memguard import require_available_bytes
    count,_ = ply_counts(c["cloud"])
    if count*200 > require_available_bytes()*.7:
        raise ValueError("Point-tile working arrays exceed available RAM; reduce or split the source cloud")
    cl = read_cloud(c["cloud"])
    X = cl.pop("xyz")
    if not np.allclose(Rup,np.eye(3)):
        X = X @ Rup.T
    from .workflow import require_points
    require_points(X,"Point cloud")
    rgb = cl.pop("rgb",None)
    del cl
    rgb = np.asarray(rgb, np.uint8) if rgb is not None else np.full((len(X), 3), 200, np.uint8)
    log(f"Tiled model: point cloud {len(X):,} points")
    lim = int(c["tile_points"])
    root = quadtree(X[:, :2], lim, int(c["max_depth"]))
    nodes = list(walk(root))
    rng = np.random.default_rng(0)
    def write(n, idx):
        P = X[idx]; n.bmin, n.bmax = P.min(0), P.max(0); n.count = len(idx)
        n.file = f"{n.key}.pnts"
        ctr = (n.bmin + n.bmax) / 2
        pos = (P - ctr).astype(np.float32)
        ft = {"POINTS_LENGTH": len(idx), "RTC_CENTER": ctr.tolist(), "POSITION": {"byteOffset": 0},
              "RGB": {"byteOffset": pos.nbytes}}
        fj = json.dumps(ft).encode()
        while (28 + len(fj)) % 8:
            fj += b" "
        body = pos.tobytes() + rgb[idx].tobytes()
        body += b"\0" * ((8 - len(body) % 8) % 8)
        import struct
        hdr = struct.pack("<4sIIIIII", b"pnts", 1, 28 + len(fj) + len(body), len(fj), len(body), 0, 0)
        with open(os.path.join(tmp, "tiles", n.file), "wb") as fh:
            fh.write(hdr + fj + body)
    sel = {}
    order = sorted(nodes, key=lambda n: -n.depth)
    for i, n in enumerate(order):
        if cancel and cancel(): raise KeyboardInterrupt
        if not n.children:
            idx = n.items
        else:
            idx = np.concatenate([sel[k.key] for k in n.children])
            if len(idx) > lim:
                idx = rng.choice(idx, lim, replace=False)
        sel[n.key] = idx
        write(n, idx)
        if n.children:
            n.bmin = np.minimum(n.bmin, np.min([k.bmin for k in n.children], axis=0))
            n.bmax = np.maximum(n.bmax, np.max([k.bmax for k in n.children], axis=0))
            for child in n.children:
                sel.pop(child.key, None)
        area = float(np.prod(np.maximum(n.bmax[:2] - n.bmin[:2], 1e-9)))
        sp = math.sqrt(area / max(len(idx), 1))
        n.texel = sp
        n.error = 0.0 if not n.children else 16 * sp
        prog(5 + 90 * (i + 1) / len(nodes))
    def fix(n):
        for k in n.children:
            fix(k)
        if n.children:
            n.error = max(n.error, 1.5 * max(k.error for k in n.children))
    fix(root)
    return {"root": root, "points": int(len(X))}


def zip_tiles(src_dir, zip_path):
    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:
        for dp, _d, fs in os.walk(src_dir):
            for f in fs:
                p = os.path.join(dp, f)
                z.write(p, os.path.relpath(p, src_dir).replace(os.sep, "/"))  # "/" in zips, also on Windows
    return zip_path
