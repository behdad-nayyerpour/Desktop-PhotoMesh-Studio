# 1.0.4 implementation and numerical review

## Scope and authorization

The user reviewed the test installer, explicitly requested the remaining fixes
and final public release, then expanded the review to numerical alignment and
marker error calculations. On 2026-11-07 the user also approved display/select-only
markers in the 3D and orthophoto views. [Version 1.0.4](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/tag/v1.0.4) was published on 2026-11-07. The [publication run](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42399927092) verified the public download against the installer that passed the upgrade test.

This review covers the changed modules and their callers/workflows. It is not a
claim that every repository path is bug-free or that synthetic accuracy establishes
accuracy on real survey data.

## Implemented behavior

- Project / Markers / Cameras panels, Photos right, initially hidden floating
  Console/Jobs, shared 3D View / Plan View layout.
- Photo selection resets Ortho/DEM tools for one-click return to raster display.
- Processing reports use the project filename instead of legacy dataset titles;
  project/camera/log text is escaped in HTML.
- Project-wide Use Photo GPS gates alignment preselection and camera references.
  Photographs remain included when GPS is off. Legacy opt-outs are preserved
  conservatively; markers never implicitly toggle GPS.
- Saved appearance/layout/render states and successful file-picker directories.
- Approved offline About/license viewer, existing project compatibility and
  failed-photo identity handling.
- Photo-only marker measurement edits and table-only surveyed XYZ edits.
  Model/orthophoto flags support display and selection. Add/Place/Move/Pin/Delete/
  Ignore/Use mutation connections are removed from those views; retained legacy
  signals/entry points cannot mutate marker data.
- Pin/refine provenance survives project save/open and PhotoMesh reference XML.
  Predictions and unconfirmed legacy unpinned locations remain display hints,
  excluded from adjustment and measured errors until pinned/refined on photos.

## Numerical findings and corrections

1. Local Optimize Cameras previously ignored the unchecked marker switch and
   still sent image observations to bundle adjustment. A separate diagnostic
   branch reproduced identical marker observations with the switch off/on.
   Both local/global workers now honor it; project GPS and per-step GPS controls
   are consistent. Check points remain independent, including the legacy hidden
   option. GPS initialization can still use one/two available control markers
   during subsequent adjustment.
2. The custom optimizer used a square-pixel Brown approximation for all cameras,
   averaging fx/fy, interpreting fisheye as Brown and dropping rational terms.
   It now preserves COLMAP camera model IDs and full model-specific calibration.
   Projection shares the canonical camera equations through calibration.py;
   fitted parameter indices are explicit. Invalid weights, focal lengths and
   non-finite initial residuals are rejected.
3. Inverse distortion uses converged Newton inversion with finite/singularity/
   nonconvergence checks. Triangulation rejects non-finite, degenerate and
   behind-camera intersections. A failed solve retains the published model.
4. Marker diagnostics use current measured observations, not automatically
   generated predictions. Pixel residuals include finite off-image projections
   rather than silently discarding large errors. Reference XYZ remains immutable
   under photo edits. Current control/check rows and RMS update after edits,
   ignore/type changes and Undo/Redo, including camera-calibration cache identity.
   Missing/invalid errors are unavailable, never fabricated zero values.
5. Duplicate observation aliases count each camera once. Conflicting equal-status
   aliases fail clearly; pins take priority over unpinned aliases. Marker/photo
   navigation, filtering, registration and photo overlays use stable aliases.
   Re-alignment preserves stored aliases across removal, disabling and reordering.
6. GPS pair selection validates complete positions and uses continuous ECEF chord
   distances across the date line. Similarity fitting validates finite paired
   positions/weights and returns a transform fitted to its final inlier mask.
7. Geographic references consistently enforce the supported UTM latitude/zone
   range. Longitude +180 uses zone 60, never invalid zone 61. Invalid reference
   errors are unavailable while valid markers retain their independent rows.
8. Known source-photo/calibration dimension mismatches fail before marker
   optimization/refinement rather than mixing pixel units. Out-of-photo margin clicks cannot create/move
   measurements, and imported out-of-bounds observations are rejected before
   adjustment. Normal pipelines
   restore original-photo dimensions; native fixtures verify that contract.
9. Added-photo resection requires measured 3D controls or surveyed coordinates
   in an existing referenced frame. Predicted-only 3D hints cannot initialize
   its camera. Existing poses and calibration remain intact.
10. The active CRS follows a successfully applied georeferencing result, and
   legacy blank project CRS falls back to its persisted frame for marker edits
   and selected-photo registration.
11. Exported reference reports retain current pixel errors/counts. Reference XML
   preserves ignored/locked/control status and measurement provenance.

## Maintainability and affected-caller review

Read the main window, reference/marker/registration callers, camera I/O and
calibration, project serialization, photo naming/GPS policy, native/fast alignment,
panes/error summaries, both spatial views, photo event/menu handling and downstream
product invalidation. The repository AST/static inventory and equivalent-workload
performance gates run in CI. Static/zero-reference findings are leads, not a
deletion list; Qt hooks, protocol methods, dynamic tasks and compatibility entry
points are retained intentionally.

Focused cleanup: one canonical marker-observation selection/deduplication policy,
one measured/predicted predicate, shared current diagnostics, shared photo identity,
and model-preserving calibration projection. Obsolete simplified optimizer
projection/calibration helpers were removed after checking callers. The photo
Place command now uses the same validated pin operation. Obsolete spatial editing
bodies and signal connections were removed; no-op compatibility entry points and
signals are intentional. The retired Ortho marker-height editing helper and the
now-unused flat-GPS math import were removed after checking their callers and
replacement workflow. Existing CPU/GPU/legacy engine variants remain.

## Validation

Validated application commit `910d42f25c2d37b9a15da032f875b1f31c021e53`. [Linux and Windows tests](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42383383754) and the [Windows installer and upgrade](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42383383859) succeeded on this commit.

- On each OS the full suite had 775 passes and eight skips. The dedicated numerical suite had 72 passes. Mesa overlay, theme/scale layout checks and static gates passed. The inventory covered 137 Python files and 73 application modules, with zero static leads and zero exact nontrivial body duplicates.
- The equivalent reference adjustment on Linux measured 0.35751507235 px RMS for both versions. Median elapsed time rose from 49.33 to 57.21 ms on that fixture, within the performance gate.
- Bundled COLMAP CPU recovered all 16 cameras in the known-calibration SIFT incremental and global fixtures, with reprojection RMS of 0.2233 and 0.2144 px respectively. These numbers describe the test fixtures.
- The production offline Setup passed upgrade from the public 1.0.3 installer, installed-file identity, project preservation and offline license acceptance. Final Setup size is 860,496,028 bytes. SHA-256 is `58bbe53ce24f3a0dbd0730129885d76a27471899d1d2098774e8369a594113e3`.
- The archived candidate is artifact `13578838934` with ZIP SHA-256 `c96d19d68456b62469725444d72e8978167310f725336bf008117d37f2aa2940`. Publication verifies the archive and Setup against these recorded values.

- Independent equations test projection/inverse for all seven supported COLMAP
  models, unequal fx/fy, fisheye and FULL_OPENCV rational distortion.
- Exact-data and noisy-data bundle fixtures run with calibration fixed/fitted,
  checking geometry, model identity and independent residual reduction.
- Known coordinate/vector RMSE, switch matrices, independent check points,
  alias conflicts, degeneracy, frame transformations and failed-task integrity.
- GUI marker edits/Undo/Redo, read-only spatial menus/signals, project/XML round
  trips, source pixel dimensions and dependent selected-photo registration.
- Equivalent pre-audit/current optimization accuracy and runtime comparison,
  existing texture/performance and static/inventory gates.
- Full Linux/Windows suite, Mesa overlays and layout checks at scales 1/1.5/2.
- Native COLMAP CPU geometry/feature fixtures and disposable 1.0.3-to-1.0.4
  upgrade; installed source hashes and offline Dark/Light license validation.

## Remaining limits

Real-data CUDA processing, survey accuracy, target GPU/driver/OpenGL and performance
on the user's projects require target-hardware/data acceptance. No user files or
local working copies were inspected or modified. Legacy unpinned locations cannot
be reliably classified as measured from old files; they require photo confirmation
or refinement. Turning GPS off does not undo an already established coordinate
frame. Dense products must be rebuilt after camera optimization.
