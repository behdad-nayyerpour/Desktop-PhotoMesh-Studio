"""Ground control points, coordinate systems and georeferencing.

* CRS: local metric (LOCAL_CS / "XYZ"), WGS84 geographic (EPSG:4326) and
  UTM (EPSG:326zz/327zz). UTM is implemented here (Krueger series, sub-mm
  inside a zone) so no PROJ data is needed at runtime; pyproj is only used by
  the tests to cross-check when installed.
* Import of marker files: Metashape "Export Reference" text (as exported from
  the Reference pane, incl. '# CoordinateSystem:' header), plain
  label/X/Y/Z[/accuracy] text or CSV, survey XML (<surveydata>) and Metashape
  marker XML (with photo projections), plus a projections CSV
  (marker, photo, x, y).
* Marker triangulation, Helmert (7-parameter similarity) initialization and
  GCP-constrained Levenberg-Marquardt bundle adjustment with a Schur point
  elimination. Model-specific calibration, measured image observations,
  surveyed control XYZ and optional photo GPS retain explicit units/weights.
* Per-marker error report (X/Y/Z/total m, pixel) and RMSE for control and
  check points.
"""
from __future__ import annotations

import csv

import json
import math
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict

import time
import numpy as np

from . import colmap_io as cio

# defaults as in common photogrammetry practice (Metashape's Reference settings)
DEFAULTS = {"camera_accuracy": 10.0, "camera_accuracy_z": 10.0, "marker_accuracy": 0.005,
            "marker_accuracy_z": 0.005, "projection_accuracy": 0.5, "tie_accuracy": 1.0}

# ===================================================================== CRS
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)


def geodetic_to_ecef(lat, lon, h):
    lat, lon = np.radians(lat), np.radians(lon)
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat) ** 2)
    return np.stack([(N + h) * np.cos(lat) * np.cos(lon), (N + h) * np.cos(lat) * np.sin(lon),
                     (N * (1 - WGS84_E2) + h) * np.sin(lat)], -1)


def ecef_to_geodetic(X):
    X = np.atleast_2d(X); x, y, z = X[:, 0], X[:, 1], X[:, 2]
    lon = np.arctan2(y, x); p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1 - WGS84_E2))
    for _ in range(6):
        N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat) ** 2)
        h = p / np.cos(lat) - N
        lat = np.arctan2(z, p * (1 - WGS84_E2 * N / (N + h)))
    return np.degrees(lat), np.degrees(lon), h


def enu_basis(lat0, lon0):
    la, lo = math.radians(lat0), math.radians(lon0)
    return np.array([[-math.sin(lo), math.cos(lo), 0],
                     [-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)],
                     [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)]])


def utm_zone(lon, lat=0.0):
    z = int((lon + 180) // 6) + 1
    if 56 <= lat < 64 and 3 <= lon < 12:
        z = 32
    if 72 <= lat < 84 and lon >= 0:
        z = {0: 31, 1: 31, 2: 33, 3: 33, 4: 35, 5: 35, 6: 37}.get(int(lon // 6), z) if lon < 42 else z
    return z


def _utm_consts():
    n = WGS84_F / (2 - WGS84_F)
    A = WGS84_A / (1 + n) * (1 + n ** 2 / 4 + n ** 4 / 64)
    alpha = [n / 2 - 2 * n ** 2 / 3 + 5 * n ** 3 / 16 + 41 * n ** 4 / 180,
             13 * n ** 2 / 48 - 3 * n ** 3 / 5 + 557 * n ** 4 / 1440,
             61 * n ** 3 / 240 - 103 * n ** 4 / 140, 49561 * n ** 4 / 161280]
    beta = [n / 2 - 2 * n ** 2 / 3 + 37 * n ** 3 / 96 - n ** 4 / 360,
            n ** 2 / 48 + n ** 3 / 15 - 437 * n ** 4 / 1440,
            17 * n ** 3 / 480 - 37 * n ** 4 / 840, 4397 * n ** 4 / 161280]
    delta = [2 * n - 2 * n ** 2 / 3 - 2 * n ** 3 + 116 * n ** 4 / 45,
             7 * n ** 2 / 3 - 8 * n ** 3 / 5 - 227 * n ** 4 / 45,
             56 * n ** 3 / 15 - 136 * n ** 4 / 35, 4279 * n ** 4 / 630]
    return n, A, alpha, beta, delta


def utm_forward(lat, lon, zone, south=False):
    """Geographic (deg) -> UTM easting/northing (m), Krueger series."""
    n, A, alpha, _, _ = _utm_consts()
    k0 = 0.9996
    lat = np.radians(np.asarray(lat, float)); lon = np.radians(np.asarray(lon, float))
    lon0 = math.radians(zone * 6 - 183)
    t = np.sinh(np.arctanh(np.sin(lat)) - 2 * math.sqrt(n) / (1 + n) *
                np.arctanh(2 * math.sqrt(n) / (1 + n) * np.sin(lat)))
    xi = np.arctan2(t, np.cos(lon - lon0)); eta = np.arctanh(np.sin(lon - lon0) / np.sqrt(1 + t * t))
    E = eta.copy(); N = xi.copy()
    for j, a in enumerate(alpha, 1):
        E += a * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
        N += a * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
    return 500000 + k0 * A * E, (10000000 if south else 0) + k0 * A * N


def utm_inverse(E, N, zone, south=False):
    n, A, _, beta, delta = _utm_consts()
    k0 = 0.9996
    xi = (np.asarray(N, float) - (10000000 if south else 0)) / (k0 * A)
    eta = (np.asarray(E, float) - 500000) / (k0 * A)
    xp, ep = xi.copy(), eta.copy()
    for j, b in enumerate(beta, 1):
        xp -= b * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
        ep -= b * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
    chi = np.arcsin(np.sin(xp) / np.cosh(ep))
    lat = chi.copy()
    for j, d in enumerate(delta, 1):
        lat += d * np.sin(2 * j * chi)
    lon = math.radians(zone * 6 - 183) + np.arctan2(np.sinh(ep), np.cos(xp))
    return np.degrees(lat), np.degrees(lon)


@dataclass
class CRS:
    kind: str = "local"        # local | wgs84 | utm
    zone: int = 0
    south: bool = False
    name: str = "Local Coordinates (m)"

    @property
    def epsg(self):
        if self.kind == "wgs84":
            return 4326
        if self.kind == "utm":
            return (32700 if self.south else 32600) + self.zone
        return None

    @classmethod
    def parse(cls, text):
        t = (text or "").strip()
        u = t.upper()
        m = re.search(r"EPSG[:\s\"',]*(\d{4,5})", u)
        code = int(m.group(1)) if m else None
        if "LOCAL_CS" in u or u in ("", "XYZ", "LOCAL") or "LOCAL COORD" in u:
            return cls("local", name=_wkt_name(t) or "Local Coordinates (m)")
        m2 = re.search(r"UTM ZONE\s*(\d{1,2})\s*([NS])", u)
        if m2:
            return cls("utm", int(m2.group(1)), m2.group(2) == "S", f"WGS 84 / UTM zone {int(m2.group(1))}{m2.group(2)}")
        if code and (32601 <= code <= 32660 or 32701 <= code <= 32760):
            z = code % 100; s = code > 32700
            return cls("utm", z, s, f"WGS 84 / UTM zone {z}{'S' if s else 'N'}")
        if code in (4326, 4979) or "WGS 84" in u or "WGS84" in u:
            return cls("wgs84", name="WGS 84 (EPSG::4326)")
        if u.startswith("PROJCS") or u.startswith("GEOGCS") or code:
            raise ValueError(f"Unsupported coordinate system: {t[:120]}")
        return cls("local")

    def to_metric(self, xyz, zone_hint=None):
        """Marker/camera coordinates -> metric frame used for fitting:
        local/UTM: unchanged; WGS84 (lon, lat, alt) -> UTM of the zone_hint."""
        xyz = np.asarray(xyz, float)
        if self.kind != "wgs84":
            return xyz.copy()
        zone, south = zone_hint or (utm_zone(np.mean(xyz[:, 0]), np.mean(xyz[:, 1])), np.mean(xyz[:, 1]) < 0)
        E, N = utm_forward(xyz[:, 1], xyz[:, 0], zone, south)
        return np.column_stack([E, N, xyz[:, 2]])


def _wkt_name(t):
    m = re.search(r'LOCAL_CS\["([^"]+)"', t)
    return m.group(1) if m else ""


# ================================================================= markers
@dataclass
class Marker:
    label: str
    ref: list | None = None              # reference X, Y, Z (CRS units)
    acc: list | None = None              # [xy accuracy, z accuracy] (m); None = default
    enabled: bool = True                 # True = control point, False = check point
    projections: dict = field(default_factory=dict)   # source photo -> [x, y, pinned, optional source]
    est: list | None = None              # estimated position (CRS units)
    disabled: bool = False               # excluded from adjustment/report, independent of Control/Check
    locked: bool = False                 # explicit user lock against accidental repositioning

    def to_dict(self):
        return asdict(self)


def _stem(name):
    b = os.path.basename(str(name))
    s, e = os.path.splitext(b)
    return (s if e.lower() in (".jpg", ".jpeg", ".tif", ".tiff", ".png", ".dng") else b).lower()


def _num(s):
    try:
        return float(str(s).strip())
    except Exception:
        return None


HEADER_KEYS = {
    "label": ("label", "name", "marker", "id", "point", "#label"),
    "x": ("x", "easting", "east", "e", "longitude", "lon", "x/longitude", "x/east"),
    "y": ("y", "northing", "north", "n", "latitude", "lat", "y/latitude", "y/north"),
    "z": ("z", "altitude", "alt", "height", "elevation", "h", "z/altitude"),
    "acc": ("accuracy", "acc", "accuracy_(m)", "xy_accuracy", "x_accuracy", "accuracy_x",
            "x_acc", "sxy", "acc_xy"),
    "acc_z": ("z_accuracy", "accuracy_z", "z_acc", "sz", "acc_z"),
    "enabled": ("enabled", "use", "control", "checked"),
}


def read_reference_text(path):
    """Marker coordinates from a text/CSV file. Returns (markers, CRS).

    Handles Metashape Reference exports (tab separated, '# CoordinateSystem:'
    line, '#Label X Y Z Error_(m) ...' header, '#Total error' footer) and
    simple 'label x y z [accuracy]' lists with any of tab/comma/semicolon/space.
    """
    text = open(path, encoding="utf-8-sig", errors="replace").read()
    crs_text = ""
    header = None
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            body = s.lstrip("#").strip()
            if body.lower().startswith("coordinatesystem"):
                crs_text = body.split(":", 1)[1].strip() if ":" in body else ""
            elif re.match(r"(?i)label\b|name\b", body):
                header = _split(body)
            continue
        rows.append(_split(s))
    if rows and header is None and _num(rows[0][1] if len(rows[0]) > 1 else "") is None:
        header, rows = rows[0], rows[1:]
    col = {}
    if header:
        h = [c.strip().lower().replace(" ", "_") for c in header]
        for key, names in HEADER_KEYS.items():
            for i, c in enumerate(h):
                if c in names and key not in col:
                    col[key] = i
    col.setdefault("label", 0); col.setdefault("x", 1); col.setdefault("y", 2); col.setdefault("z", 3)
    if not header and rows and len(rows[0]) >= 5 and _num(rows[0][4]) is not None:
        col["acc"] = 4
    markers = []
    for r in rows:
        if len(r) <= col["z"]:
            continue
        lab = r[col["label"]].strip()
        x, y, z = (_num(r[col[k]]) for k in ("x", "y", "z"))
        if not lab or x is None or y is None:
            continue
        m = Marker(lab, [x, y, z if z is not None else 0.0])
        a = _num(r[col["acc"]]) if "acc" in col and col["acc"] < len(r) else None
        az = _num(r[col["acc_z"]]) if "acc_z" in col and col["acc_z"] < len(r) else None
        if a:
            m.acc = [a, az or a]
        if "enabled" in col and col["enabled"] < len(r):
            m.enabled = r[col["enabled"]].strip().lower() not in ("0", "false", "no", "check")
        markers.append(m)
    crs = CRS.parse(crs_text) if crs_text else _guess_crs(markers)
    return markers, crs


def _split(s):
    for d in ("\t", ";", ","):
        if d in s:
            return [c.strip() for c in s.split(d)]
    return s.split()


def _guess_crs(markers):
    if not markers:
        return CRS()
    a = np.array([m.ref for m in markers], float)
    if np.all(np.abs(a[:, 0]) <= 180) and np.all(np.abs(a[:, 1]) <= 90) and np.ptp(a[:, 0]) < 1:
        return CRS("wgs84", name="WGS 84 (EPSG::4326)")
    return CRS()


def read_markers_xml(path):
    """Legacy marker XML (camera/marker records and frame locations) or
    survey XML (<surveydata><markers><marker name><gcp x y z checkpoint>).
    Returns (markers, CRS)."""
    root = ET.parse(path).getroot()
    if root.tag == "surveydata":
        crs = CRS.parse(root.get("epsgcode") and f"EPSG:{root.get('epsgcode')}" or root.get("coordinatesystem", ""))
        out = []
        for mk in root.iter("marker"):
            g = mk.find("gcp")
            ref = [float(g.get(k)) for k in ("x", "y", "z")] if g is not None else None
            m = Marker(mk.get("name") or mk.get("id"), ref,
                       enabled=(g is None or g.get("checkpoint", "false").lower() != "true"))
            for im in mk.iter("image"):
                if im.get("x") is not None:
                    m.projections[im.get("name") or im.get("label")] = [float(im.get("x")), float(im.get("y")), True]
            out.append(m)
        return out, crs
    # Locate the record container by its documented children, independent of
    # the container's legacy vendor-specific name.
    dataset = next((node for node in root.iter()
                    if node.find("markers") is not None and node.find("cameras") is not None), None)
    if dataset is None:
        raise ValueError("Marker XML has no camera and marker record container")
    cams = {c.get("id"): c.get("label") for c in dataset.iter("camera") if c.get("label")}
    crs_el = dataset.find("reference")
    crs = CRS.parse(crs_el.text if crs_el is not None and crs_el.text else "")
    byid = {}
    for mk in dataset.find("markers") if dataset.find("markers") is not None else []:
        ref = mk.find("reference")
        r = [float(ref.get(k)) for k in ("x", "y", "z")] if ref is not None and ref.get("x") else None
        m = Marker(mk.get("label"), r)
        if root.tag == "photomesh-reference":
            m.enabled = mk.get("enabled", "true").lower() != "false"
            m.disabled = mk.get("disabled", "false").lower() == "true"
            m.locked = mk.get("locked", "false").lower() == "true"
        if ref is not None:
            m.enabled = ref.get("enabled", "true").lower() != "false"
            if ref.get("sx"):
                m.acc = [float(ref.get("sx")), float(ref.get("sz") or ref.get("sx"))]
        byid[mk.get("id")] = m
    for fm in dataset.iter("frame"):
        for mk in fm.iter("marker"):
            m = byid.get(mk.get("marker_id"))
            if m is None:
                continue
            for loc in mk.findall("location"):
                lab = cams.get(loc.get("camera_id"))
                if lab:
                    m.projections[lab] = [float(loc.get("x")), float(loc.get("y")),
                                          loc.get("pinned", "true").lower() == "true"]
                    if root.tag == "photomesh-reference" and loc.get("source") in ("predicted", "refined"):
                        m.projections[lab].append(loc.get("source"))
    return list(byid.values()), crs


def write_markers_xml(path, markers, crs_text=""):
    """PhotoMesh reference XML, preserving reference accuracy and photo projections.
    CSV is available for exchange with applications requiring other XML schemas."""
    photos = sorted({p for m in markers for p in m.projections})
    pid = {p: i for i, p in enumerate(photos)}
    doc = ET.Element("photomesh-reference", version="2.0")
    ch = ET.SubElement(doc, "dataset", label="Project")
    cams = ET.SubElement(ch, "cameras")
    for p, i in pid.items():
        ET.SubElement(cams, "camera", id=str(i), label=p)
    mks = ET.SubElement(ch, "markers")
    for k, m in enumerate(markers):
        mk = ET.SubElement(mks, "marker", id=str(k), label=m.label, enabled=str(m.enabled).lower(),
                           disabled=str(m.disabled).lower(), locked=str(m.locked).lower())
        if m.ref is not None:
            a = {"x": repr(float(m.ref[0])), "y": repr(float(m.ref[1])), "z": repr(float(m.ref[2])),
                 "enabled": "true" if m.enabled else "false"}
            if m.acc:
                a.update(sx=repr(float(m.acc[0])), sy=repr(float(m.acc[0])), sz=repr(float(m.acc[1])))
            ET.SubElement(mk, "reference", a)
    fr = ET.SubElement(ET.SubElement(ch, "frames"), "frame", id="0")
    fm = ET.SubElement(fr, "markers")
    for k, m in enumerate(markers):
        if not m.projections:
            continue
        e = ET.SubElement(fm, "marker", marker_id=str(k))
        for p, v in m.projections.items():
            ET.SubElement(e, "location", camera_id=str(pid[p]), pinned="true" if (len(v) < 3 or v[2]) else "false",
                          x=repr(float(v[0])), y=repr(float(v[1])),
                          **({"source": v[3]} if len(v) > 3 and v[3] in ("predicted", "refined") else {}))
    if crs_text:
        ET.SubElement(ch, "reference").text = crs_text
    ET.ElementTree(doc).write(path, encoding="utf-8", xml_declaration=True)


def read_projections_csv(path, markers):
    """Add projections from 'marker,photo,x,y[,pinned]' rows to markers (by label)."""
    by = {m.label: m for m in markers}
    n = 0
    for r in csv.reader(open(path, encoding="utf-8-sig")):
        if len(r) < 4 or _num(r[2]) is None:
            continue
        m = by.setdefault(r[0].strip(), Marker(r[0].strip()))
        m.projections[r[1].strip()] = [float(r[2]), float(r[3]), (r[4].strip().lower() != "false") if len(r) > 4 else True]
        n += 1
    return [m for m in by.values()], n


def import_markers(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xml":
        return read_markers_xml(path)
    return read_reference_text(path)


def merge_markers(existing, new):
    """Update existing markers by label (coordinates/projections), append new."""
    by = {m.label: m for m in existing}
    for m in new:
        if m.label in by:
            o = by[m.label]
            if m.ref is not None:
                o.ref, o.acc, o.enabled = m.ref, m.acc or o.acc, m.enabled
            o.projections.update(m.projections)
        else:
            existing.append(m); by[m.label] = m
    return existing


# ============================================================ geometry
def umeyama(src, dst, w=None, scale=True):
    """Similarity dst ~ s R src + t (weighted least squares)."""
    src = np.asarray(src, float); dst = np.asarray(dst, float)
    w = np.ones(len(src)) if w is None else np.asarray(w, float)
    if src.ndim != 2 or src.shape[1:] != (3,) or src.shape != dst.shape or len(src) < 3 or not np.isfinite(src).all() or not np.isfinite(dst).all():
        raise ValueError("Similarity needs at least three finite paired 3D positions")
    if w.shape != (len(src),) or not np.isfinite(w).all() or np.any(w <= 0):
        raise ValueError("Similarity weights must be finite and positive")
    w = w / w.sum()
    ms, md = w @ src, w @ dst
    a, b = src - ms, dst - md
    S = (b * w[:, None]).T @ a
    U, D, Vt = np.linalg.svd(S)
    E = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        E[2, 2] = -1
    R = U @ E @ Vt
    var = (w * (a ** 2).sum(1)).sum()
    if var <= 1e-20:
        raise ValueError("Reference baseline is degenerate")
    s = float(np.trace(np.diag(D) @ E) / var) if scale else 1.0
    if not np.isfinite(s) or s <= 0:
        raise ValueError("Invalid similarity scale")
    return s, R, md - s * R @ ms


def robust_helmert(src, dst, w=None, max_iter=5, k=3.0, min_pts=3):
    """Umeyama with iterative outlier rejection; returns (s, R, t, inlier mask)."""
    src = np.asarray(src, float); dst = np.asarray(dst, float)
    keep = np.ones(len(src), bool)
    for _ in range(max_iter):
        s, R, t = umeyama(src[keep], dst[keep], None if w is None else np.asarray(w)[keep])
        r = np.linalg.norm(dst - (s * src @ R.T + t), axis=1)
        thr = max(k * 1.4826 * np.median(r[keep]), 1e-9)
        new = r <= thr
        if new.sum() < min_pts or np.array_equal(new, keep):
            break
        keep = new
    # The returned transform must fit the returned inliers, including when the
    # final rejection step reaches the iteration limit.
    s, R, t = umeyama(src[keep], dst[keep], None if w is None else np.asarray(w)[keep])
    return s, R, t, keep


def apply_sim(sim, X):
    s, R, t = sim
    return s * np.asarray(X, float) @ R.T + t


def sim_matrix(s, R, t):
    M = np.eye(4); M[:3, :3] = s * R; M[:3, 3] = t
    return M


def transform_model(model: cio.Model, s, R, t):
    """Apply X' = s R X + t to a COLMAP model (poses and points) in place."""
    for im in model.images.values():
        Ri = im.R(); C = im.center()
        Rn = Ri @ R.T; Cn = s * R @ C + t
        im.qvec = cio.rot_to_qvec(Rn); im.tvec = -Rn @ Cn
    model.points.xyz = s * model.points.xyz @ R.T + t
    return model


def name_index(model):
    """Unambiguous legacy photo stems only; never choose an arbitrary camera."""
    names = {}
    ambiguous = set()
    for iid, image in model.images.items():
        stem = _stem(image.name)
        if stem in names:
            ambiguous.add(stem)
        else:
            names[stem] = iid
    return {stem: iid for stem, iid in names.items() if stem not in ambiguous}


def validate_projection_dimensions(model, photo_sizes=None):
    """Source-photo observations require calibration in original photo pixels."""
    exact = {image.name: image for image in model.images.values()}
    for name, size in (photo_sizes or {}).items():
        image = exact.get(name)
        if image is None:
            continue
        camera = model.cameras[image.camera_id]
        if list(size) != [camera.width, camera.height]:
            raise ValueError(f"{name}: source photo is {size[0]}x{size[1]}, calibration is "
                             f"{camera.width}x{camera.height}. Re-align to restore original photo pixels "
                             "before measuring or optimizing markers.")


def projection_is_measured(value):
    """Pins and image-refined locations are measurements; predictions/unknowns are not."""
    return len(value) < 3 or bool(value[2]) or (len(value) > 3 and value[3] == "refined")


def marker_image_observations(model, projections, names=None, measured_only=False):
    """One finite observation per camera; prefer pins, reject conflicting equal-status aliases."""
    names = name_index(model) if names is None else names
    observations = {}
    for label, value in projections.items():
        if measured_only and not projection_is_measured(value):
            continue
        iid = names.get(_stem(label))
        if iid is None:
            continue
        uv = np.asarray(value[:2], float)
        if uv.shape != (2,) or not np.isfinite(uv).all():
            raise ValueError(f"Invalid marker observation on {label}")
        if measured_only and iid in model.images:
            camera = model.cameras[model.images[iid].camera_id]
            if not (0 <= uv[0] < camera.width and 0 <= uv[1] < camera.height):
                raise ValueError(f"Marker observation lies outside source photo {label}")
        pinned = len(value) < 3 or bool(value[2])
        if iid in observations:
            old, old_pin = observations[iid]
            if old_pin == pinned and not np.allclose(old, uv, rtol=0, atol=1e-7):
                raise ValueError(f"Conflicting marker observations for camera {iid}")
            if old_pin or not pinned:
                continue
        observations[iid] = (uv, pinned)
    return [(iid, float(uv[0]), float(uv[1])) for iid, (uv, _pin) in observations.items()]


def triangulate_marker(model, projections, names=None, refine=True, measured_only=False):
    """Marker position in the model frame from its photo projections."""
    names = names or name_index(model)
    C, D, obs = [], [], []
    for iid, x, y in marker_image_observations(model, projections, names, measured_only):
        im = model.images[iid]; cam = model.cameras[im.camera_id]
        xn, yn = cio.undistort_points(cam, np.array([[x, y]], float))
        d = im.R().T @ np.array([xn[0], yn[0], 1.0])
        C.append(im.center()); D.append(d / np.linalg.norm(d)); obs.append((iid, x, y))
    if len(C) < 2:
        return None, len(C)
    C, D = np.array(C), np.array(D)
    A = np.zeros((3, 3)); b = np.zeros(3)
    for c, d in zip(C, D):
        P = np.eye(3) - np.outer(d, d); A += P; b += P @ c
    if np.linalg.matrix_rank(A, tol=1e-10) < 3:
        return None, len(C)
    X = np.linalg.solve(A, b)
    if not np.isfinite(X).all():
        return None, len(C)
    if refine:
        for _ in range(5):          # Gauss-Newton on reprojection error
            J, r = [], []
            for iid, x, y in obs:
                im = model.images[iid]; cam = model.cameras[im.camera_id]; R = im.R()
                f = lambda P: cio.project(cam, R, im.tvec, P[None])[0][0]
                p0 = f(X); r.append(p0 - [x, y])
                eps = 1e-6 * max(1.0, np.abs(X).max())
                J.append(np.stack([(f(X + eps * e) - p0) / eps for e in np.eye(3)], 1))
            J = np.vstack(J); r = np.concatenate(r)
            dx = np.linalg.lstsq(J, -r, rcond=None)[0]
            X = X + dx
            if np.linalg.norm(dx) < 1e-9 * max(1, np.abs(X).max()):
                break
    if not np.isfinite(X).all() or any(
            (model.images[iid].R() @ X + model.images[iid].tvec)[2] <= 0 for iid, _x, _y in obs):
        return None, len(C)
    return X, len(C)


def marker_observation_diagnostic(model, marker, names=None):
    """3D estimate and RMS image-vector residual, counting each camera once."""
    names = name_index(model) if names is None else names
    X, _n = triangulate_marker(model, marker.projections, names, measured_only=True)
    if X is None:
        return None, None, 0
    residuals = []
    observations = marker_image_observations(model, marker.projections, names, measured_only=True)
    for iid, x, y in observations:
        image = model.images[iid]
        uv, depth = cio.project(model.cameras[image.camera_id], image.R(), image.tvec, X[None])
        if depth[0] <= 0 or not np.isfinite(uv).all():
            return None, None, len(observations)
        residuals.append(float(np.sum((uv[0]-[x,y])**2)))
    return X, float(np.sqrt(np.mean(residuals))) if residuals else None, len(observations)


def marker_diagnostics(model, markers, crs, offset=None, zone_hint=None, cache=None):
    """Current residuals without editing reference XYZ; caller owns cache model identity."""
    offset = np.asarray(offset if offset is not None else [0,0,0], float)
    names = name_index(model)
    estimates, pixels, counts = {}, {}, {}
    cache = {} if cache is None else cache
    for marker in markers:
        if marker.disabled:
            continue
        key = (marker.label, json.dumps(marker.projections, sort_keys=True))
        if key not in cache:
            try:
                cache[key] = marker_observation_diagnostic(model, marker, names)
            except (ValueError, np.linalg.LinAlgError):
                # An invalid diagnostic is unavailable, never a zero or stale error.
                cache[key] = (None, None, 0)
        X, pixel, count = cache[key]
        if X is None:
            continue
        estimates[marker.label] = X + offset
        pixels[marker.label], counts[marker.label] = pixel, count
    metric = lambda value: crs.to_metric(np.atleast_2d(value), zone_hint)[0]
    rows = marker_errors([marker for marker in markers if not marker.disabled], metric, estimates)
    for row in rows:
        row["pix"] = pixels.get(row["label"])
        row["n"] = counts.get(row["label"], 0)
    return estimates, pixels, counts, rows


def predict_projection(model, iid, X):
    """Pixel position of model-frame point X in image iid (None if behind/outside)."""
    im = model.images[iid]; cam = model.cameras[im.camera_id]
    uv, z = cio.project(cam, im.R(), im.tvec, np.asarray(X, float)[None])
    u, v = uv[0]
    if z[0] <= 0 or not (0 <= u < cam.width and 0 <= v < cam.height):
        return None
    return float(u), float(v)


# ======================================================== bundle adjustment
def _skew_rows(v):
    """(n,3) -> (n,3,3) cross-product matrices."""
    z = np.zeros(len(v))
    return np.stack([np.stack([z, -v[:, 2], v[:, 1]], 1),
                     np.stack([v[:, 2], z, -v[:, 0]], 1),
                     np.stack([-v[:, 1], v[:, 0], z], 1)], 1)


def gcp_bundle_adjust(model, markers_model_obs, control, opts=None, log=print, cam_priors=None):
    """GCP-constrained bundle adjustment (Levenberg-Marquardt with a Schur
    complement on the points, analytic pose/point Jacobians).

    model              COLMAP model already in the world (metric, offset) frame
    markers_model_obs  {label: (X0 (3,), [(image_id, x, y), ...])}
    control            {label: (ref (3,), sigma (3,))}  - control points only
    cam_priors         {image_id: (C_gps (3,), sigma (3,))} or None
    opts: tie_points (40000), tie_accuracy (px), projection_accuracy (px),
          fit_intrinsics (True) / intrinsics (model-specific fit preset),
          max_iterations (30), huber (robust threshold in sigmas)
    Updates model poses/intrinsics in place and re-triangulates all tie points.
    Returns {"markers": {label: X}, "tie_rms_px", "iterations"}.
    """
    import scipy.sparse as sp
    from scipy.linalg import cho_factor, cho_solve
    from scipy.spatial.transform import Rotation
    o = {"tie_points": 40000, "tie_accuracy": 1.0, "projection_accuracy": 0.5,
         "fit_intrinsics": True, "intrinsics": "f,cx,cy,k1-k3,p1,p2", "max_iterations": 30,
         "huber": 4.0}
    o.update(opts or {})
    for key in ("tie_accuracy", "projection_accuracy", "huber"):
        if not np.isfinite(o[key]) or o[key] <= 0:
            raise ValueError(f"{key} must be finite and positive")
    for references in (control, cam_priors or {}):
        for label, (position, sigma) in references.items():
            position, sigma = np.asarray(position, float), np.asarray(sigma, float)
            if position.shape != (3,) or sigma.shape != (3,) or not np.isfinite(position).all() or not np.isfinite(sigma).all() or np.any(sigma <= 0):
                raise ValueError(f"Invalid coordinate/accuracy for reference {label}")
    P = model.points
    img_ids = sorted(model.images)
    ipos = {iid: k for k, iid in enumerate(img_ids)}
    cam_ids = sorted(model.cameras)
    cpos = {cid: k for k, cid in enumerate(cam_ids)}
    R = np.array([model.images[i].R() for i in img_ids])
    C = np.array([model.images[i].center() for i in img_ids])
    from .calibration import pack_calibrations, project_calibrations, apply_increment
    K, camera_models, kidx, kactive = pack_calibrations(
        [model.cameras[c] for c in cam_ids], o["intrinsics"] if o["fit_intrinsics"] else "none")
    nk = kidx.shape[1]
    cam_of_img = np.array([cpos[model.images[i].camera_id] for i in img_ids])
    # ---- tie point subset (well observed, low error)
    tl = P.track_len()
    good = np.flatnonzero((tl >= 3) & (P.error < 1.5))
    if len(good) < 100:
        good = np.flatnonzero(tl >= 2)
    rng = np.random.default_rng(0)
    sel = np.sort(rng.choice(good, min(int(o["tie_points"]), len(good)), replace=False))
    sub = P.subset(sel)
    t_pt = np.repeat(np.arange(len(sub)), sub.track_len())
    t_img = np.array([ipos[int(i)] for i in sub.track_img], int)
    t_uv = np.array([model.images[int(i)].xys[j] for i, j in zip(sub.track_img, sub.track_idx)]).reshape(-1, 2)
    # ---- markers are extra points (index nT + k) with their own projection sigma
    mlabels = list(markers_model_obs)
    m_pt, m_img, m_uv = [], [], []
    for k, l in enumerate(mlabels):
        for iid, x, y in markers_model_obs[l][1]:
            if iid in ipos:
                m_pt.append(k); m_img.append(ipos[iid]); m_uv.append((x, y))
    nI, nC, nT, nM = len(img_ids), len(cam_ids), len(sub), len(mlabels)
    X = np.vstack([sub.xyz, np.array([markers_model_obs[l][0] for l in mlabels]).reshape(-1, 3)])
    o_pt = np.r_[t_pt, nT + np.array(m_pt, int)].astype(int)
    o_img = np.r_[t_img, np.array(m_img, int)].astype(int)
    o_uv = np.vstack([t_uv, np.array(m_uv, float).reshape(-1, 2)])
    o_sig = np.r_[np.full(len(t_pt), float(o["tie_accuracy"])),
                  np.full(len(m_pt), float(o["projection_accuracy"]))]
    nO, nP = len(o_pt), nT + nM
    # robust (Huber) weighting only for automatic tie points; marker projections
    # are user-placed and must keep their full weight, otherwise a deformed
    # block can't be pulled onto the control points
    o_huber = np.r_[np.full(len(t_pt), float(o["huber"])), np.full(len(m_pt), np.inf)]
    ctrl = [(nT + mlabels.index(l), np.asarray(r, float), np.asarray(s, float))
            for l, (r, s) in control.items() if l in mlabels]
    priors = [(ipos[i], np.asarray(c, float), np.asarray(s, float))
              for i, (c, s) in (cam_priors or {}).items() if i in ipos]
    n_cam = 6 * nI + nk * nC                     # reduced (camera side) system size
    log(f"GCP bundle adjustment: {nI} cameras, {nC} camera group(s), {nT:,} tie points "
        f"({len(t_pt):,} projections), {nM} markers ({len(m_pt)} projections, {len(ctrl)} control), "
        f"{len(priors)} camera GPS priors, intrinsics: {o['intrinsics'] if nk else 'fixed'}")

    observation_models = camera_models[cam_of_img[o_img]]

    def residuals(R, C, K, X):
        Xc = np.einsum("nij,nj->ni", R[o_img], X[o_pt] - C[o_img])
        r = (project_calibrations(K[cam_of_img[o_img]], observation_models, Xc) - o_uv) / o_sig[:, None]
        return r, Xc

    def cost(R, C, K, X):
        if not np.isfinite(K).all() or np.any(K[:, 0] <= 0) or np.any(
                K[~np.isin(camera_models, [0,2,3]), 1] <= 0):
            return float("inf")
        r, Xc = residuals(R, C, K, X)
        e = np.sqrt((r ** 2).sum(1))
        hh = np.minimum(o_huber, e)
        rho = 2 * hh * e - hh * hh                                 # Huber (tie points only)
        rho[Xc[:, 2] <= 0] = 1e6
        if not np.isfinite(rho).all():
            return float("inf")
        c = rho.sum()
        for p, ref, s in ctrl:
            c += (((X[p] - ref) / s) ** 2).sum()
        for i, cg, s in priors:
            c += (((C[i] - cg) / s) ** 2).sum()
        return 0.5 * c

    # sparse index structure (fixed): observation o -> camera-side columns, point
    ocols = np.hstack([6 * o_img[:, None] + np.arange(6),
                       6 * nI + nk * cam_of_img[o_img][:, None] + np.arange(nk)]).astype(np.int64)
    nb = ocols.shape[1]
    lam = 1e-3
    why = ""
    t_start = time.perf_counter()
    cur = cost(R, C, K, X)
    if not np.isfinite(cur):
        raise ValueError("Initial bundle residuals are non-finite; check observations and calibration")
    c0 = cur
    it = 0
    for it in range(1, int(o["max_iterations"]) + 1):
        r, Xc = residuals(R, C, K, X)
        Kobs = K[cam_of_img[o_img]]
        # d(uv)/d(Xc) by central differences (3 evals), d(uv)/dK (nk evals)
        h = 1e-6 * np.maximum(np.abs(Xc[:, 2]), 1e-6)
        Jxc = np.empty((nO, 2, 3))
        for j in range(3):
            d = np.zeros_like(Xc); d[:, j] = h
            Jxc[:, :, j] = (project_calibrations(Kobs, observation_models, Xc + d) - project_calibrations(Kobs, observation_models, Xc - d)) / (2 * h[:, None])
        Jk = np.empty((nO, 2, nk))
        for a in range(nk):
            selected = kidx[cam_of_img[o_img], a]
            enabled = kactive[cam_of_img[o_img], a]
            rows = np.arange(nO)
            hk = np.maximum(1e-7, 1e-6 * np.abs(Kobs[rows, selected]))
            Kp = Kobs.copy(); Kp[rows, selected] += hk * enabled
            Km = Kobs.copy(); Km[rows, selected] -= hk * enabled
            Jk[:, :, a] = (project_calibrations(Kp, observation_models, Xc) -
                           project_calibrations(Km, observation_models, Xc)) / (2 * hk[:, None])
        Ro = R[o_img]
        # Xc = R (X - C); perturb R <- Exp(w) R:  dXc/dw = -[Xc]x ; dXc/dC = -R ; dXc/dX = R
        Jw = -np.einsum("nij,njk->nik", Jxc, _skew_rows(Xc))
        JC = -np.einsum("nij,njk->nik", Jxc, Ro)
        JX = np.einsum("nij,njk->nik", Jxc, Ro)
        A = np.concatenate([Jw, JC, Jk], 2) / o_sig[:, None, None]       # (nO, 2, nb)
        B = JX / o_sig[:, None, None]                                     # (nO, 2, 3)
        # IRLS Huber weights
        e = np.sqrt((r ** 2).sum(1))
        wgt = np.minimum(1.0, o_huber / np.maximum(e, 1e-12))
        wgt[Xc[:, 2] <= 0] = 0
        sw = np.sqrt(wgt)[:, None, None]
        A = A * sw; B = B * sw; rw = r * sw[:, :, 0]
        # ---- normal equations
        # U (camera side): dense n_cam x n_cam
        AtA = np.einsum("nki,nkj->nij", A, A)                             # (nO, nb, nb)
        U = sp.coo_matrix((AtA.ravel(), (np.repeat(ocols, nb, 1).ravel(), np.tile(ocols, (1, nb)).ravel())),
                          shape=(n_cam, n_cam)).toarray()
        gc = np.zeros(n_cam)
        np.add.at(gc, ocols.ravel(), -np.einsum("nki,nk->ni", A, rw).ravel())
        # V (point blocks) and gp
        BtB = np.einsum("nki,nkj->nij", B, B)
        V = np.zeros((nP, 3, 3)); np.add.at(V, o_pt, BtB)
        gp = np.zeros((nP, 3)); np.add.at(gp, o_pt, -np.einsum("nki,nk->ni", B, rw))
        for p, ref, s in ctrl:
            V[p] += np.diag(1 / s ** 2); gp[p] -= (X[p] - ref) / s ** 2
        for i, cg, s in priors:
            for j in range(3):
                q = 6 * i + 3 + j
                U[q, q] += 1 / s[j] ** 2; gc[q] -= (C[i, j] - cg[j]) / s[j] ** 2
        # W (camera side x points), per observation block A^T B
        AtB = np.einsum("nki,nkj->nij", A, B)                             # (nO, nb, 3)
        Wrows = np.repeat(ocols, 3, 1).ravel()
        Wcols = (3 * o_pt[:, None, None] + np.arange(3)[None, None, :]).repeat(nb, 1).ravel()
        W = sp.csr_matrix((AtB.ravel(), (Wrows, Wcols)), shape=(n_cam, 3 * nP))
        accepted = False
        for _ in range(10):
            Ud = U + lam * np.diag(np.maximum(np.diag(U), 1e-9))
            Vd = V + lam * np.einsum("nii->ni", V)[:, :, None] * np.eye(3)
            Vd += 1e-12 * np.eye(3)
            Vinv = np.linalg.inv(Vd)
            Vi = _block_diag_csr(Vinv)
            WVi = W @ Vi
            S = Ud - (WVi @ W.T).toarray()
            rhs = gc - WVi @ gp.ravel()
            try:
                dc = cho_solve(cho_factor(S, check_finite=False), rhs, check_finite=False)
            except np.linalg.LinAlgError:
                lam *= 10; continue
            dp = np.einsum("nij,nj->ni", Vinv, gp - (W.T @ dc).reshape(nP, 3))
            dw = dc[:6 * nI].reshape(nI, 6)
            Rn = Rotation.from_rotvec(dw[:, :3]).as_matrix() @ R
            Cn = C + dw[:, 3:]
            Kn = K.copy()
            if nk:
                Kn = apply_increment(K, kidx, kactive, dc[6 * nI:].reshape(nC, nk))
            Xn = X + dp
            new = cost(Rn, Cn, Kn, Xn)
            if new < cur:
                rel = (cur - new) / max(cur, 1e-30)
                R, C, K, X, cur = Rn, Cn, Kn, Xn, new
                lam = max(lam / 3, 1e-7); accepted = True
                break
            lam *= 10
        if o.get("verbose"):
            log(f"    it {it}: cost {cur:.6g} lambda {lam:.1e} {'accepted' if accepted else 'rejected'}")
        if not accepted or rel < 1e-7:
            why = "no decrease" if not accepted else "converged"
            break
    else:
        why = "max iterations"
    log(f"  stopped: {why}")
    rr, _ = residuals(R, C, K, X)
    nt = len(t_pt)
    log(f"  chi2: tie projections {np.sum(rr[:nt] ** 2):.4g} (n={nt}), marker projections "
        f"{np.sum(rr[nt:] ** 2):.4g} (n={nO - nt}), control coordinates "
        f"{sum((((X[p] - ref) / s_) ** 2).sum() for p, ref, s_ in ctrl):.4g} (n={len(ctrl)})")
    log(f"  cost {c0:.4g} -> {cur:.4g} in {it} LM iterations, {time.perf_counter() - t_start:.1f} s")
    # ---- write back
    for k, iid in enumerate(img_ids):
        im = model.images[iid]
        im.qvec = cio.rot_to_qvec(R[k]); im.tvec = -R[k] @ C[k]
    if nk:
        for k, cid in enumerate(cam_ids):
            size = cio.CAMERA_MODELS[model.cameras[cid].model][1]
            model.cameras[cid].params = K[k, :size].copy()
    retriangulate(model)
    r, _ = residuals(R, C, K, X)
    final_errors, _, _ = cio.observation_errors(model)
    return {"markers": {l: X[nT + k] for k, l in enumerate(mlabels)},
            "tie_rms_px": float(np.sqrt(np.mean(final_errors ** 2))) if len(final_errors) else 0.0,
            "iterations": it, "intrinsics": {cid: K[k].tolist() for k, cid in enumerate(cam_ids)}}


def _block_diag_csr(blocks):
    """(n,3,3) -> sparse block-diagonal (3n x 3n)."""
    import scipy.sparse as sp
    n = len(blocks)
    rows = (3 * np.arange(n)[:, None, None] + np.arange(3)[None, :, None]).repeat(3, 2)
    cols = (3 * np.arange(n)[:, None, None] + np.arange(3)[None, None, :]).repeat(3, 1)
    return sp.csr_matrix((blocks.ravel(), (rows.ravel(), cols.ravel())), shape=(3 * n, 3 * n))


def retriangulate(model, min_angle_deg=0.5):
    """Re-triangulate all tie points from their tracks with the current cameras
    (linear least squares on rays) and update their mean reprojection error."""
    P = model.points
    tl = P.track_len()
    pidx = np.repeat(np.arange(len(P)), tl)
    imgs = P.track_img.astype(np.int64)
    D = np.empty((len(pidx), 3)); Cc = np.empty((len(pidx), 3))
    for iid, im in model.images.items():
        sel = np.flatnonzero(imgs == iid)
        if not len(sel):
            continue
        cam = model.cameras[im.camera_id]
        xn, yn = cio.undistort_points(cam, im.xys[P.track_idx[sel]])
        d = np.column_stack([xn, yn, np.ones_like(xn)]) @ im.R()
        D[sel] = d / np.linalg.norm(d, axis=1, keepdims=True); Cc[sel] = im.center()
    Pm = np.eye(3)[None] - D[:, :, None] * D[:, None, :]
    A = np.zeros((len(P), 3, 3)); b = np.zeros((len(P), 3))
    np.add.at(A, pidx, Pm); np.add.at(b, pidx, np.einsum("nij,nj->ni", Pm, Cc))
    ok = np.linalg.det(A) > 1e-12
    X = P.xyz.copy()
    X[ok] = np.linalg.solve(A[ok], b[ok][..., None])[..., 0]
    P.xyz = X
    errs, _, pid = cio.observation_errors(model)
    s = np.zeros(len(P)); np.add.at(s, pid, errs)
    P.error = s / np.maximum(tl, 1)
    return model


# ================================================================ report
def marker_errors(markers, crs_metric_of, est_world):
    """Rows: label, type, ref, est, dX, dY, dZ, total (m)."""
    rows = []
    for m in markers:
        if m.ref is None or m.label not in est_world:
            continue
        ref = crs_metric_of(m.ref); e = est_world[m.label]
        d = e - ref
        rows.append({"label": m.label, "type": "control" if m.enabled else "check",
                     "ref": ref.tolist(), "est": e.tolist(), "dx": d[0], "dy": d[1], "dz": d[2],
                     "total": float(np.linalg.norm(d))})
    return rows


def rmse(rows, kind):
    r = [x for x in rows if x["type"] == kind]
    if not r:
        return None
    a = np.array([[x["dx"], x["dy"], x["dz"]] for x in r])
    q = np.sqrt((a ** 2).mean(0))
    return {"n": len(r), "x": q[0], "y": q[1], "z": q[2], "xy": float(np.hypot(q[0], q[1])),
            "total": float(np.sqrt((a ** 2).sum(1).mean()))}


def write_report(path, rows, crs, pixel=None, counts=None):
    """Reference-pane style tab-separated export (+ pixel error and type)."""
    if pixel is None:
        pixel = {row["label"]: row.get("pix") for row in rows}
    if counts is None:
        counts = {row["label"]: row.get("n", 0) for row in rows}
    pixel = {key: value for key, value in pixel.items() if value is not None}
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(f"# CoordinateSystem: {crs.name}\n")
        f.write("#Label\tType\tX\tY\tZ\tError_(m)\tX_error\tY_error\tZ_error\tX_est\tY_est\tZ_est\t"
                "Error_(pix)\tProjections\n")
        for r in rows:
            f.write("\t".join([r["label"], r["type"], *(f"{v:.6f}" for v in r["ref"]), f"{r['total']:.6f}",
                               f"{r['dx']:.6f}", f"{r['dy']:.6f}", f"{r['dz']:.6f}",
                               *(f"{v:.6f}" for v in r["est"]),
                               f"{pixel.get(r['label'], float('nan')):.3f}", str(counts.get(r["label"], 0))]) + "\n")
        for kind in ("control", "check"):
            q = rmse(rows, kind)
            if q:
                f.write(f"#{kind.capitalize()} points RMSE (n={q['n']})\t\t\t\t\t{q['total']:.6f}\t"
                        f"{q['x']:.6f}\t{q['y']:.6f}\t{q['z']:.6f}\n")



def valid_gps(xyz):
    try:
        values=np.asarray(xyz,float)
    except (TypeError,ValueError):
        return None
    if values.shape!=(3,) or not np.isfinite(values).all() or abs(values[0])>180 or not -80<=values[1]<=84:
        return None
    return values


def geographic_zone(xyz):
    values=np.asarray(xyz,float)
    if values.ndim!=2 or values.shape[1]!=3 or not len(values) or any(valid_gps(row) is None for row in values):
        raise ValueError("Geographic references require finite longitude/latitude/height within the supported UTM latitude range (-80 to 84 degrees)")
    longitude=np.radians(values[:,0])
    center=float(np.arctan2(np.sin(longitude).mean(),np.cos(longitude).mean()))
    delta=np.angle(np.exp(1j*(longitude-center)))
    if np.max(np.abs(np.degrees(delta)))>6:
        raise ValueError("Geographic references span incompatible projection regions; check GPS outliers or process one survey area")
    latitude=float(values[:,1].mean())
    return utm_zone(math.degrees(center),latitude),latitude<0


def camera_gps_metric(model, gps, crs, zone_hint=None):
    """EXIF GPS is lon/lat/alt, including when the project CRS is UTM."""
    if crs.kind == "local":
        return {}
    exact = {image.name: iid for iid, image in model.images.items()}
    by_stem = {}
    for iid, image in model.images.items():
        by_stem.setdefault(_stem(image.name), []).append(iid)
    out = {}
    for label, xyz in (gps or {}).items():
        iid = exact.get(label)
        if iid is None:
            candidates = by_stem.get(_stem(label), [])
            iid = candidates[0] if len(candidates) == 1 else None
        if iid is None or len(xyz) != 3 or any(v is None for v in xyz):
            continue
        values=valid_gps(xyz)
        if values is None:
            continue
        lon,lat,alt=values
        if crs.kind == "utm":
            E, N = utm_forward(lat, lon, crs.zone, crs.south)
            out[iid] = np.array([E, N, alt], float)
        else:
            out[iid] = crs.to_metric(np.array([[lon, lat, alt]]), zone_hint)[0]
    return out


def reference_status(model, markers, crs, gps=None):
    """Count usable controls, not merely imported coordinate rows."""
    names = name_index(model)
    refs = [m for m in markers if m.enabled and not m.disabled and m.ref is not None]
    usable = 0
    for m in refs:
        X, n = triangulate_marker(model, m.projections, names, measured_only=True)
        if X is not None and n >= 2:
            usable += 1
    return {"imported": len(markers), "references": len(refs), "usable": usable,
            "gps": len(camera_gps_metric(model, gps, crs))}


def run_local_task(cfg, log=print):
    """Adjust without survey constraints; restore the first pose and baseline.

    The similarity gauge is anchored to the first input camera and its longest
    original baseline. No CRS or metric scale is invented. Dense products must
    be rebuilt after camera edits.
    """
    import shutil
    t0 = time.perf_counter()
    if not cfg.get("bundle", True):
        raise ValueError("Enable bundle adjustment for optimization without reference coordinates.")
    mdir = cfg["model"]
    model = cio.read_model(mdir)
    validate_projection_dimensions(model, cfg.get("photo_sizes"))
    ids = sorted(model.images)
    if len(ids) < 2 or not np.any(model.points.track_len() >= 2):
        raise ValueError("Local optimization needs two aligned cameras and tracked tie points.")
    first = ids[0]
    C0, R0 = model.images[first].center().copy(), model.images[first].R().copy()
    other = max(ids[1:], key=lambda i: np.linalg.norm(model.images[i].center() - C0))
    baseline = float(np.linalg.norm(model.images[other].center() - C0))
    if baseline <= 1e-10:
        raise ValueError("Local optimization needs cameras with a nonzero baseline.")
    names = name_index(model)
    markers = [Marker(**m) for m in cfg.get("markers", []) if not m.get("disabled", False)]
    obs = {}
    for m in markers:
        if not cfg.get("use_markers", True) or not m.enabled:
            continue
        X, _n = triangulate_marker(model, m.projections, names, measured_only=True)
        if X is not None:
            obs[m.label] = (X, marker_image_observations(model, m.projections, names, measured_only=True))
    acc = dict(DEFAULTS); acc.update(cfg.get("accuracies") or {})
    stats = gcp_bundle_adjust(model, obs, {}, {
        "tie_points": cfg.get("tie_points", 40000), "tie_accuracy": acc["tie_accuracy"],
        "projection_accuracy": acc["projection_accuracy"],
        "fit_intrinsics": cfg.get("fit_intrinsics", True),
        "max_iterations": cfg.get("max_iterations", 30)}, log=log)
    Cn = model.images[first].center()
    length = float(np.linalg.norm(model.images[other].center() - Cn))
    if length <= 1e-10 or not np.isfinite(length):
        raise ValueError("Optimization produced a degenerate baseline; original model retained.")
    R = R0.T @ model.images[first].R()
    scale = baseline / length
    transform_model(model, scale, R, C0 - scale * R @ Cn)
    offset = np.asarray(cfg.get("offset") or [0, 0, 0], float)
    est = {}
    for m in markers:
        try:
            X, pixel, n = marker_observation_diagnostic(model, m)
        except (ValueError, np.linalg.LinAlgError) as error:
            log(f"Marker {m.label}: residual unavailable ({error})")
            X, pixel, n = None, None, 0
        est[m.label] = {"est": (X + offset).tolist() if X is not None else None, "n": n, "pix": pixel}
    backup = mdir.rstrip("/\\") + "_original"
    if not os.path.isdir(backup):
        shutil.copytree(mdir, backup)
    stage = mdir.rstrip("/\\") + "_optimize_tmp"
    try:
        shutil.rmtree(stage, ignore_errors=True)
        cio.write_model(stage, model)
        from .workflow import publish_outputs
        publish_outputs([(stage,mdir)])
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    out = {"local_only": True, "similarity": None, "markers": est,
           "bundle": {k: v for k, v in stats.items() if k != "markers"},
           "seconds": time.perf_counter() - t0}
    if cfg.get("result"):
        with open(cfg["result"], "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=float)
    log(f"Reference use: marker image observations={len(obs)}, marker XYZ controls=0, camera GPS=0.")
    log("Cameras optimized in the existing frame; no georeferencing was performed. "
        "Rebuild dense products to use the optimized cameras.")
    return out


# ============================================================ the task
def run_task(cfg, log=print):
    """Optimize Cameras / georeference (child-process task).

    cfg: model (dir, rewritten in place, original kept in <model>_original),
         markers (list of Marker dicts), crs (text), camera_gps
         {photo label: [lon, lat, alt]} (optional), use_markers, use_cameras,
         accuracies (DEFAULTS keys), bundle (bool), tie_points, fit_intrinsics,
         report (path), result (json path), offset (optional [3]),
         transform_files [list of ply paths to transform with the similarity]
    """
    if cfg.get("local_only"):
        return run_local_task(cfg, log)
    import shutil
    import time
    t0 = time.perf_counter()
    acc = dict(DEFAULTS); acc.update(cfg.get("accuracies") or {})
    mdir = cfg["model"]
    backup = mdir.rstrip("/\\") + "_original"
    if not os.path.isdir(backup):
        shutil.copytree(mdir, backup)
    model = cio.read_model(mdir)
    validate_projection_dimensions(model, cfg.get("photo_sizes"))
    crs = CRS.parse(cfg.get("crs", ""))
    markers = [Marker(**m) for m in cfg.get("markers", []) if not m.get("disabled", False)]
    names = name_index(model)
    # Camera references outside the aligned model must not select its map zone.
    gps={}
    exact_names = {image.name for image in model.images.values()}
    for label,value in (cfg.get("camera_gps") or {}).items():
        clean=valid_gps(value)
        if clean is not None and (label in exact_names or _stem(label) in names):
            gps[label]=clean.tolist()
    # ---- triangulate markers in the current model
    tri = {}
    for m in markers:
        if not cfg.get("use_markers", True) or not m.enabled:
            continue
        X, n = triangulate_marker(model, m.projections, names, measured_only=True)
        if X is not None:
            tri[m.label] = X
    control = [m for m in markers if m.enabled and m.ref is not None and m.label in tri]
    log(f"Markers: {len(markers)} imported, {len(tri)} with >=2 projections on aligned photos, "
        f"{len(control)} control, {sum(1 for m in markers if not m.enabled and m.label in tri)} check")
    # ---- initial similarity
    zone_hint=None
    if crs.kind=="wgs84":
        references=[m.ref for m in control] if cfg.get("use_markers",True) and len(control)>=3 else list(gps.values())
        if references: zone_hint=geographic_zone(references)
    metric = lambda xyz: crs.to_metric(np.atleast_2d(xyz),zone_hint)[0]
    cam_gps = camera_gps_metric(model, gps, crs, zone_hint) if cfg.get("use_cameras") else {}
    use_markers = cfg.get("use_markers", True)
    if use_markers and len(control) >= 3:
        src = np.array([tri[m.label] for m in control]); dst = np.array([metric(m.ref) for m in control])
        what = "control markers"
    elif len(cam_gps) >= 3:
        ids = sorted(cam_gps)
        src = np.array([model.images[i].center() for i in ids]); dst = np.array([cam_gps[i] for i in ids])
        what = "camera GPS"
    else:
        refs = sum(m.enabled and m.ref is not None for m in markers)
        raise ValueError(f"Cannot georeference: {len(markers)} markers imported, {refs} enabled with XYZ, "
                         f"{len(control)} triangulated controls, {len(cam_gps)} usable camera GPS positions. "
                         "Need 3 non-collinear controls with XYZ and placements on at least 2 aligned photos each, "
                         "or 3 camera GPS positions in a geographic/UTM CRS. "
                         "For optimization without georeferencing, use local-only bundle adjustment.")
    if min(np.linalg.matrix_rank(src - src.mean(0)), np.linalg.matrix_rank(dst - dst.mean(0))) < 2:
        raise ValueError("Reference positions are collinear; use at least 3 non-collinear control positions.")
    offset = np.asarray(cfg.get("offset") or np.round(dst.mean(0), -2), float)
    s, R, t, inl = robust_helmert(src, dst - offset)
    if what == "control markers" and inl.sum() < len(inl):
        bad = [control[i].label for i in np.flatnonzero(~inl)]
        log(f"Helmert: {len(bad)} control marker(s) look inconsistent (still used in BA with their accuracy): {', '.join(bad)}")
    res_h = np.linalg.norm(apply_sim((s, R, t), src) - (dst - offset), axis=1)
    log(f"Helmert fit to {what}: scale {s:.6g}, RMS {np.sqrt(np.mean(res_h ** 2)):.4f} m over {len(src)} points")
    transform_model(model, s, R, t)
    tri = {l: apply_sim((s, R, t), X) for l, X in tri.items()}
    # ---- bundle adjustment with GCPs
    stats = {}
    if cfg.get("bundle", True):
        obs = {}
        ctrl_labels = {m.label for m in control} if use_markers else set()
        for m in markers:
            if not cfg.get("use_markers", True) or m.label not in tri:
                continue
            # check points stay independent: their projections are not used in the adjustment
            if m.label not in ctrl_labels:
                continue
            o = marker_image_observations(model, m.projections, names, measured_only=True)
            obs[m.label] = (tri[m.label], o)
        ctrl = {}
        if use_markers:
            for m in control:
                a = m.acc or [acc["marker_accuracy"], acc["marker_accuracy_z"]]
                ctrl[m.label] = (metric(m.ref) - offset, [a[0], a[0], a[1]])
        pri = None
        if cam_gps and cfg.get("use_cameras"):
            pri = {i: (c - offset, [acc["camera_accuracy"]] * 2 + [acc["camera_accuracy_z"]])
                   for i, c in cam_gps.items()}
        stats = gcp_bundle_adjust(model, obs, ctrl, {"tie_points": cfg.get("tie_points", 40000),
                                                     "tie_accuracy": acc["tie_accuracy"],
                                                     "projection_accuracy": acc["projection_accuracy"],
                                                     "fit_intrinsics": cfg.get("fit_intrinsics", True),
                                                     "intrinsics": cfg.get("intrinsics", "f,cx,cy,k1-k3,p1,p2"),
                                                     "max_iterations": cfg.get("max_iterations", 30),
                                                     "verbose": cfg.get("verbose", False)},
                                  log=log, cam_priors=pri)
    log(f"Reference use: marker image observations={len(obs) if cfg.get('bundle', True) else 0}, "
        f"marker XYZ controls={len(control) if use_markers else 0}, camera GPS={len(cam_gps)}.")
    # ---- final marker estimates: re-triangulate with optimised cameras
    est, pix, cnt, rows = marker_diagnostics(model, markers, crs, offset, zone_hint)
    # ---- commit transactionally: build every output in temporary files first,
    # so a failure leaves the model AND the point cloud / mesh in the old frame
    M = sim_matrix(s, R, t)
    new_dir = mdir.rstrip("/\\") + "_georef_tmp"
    staged = []
    try:
        shutil.rmtree(new_dir, ignore_errors=True)
        cio.write_model(new_dir, model)
        for p in cfg.get("transform_files") or []:
            if p and os.path.exists(p):
                staged.append((transform_ply(p, M, out=p + ".georef_tmp"), p))
    except BaseException:
        shutil.rmtree(new_dir, ignore_errors=True)
        for tmp, _p in staged:
            if os.path.exists(tmp):
                os.remove(tmp)
        raise
    from .workflow import publish_outputs
    try:
        publish_outputs([(new_dir,mdir),*staged])
    finally:
        shutil.rmtree(new_dir,ignore_errors=True)
        for tmp,_ in staged:
            if os.path.isfile(tmp): os.remove(tmp)
    for _,p in staged:
        log(f"Transformed {os.path.basename(p)} into the georeferenced frame")
    errs, _, _ = cio.observation_errors(model)
    log(f"Tie points: {len(model.points):,}, reprojection RMS {np.sqrt(np.mean(errs ** 2)):.3f} px")
    for kind in ("control", "check"):
        q = rmse(rows, kind)
        if q:
            log(f"{kind.capitalize()} points RMSE (n={q['n']}): X {q['x']:.4f}  Y {q['y']:.4f}  "
                f"Z {q['z']:.4f}  XY {q['xy']:.4f}  total {q['total']:.4f} m")
    if cfg.get("report"):
        write_report(cfg["report"], rows, crs, pix, cnt)
    out = {"offset": offset.tolist(), "similarity": M.tolist(), "crs": crs.name, "crs_kind": crs.kind,
           "zone": zone_hint,
           "markers": {m.label: {"est": est[m.label].tolist() if m.label in est else None,
                                 "pix": pix.get(m.label), "n": cnt.get(m.label, 0)} for m in markers},
           "rows": rows, "control_rmse": rmse(rows, "control"), "check_rmse": rmse(rows, "check"),
           "bundle": {k: v for k, v in stats.items() if k != "markers"},
           "seconds": time.perf_counter() - t0}
    if cfg.get("result"):
        with open(cfg["result"], "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=float)
    log(f"Georeferencing done in {out['seconds']:.1f} s")
    return out


def replace_file(tmp, dst, attempts=20, delay=0.25):
    """os.replace with retries: on Windows the target can be briefly locked
    (viewer, antivirus, indexer). Raises the last error if it stays locked."""
    import time as _t
    for k in range(attempts):
        try:
            os.replace(tmp, dst)
            return
        except PermissionError:
            if k == attempts - 1:
                raise
            _t.sleep(delay)


def _ply_vertex_layout(fh):
    from .plyio import vertex_layout
    return vertex_layout(fh)


def _xform_vertices(v, R, t, Rn):
    X = np.column_stack([v["x"], v["y"], v["z"]]).astype(np.float64)
    Y = X @ R.T + t
    v["x"], v["y"], v["z"] = Y[:, 0], Y[:, 1], Y[:, 2]
    if "nx" in v.dtype.names:
        N = np.column_stack([v["nx"], v["ny"], v["nz"]]).astype(np.float64) @ Rn.T
        v["nx"], v["ny"], v["nz"] = N[:, 0], N[:, 1], N[:, 2]


def _reverse_winding_plyfile(ply):
    names = [e.name for e in ply.elements]
    if "face" not in names:
        return
    f = ply["face"].data
    key = "vertex_indices" if "vertex_indices" in f.dtype.names else f.dtype.names[0]
    col = f[key]
    if col.dtype == object:
        for k in range(len(col)):
            col[k] = np.ascontiguousarray(col[k][::-1])
    else:
        f[key] = col[:, ::-1]


def _reverse_winding_stream(src, dst, path, faces_at):
    """Copy the face element (next after the vertices) with reversed winding."""
    from .plyio import read_header
    pos = src.tell()
    src.seek(0)
    elems = read_header(src)[2]
    src.seek(pos)
    if len(elems) < 2 or elems[1][0] != "face":
        return
    _name, m, props = elems[1]
    if len(props) != 1 or props[0] is None or props[0][0] != "list":
        raise ValueError(f"{path}: cannot mirror faces with extra properties")
    cdt = np.dtype(props[0][2]); idt = np.dtype(props[0][3])
    done = 0
    while done < m:
        k = min(1_000_000, m - done)
        f = np.fromfile(src, dtype=[("n", cdt), ("i", idt, (3,))], count=k)
        if len(f) != k or (f["n"] != 3).any():
            raise ValueError(f"{path}: cannot mirror non-triangle faces")
        f["i"] = f["i"][:, ::-1]
        f.tofile(dst)
        done += k


def transform_ply(path, M, out=None, block_size=2_000_000):
    """Apply a 4x4 similarity to the vertices (and normals) of a PLY file.

    Never rewrites the file in place: the result goes to `out`, by default a
    temporary file next to it that then atomically replaces the original, so
    the original is never left half-written. The input is read with plain file
    I/O, not a memory map: on Windows a mapped file cannot be truncated or
    replaced, which made the old in-place rewrite fail with
    'OSError: [Errno 22] Invalid argument'. Binary PLYs are streamed in blocks
    of `block_size` vertices (bounded memory); the rest of the file (faces) is
    copied verbatim.

    A transform with a reflection (det < 0) also reverses the triangle winding
    (so face normals keep pointing outward/up) and maps the stored normals with
    the orthonormal part Q = R/|s|; the old R/cbrt(det) negated them, so both
    the stored and the winding normals pointed into the surface."""
    import shutil
    R = np.asarray(M, dtype=np.float64)[:3, :3]
    t = np.asarray(M, dtype=np.float64)[:3, 3]
    det = float(np.linalg.det(R))
    Rn = R / abs(np.cbrt(det))
    mirror = det < 0
    tmp = out or (path + ".georef_tmp")
    try:
        with open(path, "rb") as src:
            lay = _ply_vertex_layout(src)
            if lay is None:                       # ascii / unusual layout: plyfile, in memory
                from plyfile import PlyData
                src.seek(0)
                ply = PlyData.read(src, mmap=False)
                _xform_vertices(ply["vertex"].data, R, t, Rn)
                if mirror:
                    _reverse_winding_plyfile(ply)
                with open(tmp, "wb") as dst:
                    ply.write(dst)
                    dst.flush(); os.fsync(dst.fileno())
            else:
                head, dt, n = lay
                with open(tmp, "wb") as dst:
                    dst.write(head)
                    done = 0
                    while done < n:
                        k = min(block_size, n - done)
                        v = np.fromfile(src, dtype=dt, count=k)
                        if len(v) != k:
                            raise ValueError(f"{path}: truncated vertex data ({done + len(v)} of {n})")
                        _xform_vertices(v, R, t, Rn)
                        v.tofile(dst)
                        done += k
                    if mirror:
                        _reverse_winding_stream(src, dst, path, len(head) + dt.itemsize * n)
                    shutil.copyfileobj(src, dst, 16 << 20)        # faces etc., unchanged
                    dst.flush(); os.fsync(dst.fileno())
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    if out is None:
        replace_file(tmp, path)
    return tmp
