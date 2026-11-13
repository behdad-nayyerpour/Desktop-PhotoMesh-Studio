# Combined survey/terrain tools candidate (2026-11-12)

## Finalization items4/5/6/7 (2026-11-13)

User accepts the capacity/manual test iteration and requests closing dependency
provenance, script/error handling and locked dependencies, branding/docs/shortcut
completion and final real-data validation. User has no surveyed personal fixture
and explicitly authorizes a reputable public reference dataset. Preserve the
approved PDF bytes, project/settings compatibility and previous survey tools;
direct point selection/deletion remains deferred. Maintainability review covers
changed callers, reusable build/verification contracts, true numerical residuals,
offline operation, cancellation and upgrade/rollback. Validate exact upstream
wheel and native source/build provenance instead of changing a review status
without evidence. Test public data against held-out independent references;
separate GPS/height assumptions, classification and progress/ETA measurements.
No claim of target-GPU validation without that hardware. Deliver one combined
incremental BAT against the accepted capacity baseline; no Setup, repository
rename, announcement or public installer release is authorized by this request.

### Finalization evidence (2026-11-13)

- User-script reading/compilation/execution now reports complete tracebacks,
  accepts Python encoding declarations and preserves console objects. Script
  execution remains on the GUI thread to preserve Qt ownership; long blocking
  custom scripts remain the author's responsibility.
- An exact76-package Windows x64 CPython3.13 lock records official wheel hashes.
  Build stages reject version drift and unexpected packages; package metadata
  is checked separately from binary inventories and upstream byte comparison.
  Native package preparation stays on disposable builders, never user patching.
- All1564 compared Qt binaries/resources match official PyPI wheels, including
  Pdf/WebEngine6.12.0.140. All71 legacy COLMAP3.8 and74 GLOMAP1.2.0 native files
  match primary release archives. Legacy CUDART identifies as11.8.89. Retained
  source/build descriptions, versioned NVIDIA terms and source locations improve
  the offline notices. Exact linked-library corresponding-source/build retention
  and split WebEngine source packaging remain release gates; do not mark legal
  redistribution clearance complete merely from those identity matches.
- Per-user legacy shortcuts are renamed only when their launcher, main script
  and working directory identify this exact install. Preserve original bytes,
  target and arguments; skip collisions and unrelated shortcuts. Real WScript
  fixtures verify custom paths with spaces, backup, repeat behavior and ownership.
- Current README/update/install/packaging guidance identifies Lens2Mesh1.0.5 as
  a candidate, retaining the public1.0.4 download and compatibility identities.
  Sharp actual Dark/Light Mesa screenshots use public data with attribution.
  The complete approved English PDF remains byte-for-byte unchanged.
- Independent public RTK/GCP data: OpenDroneMap/odm_data_helenenschacht at
  eece33e9ece2ff358a7bdc02e1db6f67925e00c4. All35 selected photos register;
  12,459 sparse points. Controls1/2/4 constrain adjustment, while3/5 remain
  independent. Their XY errors are0.08855/0.07382m and height differences
  -0.16925/-0.20267m. GPS-only XY errors are0.09401/0.12220m; GPS height is not
  assessed against a control datum that was not confirmed. Mixed unknown
  heights are rejected. Results match the accepted capacity baseline exactly;
  these limited results do not certify centimetre accuracy for all projects.
- Public human-labelled LiDAR: PDAL/data Autzen at
  ce0024257c573526389c4db9ab26e82739b8aaa9,10,653,336 points. Read horizontal
  international feet and vertical US-survey feet separately from its compound
  CRS; convert units without inferring a datum transformation. Ground recall
  98.944%, precision90.200% over documented known classes; unclassified points
  are excluded from negative truth. Full LAS/LAZ coordinate/class/attribute
  round trips pass. A2m DTM has326,537 measured cells and zero filled cells;
  all measured means match independent aggregation, with real coverage retained.
- Actual CPU extraction timestamps show35 monotonic counts over91.42s from
  first to last completed image. Bursty two-worker rates correctly suppress ETA;
  the4–5s classification workload also does not invent a stable ETA. Existing
  equal-workload sparse/GPS/DEM capacity benchmarks retain identical numerical
  results. This does not establish target-CUDA, cached dense or long-run GPU ETA
  behavior. Those hardware checks remain explicit before a public Setup.

Review scope: script/UI callers, Qt ownership and console state; exact-baseline
patch allowlists and recovery; stage metadata after reviewed removals; shortcut
ownership and collisions; source/license evidence versus legal conclusions;
coordinate units, independent checkpoints and real-data reference quality.
No unrelated processing math or defaults changed in this finalization iteration.

The first finalization test candidate was be95c3a06b734dade16830f206c1d1f4024696cb; only
the two visually verified screenshot PNGs differ from the fully tested app tree
at a93c60855ae15c9da3c6b25b0100a5556642a199. Full Windows917/9skip and
Linux913/13skip plus Mesa checks pass. Disposable exact1.0.4→candidate inventory
has25,398 files; rollback restores all26,196 original files byte-for-byte.
Fresh hash-required76-wheel download and offline isolated installation/import
pass. The actual finalization BAT workflow43410086457 tests the accepted
capacity baseline,87 installed offline regressions, exact package versions,
native mesh DEM/PLY/manual/splash behavior, full app rollback, reapplication
and a second byte-exact rollback. The app-only delta updates30 components,
2,454,185 bytes; PDF, reusable Python and engines are unchanged.

Additional bounded target-GPU smoke used four SHA-verified public photos
(MAX_0104/0105/0106/0108.JPG) in a new validation folder. RTX3080 Laptop16GiB,
driver512.36 correctly selects the unchanged legacy COLMAP3.8 CUDA fallback.
The production PipelineRunner performs undistortion, GPU PatchMatch, fusion
and filtering: fresh8.65s/70,300 points; cached1.26s/70,301 points, zero repeated
PatchMatch commands and byte-identical geometric depth maps. An initial harness
asserted exact fused point-count equality; that is not a valid contract for the
native row-parallel fused-pixel masking. Follow-up four-thread fusion repeats
vary slightly; two one-thread repeats produce identical70,876-point files with
SHA256c549c4c1c359bebb67833fd5a7c35785b2e6523f426f5078a8e662494d61d10d.
This isolates native fusion variability from depth-cache invalidation. No
application reconstruction calculation or threading default was changed to
force that comparison. This is a Low-resolution four-photo GPU/reuse smoke,
not independent surveyed dense-surface accuracy or modern-CUDA13 driver proof.
The retained engineering/source-packaging gates above still apply before Setup.

Packaged screenshot attribution was subsequently separated from the numerical
survey fixture: final distributed PNGs use PDAL/data's CC-BY-4.0 Autzen terrain,
showing the actual automatic ground/non-ground colours. Original application
interface/logo rights and the application license are retained. The GPL survey
photos remain numerical test data. Only README, image attribution and the two
PNG captures change from that first tested delivery; processing code, PDF and
runtime remain the same. The exact final delivery revision and hashes are in
the final patch summary, with actual BAT rollback checks repeated for its bytes.

The delivered app candidate is63b70e534597e17a54e91a31696ed5d423e1b396.
Its30-file app-only archive is1,649,602 bytes, SHA256
dd3421f8d5c45c9c130a6d301c4f2707e29d14f37e03ba6d63c69960985af169.
[Final actual BAT validation](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43415141556)
passes87 installed regressions, offline native/document checks, complete app
rollback, reapplication and second rollback. The verified BAT is6,146 bytes,
SHA25676f24ce716afc75c9c7abe80a3447804722b4c72a2cd503e194c3d0bc938e1c3,
delivered at artifact commit dbee071a52f69857d10359f980cd72f7a522d995;
public RAW readback matches those exact tested bytes. No Setup was built.
Item4 remains open specifically for the corresponding-source/build packaging
gates recorded above; these tests do not close those findings.

## Approved performance, offline manual and dependency iteration (2026-11-13)

User defers direct point selection/deletion to the following version and requests
one BAT for: sparse camera-side bundle solution, exact GPS neighbour preselection,
faster exact DEM median aggregation; offline Help access to the approved unchanged
complete PDF; and completion of the engineering dependency/redistribution review.
Review numerical contracts and callers, compare equal inputs to the current
implementation, include deterministic ties and cancellation, and measure memory
and runtime. Preserve project formats, reference weights, section interaction and
all other candidate functionality. Reconstruct the exact accepted section baseline
from authenticated artifacts; validate apply/offline/rollback on a disposable
installed runtime. Audit Qt/native/model components against exact inventory and
primary upstream terms, collect version-matched notices/source information, and
remove a component only after dependency verification. Record unresolved evidence
honestly; do not describe engineering review as legal clearance. No full Setup,
repository rename, PDF edits or public installer release in this iteration.

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
6. Interactive 3D distance/coordinate differences with actual surface picks,
   correct model scale/offset and m only when established. The 2026-11-13 request
   merges the visible measurement command into Survey > Cross Section.
7. Interactive mesh-derived profile in a closable bottom panel (superseding the
   original floating-window scope), draw/edit section line in 3D, a calibrated
   photo or co-registered orthophoto; gaps, multi-intersection semantics, slope,
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

Delivery status (2026-11-13): final app52f18f45a505d6bb5fdb33310bf1a11867ed75ae
passed Windows861/8 skipped and Linux857/12 skipped, installed inventory26249
with runtime bundles unchanged, and actual combined BAT35 installed tests plus
full byte-exact rollback/reapply/second rollback. See release-review-105.md for
run links and hashes. One BAT delivered from artifact commit8710ba0b66b63bab74b439e1fdac8ad6655b04e5;
757822-byte delta against the verified current progress baseline. Await the user's
candidate test before a full Setup; real surveyed checks remain outstanding.

## Survey interaction revision (2026-11-13)

User requests closable bottom panels for both tools, native model navigation
during drawing, measurement/section clicks in 3D, co-registered orthophotos and
aligned photos, and a mouse-following draft line with calculation only after the
second click. Manual coordinates remain. Keep photo rays in the calibrated model
frame and refuse missing depth/alignment or stale source identities. Preview is
visual only, not a fabricated depth measurement. Separate cohesive survey UI/
controller work from terrain/classification. Review event propagation, dock/
worker lifecycle, projection/scaled photo coordinates, stale results and marker
editing interactions. Test click versus drag, both tools in all views, live
preview versus committed results, closure/reopen, manual inputs and known
geometry. Deliver one hash-bound BAT; retain PDF and defer Setup as instructed.

User added endpoint dragging and a midpoint grip for moving the whole line.
Implemented and verified in appde38ba9e9b3759596061d59fd26b737ea7b1a884:
Windows876/9 skipped, Linux872/13 skipped, two separate Mesa GL checks and50 actual
installed tests with rollback/reapply. The single panel BAT downloads90178 bytes
and updates8 app components against the verified current survey build; public
artifact commit302a8a77787311366590115b844091f64c815cd8. Acceptance pending.

## Unified Survey cross section corrections (2026-11-13)

User requests moving Cross Section from Display to Survey, removing standalone
Measure Distance and Pick Start/End buttons, retaining distance information in
the section panel, fixing final clicks and all handles on photos/orthophotos,
blocking context/control-point edits while the panel is open, and preventing new
drawing during slow surface/profile work. Reproduce complete mouse event paths
instead of testing only controller calls. Review press/release propagation,
viewport dimensions/transforms, camera/raster identity, explicit draft/busy/ready
states, worker ownership/cancellation and close-time restoration. Keep native
navigation, manual XY input, three handles, numerical geometry and project data.
Run actual photo/ortho click/move/click and endpoint/midpoint drags with calibrated
fixtures, delayed workers and blocked/restored marker gestures. Assess maintainability,
compatibility and UI responsiveness; one exact-baseline BAT, no Setup/PDF change.

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
