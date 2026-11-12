# Combined survey/terrain tools candidate (2026-11-12)

User explicitly requests GPS/calibration, coordinates, classification, LAS/LAZ,
DTM, measurement and cross section in ONE incremental BAT. Do not deliver small
intermediate BATs for these items. No Setup before candidate acceptance; retain
PDF unchanged per existing user instruction. Prior accepted app iteration: display;
progress candidate delivered, acceptance not separately confirmed. Combined patch
must handle the user's verified installed baseline safely, including latest progress
if present, without weakening hash checks.

Implementation/maintainability plan:
1. Strict shared EXIF GPS decoder; correct model-specific intrinsic presets;
   camera-model selection wired through all extraction routes. Validate metadata
   provenance, per-camera accuracy and height reference; preserve GPS-off semantics.
2. Explicit coordinate/height-frame metadata and tested Cartesian/ENU frame work;
   do not silently convert vertical datums or reinterpret legacy projects. Audit
   marker residuals, downstream rasters/shapes/exports and local-unit labeling.
3. Ground/non-ground classification with explicit terrain/slope/height settings,
   source-bound persistent labels, class colors/filtering, and preservation of
   other PLY attributes. Classified ground is separate from outlier filtering.
4. Streaming LAS/LAZ with double-to-integer bounds/precision validation and CRS,
   class/RGB preservation; vendor only required audited dependencies in app paths
   so updater never redownloads Python/engines or runs pip on user machine.
5. Ground-only DTM path alongside DSM. Preserve measured vs interpolated masks;
   never interpolate across unbounded gaps without an explicit limit.
6. Interactive 3D distance/coordinate differences with actual surface/point picks,
   correct model scale/offset and m only when established.
7. Interactive mesh-derived profile in floating window, draw/edit section line
   in 3D or co-registered orthophoto; gaps, multi-intersection semantics, slope,
   cancel and stale-result guards. Keep slow mesh work off GUI thread.
8. Synthetic numerical tests + independent references; affected-caller/workflow
   review and full Windows regressions. Document target surveyed-data/GPU checks
   not performed. Build one exact-baseline incremental archive; actual installed
   download/apply/offline workflows/rollback/reapply tests before delivery.

Implemented candidate scope: strict shared EXIF/XMP metadata decoding, explicit
camera models/intrinsic presets, opt-in GPS priors/reported deviations, supported
metre-based projected CRS and explicit WGS84 ENU with height-reference gates;
ground/non-ground classification with preserved original cloud/attributes;
class colors/visibility, streaming LAS/LAZ, independent ground-only DTM;
actual-surface distance picks and editable mesh upper-envelope cross sections.
New processing is in focused survey/coordinate/terrain modules. Existing DSM,
marker photo-only editing, old project defaults and runtime bundles remain intact.

Local numerical/affected-workflow regression: 157 passed before final DTM build
integration and visible-class picking additions. Real DTM backend/UI completion
now also passes (5 survey UI tests). Independent comparisons use pyproj/ECEF,
known mesh slopes/holes, source attribute comparisons and LAS/LAZ round trips.
Fresh Windows full regression, installed single-BAT apply/rollback and release
inventory are required before delivery. No target surveyed terrain, independent
surveyed checkpoints or actual CUDA alignment benchmark has been performed.

Installed managed baseline was read-only verified against all 106 trusted app
files derived from authenticated R2+splash+display+progress archives. Ignore
unmanaged local files when constructing the patch baseline. New dependencies
are exact laspy 2.6.1 (BSD) and lazrs 0.7.0 Windows CPython3.13 (MIT) wheel members,
including licenses/RECORD and wheel hashes, vendored under app only; no pip on
the user's installation. Whole-runtime licensing review remains a separate item.

Existing code map: reference_ui.py mixin for GPS/markers/optimization;
georef.CRS and run_task for adjustments, workflow.processing_crs/source_unit;
calibration.py has model-specific fit indices, colmap_io models0..6;
fastpipe.fast_steps extract() and colmap.align_steps feature extractor command
construction; dialogs.AlignPhotosDialog and OptimizeCamerasDialog;
workflow.vertex_blocks for streaming scalar ASCII/binary PLY, plycodec for full
attribute-preserving rewrite; dem_engine.build_dem is transactional and handles
block-capable DSM; ModelView.ray_at gives model-frame ray; views eventFilter,
OrthoView world coordinate interactions for tool selection; menus.py MENUS,
mainwindow handlers dict and mixins for UI integration.

Primary docs consulted: https://colmap.github.io/cameras.html and official
colmap/colmap doc/faq.rst parameter orders; https://laspy.readthedocs.io/en/latest/
installation.html and github.com/laspy/laspy for chunked writer/LAZ and CRS support.
No external code copied; dependencies need exact wheel/version/license verification.
