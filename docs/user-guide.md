# User guide

[Documentation](README.md) · [Installation](installation.md)

1. *Workflow → Add Photos…* / *Add Folder…* — photos are analysed in parallel
   (EXIF GPS, thumbnails, global descriptors) and appear in **Photos**,
   **Workspace** and **Reference** panes.
2. *Workflow → Align Photos…* — Accuracy, matching mode (**Fast** default /
   Exhaustive / Sequential), **camera estimation** (Auto / Global / Incremental /
   Hierarchical), coarse-to-fine, key point limit, guided matching…
   Result: camera positions + tie points in the **Model** view.
3. *Workflow → Build Point Cloud…* — Quality + Depth filtering (CUDA).
4. *Workflow → Build Model…* — Source (Depth maps / Point cloud),
   surface type, face count.
5. *File → Save* stores a `*.pmsx` project (JSON); results live in
   `<project>.files/`.

## Dense cloud, filtering, mesh and ground control

**Build Point Cloud** (Workflow menu) – own parallel undistortion (photos are read in
place and never written to; downscaled undistorted copies go to `<workdir>\dense`),
quality Ultra/High/Medium/Low/Lowest = 1/2/4/8/16× downscale, one undistorted
pinhole camera per camera group, PatchMatch neighbours chosen from the sparse model
(shared tie points × triangulation-angle weight, 8 per photo by default),
geometric consistency, depth filtering Disabled/Mild/Moderate/Aggressive mapped to
PatchMatch/fusion thresholds, then outlier filtering (minimum confidence = photos
per point, terrain sanity check, statistical and radius outlier removal; scipy
cKDTree, multi-threaded). Depth maps can be reused when the settings are unchanged.

**Tools > Point Cloud > Filter Point Cloud / Filter by Confidence**, **Model >
Gradual Selection** (tie points: reprojection error, reconstruction uncertainty,
image count, projection accuracy).

**Build Model** – Poisson (Open3D) with density trimming (Interpolation
Disabled/Enabled/Extrapolated), or Delaunay from the depth maps; face count
High/Medium/Low (points/5, /15, /45 as in Metashape) or Custom, quadric decimation,
removal of faces bridging gaps, long-edge faces and small components; automatic
voxel downsampling above 12 M points so big clouds fit in RAM.

**Ground control** – File > Import > Import Markers / Import Reference reads
Metashape reference exports (`# CoordinateSystem:` + `#Label X Y Z ...`, as
exported by Metashape), plain label/X/Y/Z[/accuracy] text or CSV, Metashape
markers XML (with photo projections and pinned flags) and survey XML.
Coordinate systems: local (metres), WGS84 lon/lat/alt and UTM (own conversion,
no PROJ data needed). The **Markers** pane lists reference, error (m), projections and
pixel error; the check box switches control ↔ check point. In the Photo view,
right-click to place the selected marker or edit an existing marker. **Tools > Markers > Refine Markers** predicts every marker in every photo and
refines it locally (template from a pinned placement, else a checkerboard-corner
detector, multi-view consensus). **Tools > Optimize Cameras** runs a robust Helmert
fit followed by a GCP-constrained bundle adjustment (Levenberg–Marquardt with Schur
complement: poses, f/cx/cy/k1-k3/p1/p2 per camera group, tie points, markers;
accuracies as in Metashape: markers 0.005 m, projections 0.5 px, tie points 1 px,
camera GPS 10 m). Check points are not used in the adjustment. The report
(File > Export > Export Markers) contains X/Y/Z/total error and pixel error per
marker and the control/check RMSE.

## Texture and tiled model

**Workflow → Build Texture** (Diffuse map from Images). Mapping mode Generic /
Adaptive orthophoto / Orthophoto / Keep uv; blending Mosaic (default) / Average /
Max intensity / Min intensity / Disabled; texture size × count (count is an upper
bound: pages are never filled with texels upsampled past the photo resolution);
hole filling; ghosting filter; photos at working resolution (≤ 2640 px, fast) or
full resolution.

How it works (own code): the original photos are used with the current aligned
cameras (full COLMAP distortion model, any number of sensors). Every face is
ray-cast (Embree) against every camera that can see it, and scored by projected
area × viewing angle × distance to the image border × photo sharpness, top 10 views
per face. Exposure differences between photos are equalised (log-space least
squares), the ghosting filter drops views whose colour differs strongly from the
per-face median (moving vehicles, people), view selection is a smoothness-weighted
labelling (few seams), seams are levelled by per-vertex colour offsets, faces no
photo sees are filled from neighbouring colours. Charts are packed into the
atlas and sampled multithreaded. Visibility is cached (`visibility_cache.npz`), so
re-texturing with other settings is ~40 % faster.

Output in `<project>.files/…/texture/`: `model_textured.obj/.mtl`, `texture_N.jpg`,
`model_textured.glb`, `uv.npz`, `info.json`. The workspace row reads
`3D Model (N faces, …, Texture 8192x8192)`; Properties lists texel size vs photo
ground resolution (cm/pix when the chunk is georeferenced, model units otherwise).

**Workflow → Build Tiled Model** from the model (with its texture, or vertex colours)
or from the point cloud. Adaptive quadtree on the ground plane (z when georeferenced,
otherwise the mean camera up direction), leaves keep every original face, parents
are quadric-decimated with locked borders; every tile has its own atlas baked from
the full model. Output `tiled/`: Cesium 3D Tiles `tileset.json` + `tiles/*.b3dm`
(or `.glb` for 3D Tiles 1.1, `.pnts` for point clouds) and `photomesh_tiles.json`
for our viewer, which streams levels by screen-space error (16 px). Georeferenced
UTM/WGS84 chunks get an ENU→ECEF root transform (Cesium places them on the globe);
local-CRS chunks are written in local metres.

**File → Import → Import Texture… / Import Tiled Model…** attach an existing output
folder without rebuilding (e.g. a texture built from the command line or copied from
another PC). Import Texture needs the folder with `info.json`, `uv.npz` and
`texture_N.jpg` and refuses a texture of a different mesh (face count must match);
Import Tiled Model needs the folder with `tileset.json` + `photomesh_tiles.json`.
Paths are stored in the `.pmsx` on the next Save.

Real project (641 DJI photos, 1.85 M faces, RTX 3080 laptop): texture 8192×1 167 s
(25.7 cm texel – a 1.5 km² site needs more pages: 8192×4 = 12.9 cm, 157 s);
tiled model 45 s (106 tiles, 5 levels); point-cloud tiles from 27.8 M points 12 s.

## Export mesh contours to DXF

After building a model, choose **File > Export > Export Mesh Contours...**,
next to Export Model. Select a DXF destination and enter the contour interval
when prompted.
The export intersects the mesh triangles with horizontal planes at integer
multiples of the interval in world Z, then joins the sections into 3D
polylines on layers `minor` and `major`. Every fifth elevation interval is
`major` (world elevations that are multiples of 5 times the interval); the
four intermediate levels are `minor`. The index is anchored at world Z = 0,
including negative elevations. Both CAD layers are defined in every DXF.
Every vertex retains its contour elevation; open lines and closed loops are preserved. The existing mesh DXF
option remains separate.

The interval uses the current model/world coordinate units. Georeference and
scale the model first for surveying units, and make sure model Z is vertical.
This is a section of the actual mesh, so roofs, vegetation and other mesh
features are included; it is not a classified bare-earth surface. No smoothing
or raster resampling is applied. Export runs in a cancellable background task
and replaces the destination only when complete. Extremely small intervals
are rejected if they would produce excessive output. AutoCAD and Civil 3D
are not required to generate the DXF.

## Ground control and check points

The marker section of the Reference pane provides **All**, **Control**, and **Check** tabs and coordinate
and pixel RMSE summaries. Control points participate in adjustment; check points
measure the result independently. Ignoring a marker is separate from its
Control/Check classification.

Right-click an existing marker in the Photo, Ortho, or Model view to **Delete**,
**Pin**, **Ignore/Use**, or **Move** it. Move enables a crosshair for the next
placement; **Escape** cancels. Moving a marker does not overwrite its surveyed
reference coordinates.

Marker display states are green for pinned placements, blue for placed/used
predictions, and grey for unused predictions or ignored markers.
To place an already selected marker on the orthomosaic, use **Place Marker**;
**Add Marker** creates a new marker.

## Rebuild after optimizing cameras

Camera optimization can change the geometry used by later products.
Rebuild notices above the Model and Ortho views indicate outdated products.

For a final result after bundle adjustment:

1. Save the project.
2. Run **Workflow > Build Point Cloud...** with **Reuse depth maps** off.
3. Rebuild the mesh with **Build Model...**.
4. Rebuild the DEM if it is used as the orthomosaic surface.
5. Rebuild the orthomosaic and any required texture or tiled model.

Rebuilding only the orthomosaic on an old mesh or DEM does not reconstruct
that surface with the optimized cameras. Original photos do not need to be
added again.

## Orthomosaic and DEM

Use **Workflow > Build DEM...** to create an elevation raster from the mesh or
point cloud. Use **Build Orthomosaic...** with the required Mesh or DEM surface.

The Ortho tab displays an actual orthomosaic or DEM after one has been built
or imported; it does not substitute the sparse point cloud for a raster.
Use **File > Export** to export orthomosaic and DEM products.

## Progress and background work

Progress dialogs show observed stage progress separately from the weighted
overall estimate. A stage with an unknown total remains indeterminate.
Remaining time appears when enough measured progress is available.
The status bar shows only Ready/Busy and CPU/GPU load. Progress stays in the
processing dialog or relevant Model/Photos pane. A busy cursor acknowledges
commands while their settings and input data are being prepared.

[Back to the main page](../README.md)


## Reference and Workspace in 1.0

Reference combines camera GPS and marker tables. Checking a camera enables its
GPS for optimization (when camera GPS is enabled in Optimize Cameras); it does
not enable/disable the photo for alignment. Selecting a row only selects it.
Uncheck a marker to use it as a check point instead of a control point.
Ignored markers are excluded independently of that classification.

Workspace lists the project's photos and products directly, without a Chunk row
or Add/Merge/Duplicate/Delete Chunk commands. Version 1.0 opens one dataset per
project. A legacy multi-chunk file is rejected with instructions to separate its
datasets in an older version; its original file is not modified.

**Preferences > Theme** applies Dark/Light immediately and remembers the choice.
**Default view** selects the requested product when it is available after loading.
On the first 1.0 launch the file-dialog preference is reset to Windows native
dialogs. Subsequent explicit choices are preserved. The built-in dialog option remains
an explicit fallback for Windows shell-dialog problems.

Marker edits preserve the selected photo and Photos-panel scroll position.
Project preparation runs off the UI thread and is transactional: a failed or
cancelled open leaves the current project in place.
