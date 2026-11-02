# User guide

[Documentation](README.md) · [Installation](installation.md)

1. *Workflow → Add Photos…* / *Add Folder…* — photos are analysed in parallel
   (EXIF GPS, thumbnails, global descriptors) and appear in **Photos**,
   **Workspace** and **Reference** panes.
2. *Workflow → Align Photos…* — image resolution, matching mode (**Fast** default /
   Exhaustive / Sequential), **camera estimation** (Auto / Global / Incremental /
   Hierarchical), coarse-to-fine, key point limit, guided matching…
   Result: camera positions + tie points in the **Model** view.
3. *Workflow → Build Point Cloud…* — Quality + Depth filtering (CUDA).
4. *Workflow → Build Model…* — Source (Point cloud / Delaunay from fused cloud and visibility),
   trimming and target triangle count.
5. *File → Save* stores a `*.pmsx` project (JSON); results live in
   `<project>.files/`.

## Dense cloud, filtering, mesh and ground control

**Build Point Cloud** (Workflow menu) – own parallel undistortion (photos are read in
place and never written to; downscaled undistorted copies go to `<workdir>\dense`),
quality Ultra/High/Medium/Low/Lowest = 1/2/4/8/16× downscale, one undistorted
pinhole camera per camera group, PatchMatch neighbours chosen from the sparse model
(shared tie points × triangulation-angle weight, 8 per photo by default),
geometric consistency, depth filtering Disabled/Mild/Moderate/Aggressive: Disabled turns off the PatchMatch depth
filter; fusion consistency checks remain active, then outlier filtering (minimum confidence = photos
per point, terrain sanity check, statistical and radius outlier removal; scipy
cKDTree, multi-threaded). Depth maps can be reused when the settings are unchanged.

**Tools > Point Cloud > Filter Point Cloud / Filter by Confidence**, **Model >
Gradual Selection** (tie points: reprojection error, reconstruction uncertainty,
image count, projection accuracy).

**Build Model** – Poisson (Open3D) with strong/moderate trimming or permitted extrapolation,
or Delaunay from the fused cloud and visibility data; face count
High/Medium/Low (points/5, /15, /45 as in Metashape) or Custom, quadric decimation,
removal of faces bridging gaps, long-edge faces and small components; automatic
voxel downsampling with an enforced point limit and bounded large-file loading.
A manual voxel that exceeds the limit is reported rather than silently changed.

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


### Reference layout and interactive settings

Camera RMSE occupies the last camera-table row under Error (m). Control-point
and check-point RMSE occupy the last two marker-table rows under Error (m) and
Error (pix). These footer rows cannot be selected or edited as cameras/markers.
No separate error-summary section is shown.

Properties is part of the Workspace tab and uses compact rows. It is not shown
with Reference. Interactive settings use the normal pointer, including while
background work continues; processing dialogs retain the wait cursor.

3D marker labels and the legend are rasterized before GL composition to avoid
driver-dependent glyph corruption over textured models.

Workspace and Reference extend down to the status bar. Photos, Console and Jobs
share the bottom area beneath the viewport, to the right of the left tabs.


## Workflow settings in 1.0.1

- Alignment uses Full, Half, Quarter or One-eighth image dimensions. The visible
  feature limit is the only fine-stage limit; zero means the engine default,
  not unlimited. Review calibration groups before combining mixed sensors.
- Re-alignment runs in a separate generation, preserves the old project frame
  using common camera poses and replaces the active alignment only on success.
  Derived products are marked outdated; their files remain recoverable.
- Depth-map reuse includes photo identity, camera calibration and all relevant
  depth settings. The first run against an older cache without those identities
  rebuilds its working images/maps. Keep depth maps if future reuse is wanted.
- Supporting-photo confidence is an observation count. Missing counts are reported
  rather than silently ignored. Terrain rejection is off by default and is not
  bare-earth classification.
- Mesh presets show the estimated triangle target in the count field even while
  that field is disabled. Cleanup and simplification may produce fewer faces.
  Voxel values use metres only when the reconstruction has a metric frame.
- Texture page count is a hard maximum unless automatic count is selected.
  Keep UV requires an exact source identity and displays the retained page count.
  Colour hole filling infers colour; it does not repair mesh geometry.
- Point tiles use the displayed point limit directly and export PNTS. Mesh tiles
  export B3DM/GLB. Texture controls are disabled for point tiles.
- DEM output is a DSM, not automatically classified ground. Mesh input samples
  triangle interiors. Coverage masks distinguish observed (1), inferred (2)
  and nodata (0) cells. Point aggregation offers Mean, Median and Highest.
- Orthomosaic half-resolution mode halves each photo, not a fixed-size assumption.
  A DEM surface is sampled at its own grid resolution. Filled pixels are inferred,
  not additional measured detail. DEM and camera frames must agree.
- Geographic survey references are reconstructed in a metric frame. Raster CRS
  labels describe that metric processing frame; UTM eastings are never labelled
  as longitude/latitude.
- Outdated inputs are displayed in the settings. Rebuild them, or explicitly
  acknowledge using the older source. New settings use a scrollable body with
  the confirmation buttons always accessible.

### Register newly added photos

After the original photos are aligned, add the new photos and place at least six
distinct pinned control markers over each new image. Their 3D positions must be
known in the existing model (surveyed in its frame or triangulated from aligned
photos). Spread them over the image; collinear or tightly clustered controls are
rejected. A compatible calibrated camera is required; choose its calibration
when multiple groups are available.

Right-click the photo(s) in Photos or Workspace and select **Align Selected
Photos from GCPs**. The batch is published only when every selected pose passes
the reprojection/geometry checks. Existing camera poses are unchanged. Shapes
refresh on the registered photo when their display is enabled.

Processing performance is compared against 1.0.0 on the same CI runner for
equivalent workloads. Corrected geometry, larger explicitly requested feature
counts, finer pixels or additional pages change the amount of work; they cannot
be assigned the same runtime merely by changing a label.


## Engine selection and GPS in 1.0.2

The full Setup includes pinned modern CPU/CUDA engines and the tested legacy
engine when supplied by the build runtime. The app probes the driver, GPU
generation and native initialization outside its GUI process. Unsupported GPU
feature execution retries the same feature method on CPU; dense depth maps
still require a compatible NVIDIA/CUDA engine.

**Align Photos > Features and matching** offers SIFT (default), SIFT + LightGlue,
and ALIKED + LightGlue. Neural methods use local models supplied by Setup.
They are optional: learned features are not automatically faster or more
accurate on every aerial block. Their feature count is explicit (default 2,048,
maximum 4,096); neural matching does not reuse SIFT descriptors or a coarse SIFT
database. Coarse-to-fine is a SIFT path.

**Apply checked camera GPS to model scale, orientation and location** is separate
from GPS pair preselection. It is offered for an initial alignment when enough
checked cameras have valid non-collinear positions in a supported projection
region. It applies a similarity transformation; it does not turn ordinary EXIF
GPS into survey-grade control or replace calibration/GCP validation.

Existing alignments and survey frames are preserved. Use **Optimize Cameras**
with the appropriate references and accuracies to change their frame.
Rebuild derived products when camera geometry changes.

SIFT remains the default. Automatic mapping chooses the integrated global
solver for sufficiently large sets when supported, and retains incremental
fallback. A CUDA build alone does not establish GPU support in every solver:
uncertified Ceres GPU solvers and experimental backends are not enabled by default.


Coarse pose reuse additionally requires reliable focal priors reported by the
engine. If those priors are unavailable, the target-resolution features are
mapped afresh rather than inheriting a potentially ambiguous coarse calibration.
The Console records that decision. Reprojection error alone is not an
independent accuracy check; use surveyed check points for metric validation.

On older drivers, a compatible retained legacy engine continues GPU SIFT and
dense processing. Optional neural methods can use the modern CPU engine instead.
Disabling both pair-preselection options explicitly matches all image pairs;
large datasets should retain appropriate preselection to limit the workload.

Cloud Properties accepts historical pair-list and dictionary filter statistics.
Opening an older project does not require rebuilding its point cloud for this
metadata display fix.
