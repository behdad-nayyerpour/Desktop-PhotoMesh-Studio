# Combined survey/terrain tools candidate (2026-11-12)

## Final release authorization (2026-11-13)

The user authorizes completing the remaining source/licensing and hardware
review, updating the affected parts of the approved full PDF, building and
validating Setup, performing final integration/maintainability/dead-resource
review, and publishing version 1.0.5 after those checks succeed. This supersedes
the earlier no-PDF-edit and no-publication instructions for this release.
Preserve unaffected manual content and sharp screenshots. Direct point selection
and deletion are explicitly deferred to 1.0.6. Preserve the accepted application
behavior and project/settings compatibility. Do not mark unsupported hardware
paths or missing source provenance verified merely to proceed to publication.
The user has access only to the existing RTX 3080 Laptop / driver 512.36 system;
modern CUDA testing therefore needs a separately evidenced compatible runtime
or a documented, tested supported-engine policy. Do not silently update the
user's display driver. Source/notice collection, optional Qt dependency closure,
installer fresh/upgrade/custom-path/uninstall checks, PDF rendering and final
repository/caller/static review remain work to complete before publication.

## Target driver and modern-CUDA checks (2026-11-13)

The user explicitly authorized preparing the official Studio 621.14 notebook
driver and then opening its installer, and confirmed installation. Read-only
`nvidia-smi` now reports 621.14 on the RTX 3080 Laptop (16 GiB). The application's
CUDA API probe reports 13050 and selects the modern COLMAP 4.2.1 dense engine,
SHA256 `9418a14c93d4a5eec5eb33ebf48a917403b5faa7ab5d2232f23e50c206d9e427`.
The downloaded NVIDIA-signed installer was verified before launch; no silent
installation or restart was performed by the agent.

Retained public Helenenschacht photos MAX_0104/0105/0106/0108 and the same
four-view sparse model were processed in separate fresh folders. Low quality:
fresh 14.55 s / 70,989 points, cached 2.70 s / 70,992 points. High quality:
fresh 53.94 s / 634,963 points, cached 7.05 s / 634,975 points. Each fresh run
invoked real CUDA PatchMatch; cached runs invoked none. All four geometric
depth-map hashes remained identical during replay. Small point-count differences
are native parallel fusion variability already documented, not repeated depth
computation. Logs/results/depth hashes are retained under the validation evidence
folders `modern-gpu-validation` and `modern-gpu-high-validation`. High-quality
processing emitted observed ETAs after stable samples; this bounded four-photo
check does not establish independent dense accuracy or hour-long ETA accuracy.

The initial offline probes passed SIFT on GPU and both learned methods through
the existing same-method CPU fallback. The ONNX GPU provider initially lacked
`cublasLt64_12.dll`; a newer display driver does not supply this library. Those
initial failures are retained in `modern-feature-diagnostics`. The subsequent
private-runtime fix and genuine neural GPU results are recorded in
[the completion section below](#private-onnx-cuda-runtime-completion-2026-11-13).

The optional Qt review now passes 87 installed offline integration tests and
917 complete regressions (9 skipped) in run 43436592948. The exact 1,018-file
plan is adopted with this evidence recorded in the plan itself; final complete
patch/rollback inventory and Setup validation remain required. A preceding
harness run missed shared fixture modules (74
passed / 13 fixture import failures); copying the complete fixture set corrected
the harness without modifying application calculations. The static closure check
finds no remaining imports of removed modules among 1,272 remaining PE files.
Artifact 14043109942, SHA256
`ccc606478147583a09cacac3d9a627fbf7d8bfe9df30203a32845b492905d32f`,
is retained. These checks establish runtime behavior and static import closure,
not legal clearance. The full-suite harness also needed the independent PLY/DXF
test readers and their parser dependencies outside the shipped runtime; those
collection failures did not indicate missing application dependencies.

Further primary-source investigation identifies the legacy executable's exact
source commit as `45edd3dfde0d945d305de3f299f3c36ae098620c`. Its versioned Azure
recipe pins vcpkg `4efb7ed628be5e56eeee009524e6ca7f3cc49c74`; that baseline's
Qt5-base version is 5.15.8, consistent with the shipped DLL. Earlier notes calling
the legacy recipe unpinned were incomplete. Both this pinned recipe tree and the
modern `127402f1c75bb3d5ff6bce04b285faa4930a5aca` tree are retained, along with
official hash-verified Qt Base/SVG 5.15.8 and 6.11.1 source archives. Full linked
dependency source/notice retention is still being completed. GLOMAP1.2.0's
versioned workflow remains unpinned; its authenticated 18,151,227-byte official
ZIP was independently inspected and contains only executable/DLL members.
No request has been sent to upstream maintainers without user authorization.

A complete private Setup candidate was built from 65a3848 (847,159,638 bytes,
SHA256 `00e2790e78db56279ae1ba66d18c2ef3fb0cb06a881350f99cf82d575488aa8b`).
Upgrade and custom Unicode installation both passed exact application-file,
About/license/themes, updated manual, package lock and offline native terrain/PLY
checks. Shortcut target string comparison then failed before uninstall checks;
the original target was not logged, so it is not established whether this is a
path-alias test problem or a real shortcut defect. The next run records original
shortcut metadata and compares canonical file destinations. Do not deliver this
earlier unapproved Setup as final. The next build also applies the expanded
reviewed Qt cleanup.

Manual review identified a DTM dialog note incorrectly describing a DSM. Its
title/context now explicitly describes class-2 ground; the numerical processing
configuration is unchanged. All 13 affected survey/build-display tests pass;
targeted static checks pass. The updated full English manual has 119 pages and
covers all 121 reachable menu commands. The approved unaffected content is
retained, with focused new sections for GPS/calibration/height frames,
classification, DTM, LAS/LAZ, section interaction, progress and offline help.
Updated native 2x PNG screenshots are embedded losslessly. All page layouts
were reviewed as rendered contact sheets, with full-page checks of changed
reference, terrain and section pages. Windows offscreen capture initially lacked
the Linux font; explicit registration of the installed Segoe UI font corrected
the capture harness before the final screenshots/PDF were produced. No tofu
captures were accepted. The PDF SHA256 is
`716a33f587cd3cd3303629b33d6096d7a120bed4c753808f3b0e21bf58f04706`.
Help now points to the 1.0.5 PDF. Original approved 1.0.4 PDF/sources remain in
the separate guide archive; the unused old bundled copy is superseded.
All 18 affected documentation/survey/build-display tests pass. Fresh complete
source/trimmed-runtime regression and final installed package tests are pending.

## Finalization items4/5/6/7 (2026-11-13)

### Verified Setup and retained release evidence

The final engineering Setup run 43442904216 at source
`6ec8619313e0a120fed8da9dd66bbed6bba04df2` succeeds. Both upgrade from the
authenticated 1.0.4 baseline and a custom Persian destination pass exact app
file comparison, offline About/licence/themes/manual, 76-package lock and native
terrain/PLY checks. Explicit Unicode IShellLinkW confirms the desktop/Start Menu
target, application argument and icon. Uninstall succeeds and preserves the
external project/photo fixtures. Controlled local reproduction establishes that
the earlier question marks were lossy Windows Script Host getters, not a reason
to alter the installer or relax the target checks.

The retained single EXE is 753,496,141 bytes, SHA256
`b82858ffcfa45dce757bb065ec3481dcc4d61a5ad29c810b988fc88eedb7b1fa`.
Original artifact 14046324235 has outer SHA256
`3435e6a4befa7f372cdc6858b4d23976a41ffea70cfa6c7cc4ceb2d8eb4a142c`.
The connector cannot download artifacts above 512 MiB, so transport run
43449338471 splits the already verified EXE without modifying it. Both part ZIP
digests, both payload digests and the reassembled EXE digest are checked locally.
Evidence artifact 14050300131 retains install/uninstall results, Unicode/WSH
comparison and screenshots. The EXE remains a review candidate, not a published
or fully redistribution-cleared release.

Full candidate run 43439670849 also succeeds. Retained artifact 14045538131 has
SHA256 `cb7abf2e8b1db4cc4e7b250d481bcd3b142740d578047c5a79e74690db785cbb`.
Its authenticated inventories have 25,261 candidate files; every one of the
26,196 original files is restored byte-for-byte after rollback. All 1,018
reviewed Qt targets are absent in the candidate. General checks at 6ec8619
(run 43442904311) and c846a5b succeed. No numerical application code changed
after the accepted candidate; the production-code diff is limited to the DTM
dialog description/flag forwarding and the new manual path.

Official Qt 6.12.0 full sources (443,394,020 bytes, SHA256
`98ff4f44bac6ec3e1e62ee2a4316ae0e3d15badb015d753cc0268a20db52f165`)
and PySide 6.12.0 sources (18,211,772 bytes, SHA256
`099c1a597cf33c1b000e11cf68a0b82d216fb802bf81726efc720394f10c7751`)
are now retained against the publisher's mirrorlist hashes. Together with the
earlier native Qt archives and pinned recipe trees, this improves source
retention but does not certify the complete linked native dependency closure.

The notice generator can now accept the exact Qt-removal plan and full candidate
inventory. It rejects an incomplete inventory or any remaining reviewed/optional
binary before recording the exclusion; the original pre-cleanup inventory is
correctly rejected. A generated review in a separate evidence folder has 209
collected texts and retains the native source/notice blocker. This removes the
irrelevant split Pdf/WebEngine source gate only when their absence is proven;
it never turns blanket redistribution clearance on. The bundled index will be
refreshed with the final dependency review before publication.

With explicit user approval the missing GLOMAP build-record question was posted
as https://github.com/colmap/colmap/issues/5036. The old GLOMAP repository is
archived/read-only and its README identifies COLMAP as its official successor;
the approved question was posted unchanged there. No reply is present at this
checkpoint. Exact remaining native source/notice retention must still be closed
before the conditional public release; passing installer tests is not a reason
to silently clear that gate.

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
[Final actual BAT validation](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/43415141556)
passes87 installed regressions, offline native/document checks, complete app
rollback, reapplication and second rollback. The verified BAT is6,146 bytes,
SHA25676f24ce716afc75c9c7abe80a3447804722b4c72a2cd503e194c3d0bc938e1c3,
delivered at artifact commit dbee071a52f69857d10359f980cd72f7a522d995;
public RAW readback matches those exact tested bytes. No Setup was built.
Item4 remains open specifically for the corresponding-source/build packaging
gates recorded above; these tests do not close those findings.

### User acceptance (2026-11-13)

The user installed candidate63b70e534597e17a54e91a31696ed5d423e1b396
through the delivered finalization BAT and reports that all six requested manual
checks work: name/icon/version, an existing project's display/save/reopen,
offline manual/notices, script-error reporting with continued application use,
cross-section interaction and persisted appearance/layout.

Record this as acceptance of the tested candidate, not an independent numerical
accuracy measurement or closure of item4. The accepted app revision remains the
installer baseline. Complete the two recorded native/split-module source/build
packaging findings before preparing the final Setup. Candidate acceptance does
not authorize public publication. Keep the approved PDF unchanged and point
selection/deletion deferred as instructed.

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
actual-surface distance picks and editable mesh cross sections (initially an
upper envelope; replaced by exact mesh-plane intersections in the follow-up below).
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
## Private ONNX CUDA runtime completion (2026-11-13)

The native ONNX CUDA provider in the official modern engine imports CUDA 12
cuBLAS/cuBLASLt/runtime DLLs, while the dense engine carries CUDA 13 libraries.
Previously both learned methods passed the same-method CPU fallback after the
native GPU probe failed on missing cublasLt64_12.dll. No driver installation can
replace these user-mode runtime dependencies.

Pinned official redistributables are CUDA Runtime 12.8.90 and cuBLAS 12.8.4.1
(CUDA Toolkit 12.8.1), and cuDNN 9.8.0.87 for CUDA 12 / Windows x86-64.
`packaging/neural-runtime-assets.json` records source archives, official SHA-256,
sizes, exact archive LICENSE hashes and all 11 selected DLL hashes. CUDA's
Attachment A expressly lists the runtime and BLAS DLLs, including versioned
names. The actual cuDNN archive LICENSE chapter 8, section 2 explicitly grants
redistribution of runtime .dll/.so files subject to the SDK terms. Exact archive
LICENSE texts, versioned acknowledgements and Boost text are retained offline.
The application license already excludes third-party components; it is unchanged.
This closes this additional runtime's component review, not the separate
corresponding-source/build/notice findings for other native dependencies.

DLL lookup adds `app/photomesh/resources/neural-cuda12` only to pinned modern
engine child environments, after engine-owned bin/lib. It never mutates the host
PATH, Python/Qt environment, driver or legacy lookup. No algorithms, weights,
keypoint limits, numerical tolerances or project coordinates are changed.
Existing same-method CPU fallback remains available. Review covered all
child_env callers (capability probes, preflight, PipelineRunner and fastpipe).

Both learned methods passed actual GPU extraction/matching and incremental
mapping on four retained public photographs: all four cameras registered;
ALIKED/LightGlue 165 points, SIFT/LightGlue 195. Loaded DLL paths confirmed the
private CUDA 12 location. Explicit CPU runs also registered all four cameras
(167 and 339 points). CPU/GPU feature backends are not bit-identical; these are
runtime/registration checks, not an independent survey accuracy certification.
Evidence is retained in `Lens2Mesh-validation-evidence/neural-runtime-105/`.
62 focused tests passed (environment isolation, authentication, partial-update
selection, malformed payload rejection, native-resource rollback and existing
engine/updater contracts). The initial local test attempt hit the sandbox's
overlong TEMP path; rerunning under a short disposable F: test path passed.

Setup staging and incremental preparation share one verified build-time helper.
The BAT downloads only the changed app archive and needed official components,
verifies their hashes and prepares the payload before application mutation.
It does not redownload unchanged Python/engine bundles. Subsequent updates omit
unchanged neural components. Existing atomic apply, backup and rollback cover
the added app-private DLLs. Runtime identity includes the manifest. This first
addition requires about 1.24 GB download / 1.80 GB installed DLLs; no entire SDK,
headers, static libraries, developer tools or driver is installed.

Manual review: no menus, settings, defaults or documented processing workflow
changed; retain the approved 119-page PDF unchanged. Public release remains
conditional on the independently recorded remaining native source/notice gate.

The exact app iteration is `b8b2b9f0ab8e691c37e55452606ce5b52032b973`.
General run43462827366 passed925 Windows /921 Linux regressions (9/13 skips),
plus the existing numerical checks and2 Mesa overlay checks. Actual BAT
run43463385549 passed87 installed offline regressions, native PLY/mesh/DEM,
package-lock, exact11 DLL/notice checks and byte-exact app/137 Qt file rollback.
Verified artifact14057422779 SHA256
`5bd414d639d257266b922e2f1e948ce51e1a603bb3dfa048280969b0ccffdec7`;
BAT SHA256 `8dda6a4a125f547a4e264eba248e66070afdce5cff2266bde1c014f4af55b39e`.
The BAT is independently reproduced byte for byte and pins artifact commit
`0431030dcc91482cdf4e63b8a5413be80aaeed8d`, delta ZIP3,415,812 bytes SHA256
`08ab6184a90702e7d142558c0b406ece14c12bec7293ccd5b1083de2f508e8c1`.
Offline local preparation/application/rollback independently restored334 exact
fixture files, with sockets disabled. The legacy3.8 SIFT GPU probe passed with
no private-runtime lookup; modern dense Low fresh13.45s/70,992 points and
cached2.20s/70,984 points passed with all four map hashes unchanged. These
fusion count differences remain the previously established parallel variability.

The later build-stage safeguard excludes only the absolute generated private
DLL source directory, preserving the differently located license directory.
Setup always recreates the DLL stage from pinned assets; a local developer's
ignored probe DLLs cannot bypass verified preparation. PowerShell parsing and
targeted static checks passed. This safeguard changes build staging, not the
tested app or delta payload.

### Dynamic dependency closure and final runtime

The first 11-DLL iteration above was extended after review of NVIDIA's cuDNN
runtime-loading documentation: runtime-compiled engines require NVRTC and its
version-matched builtins through dynamic loading; a direct PE import scan alone
cannot establish their absence. The final set therefore contains13 DLLs,
including NVRTC12.8.93 (`nvrtc64_120_0.dll`, `nvrtc-builtins64_128.dll`). Both are
expressly listed in CUDA Attachment A and carry the same original archive
license as the other CUDA12.8 components. Headers, static libraries and alternate
NVRTC compiler DLLs are not staged. Official archive SHA256 is
`a63302a077f0248a743a1a7caa7dbd80d0fac56c6cfa9c41fa05fac9b7e5eda5`.
The final initial download is1.55GB /1.89GB installed DLLs. All archive/DLL/notice
hashes remain explicit in the preparation specification.

A real kernel compiled to compute_86 PTX with the private NVRTC and builtins.
The first standalone harness attempt set AddDllDirectory alone; NVRTC's internal
loader also needs PATH, which production child_env already supplies. Repeating
with the actual child PATH contract passed, without app or system changes.
Both learned methods additionally passed at the application's2048-pixel ALIKED
limit and4096 features: all four public cameras registered;1122 ALIKED points,
991 SIFT/LightGlue points. Full commands, loaded modules and photos are retained
in `neural-runtime-105/final-public-gpu`; compiler proof is `nvrtc-result.json`.

Independent inventory review also caught line-ending normalization of the cuDNN
LICENSE in the first Git blob. The already-tested BAT carried the correct raw
archive bytes; source checkout preservation was corrected with forced
renormalization under the existing `-text` attribute. A real-file license-hash
regression and installed-candidate validation now enforce this.63 focused tests
pass with the final four-component specification. Other native source/notice
findings remain separately open; this review grants no blanket clearance.

Final13-DLL acceptance: source31636bcc8b874aa4826d65b8bd9f2959dddd2fc0,
general43466969065 passed926 Windows /922 Linux tests (9/13 skipped), plus2 Mesa
checks. Full43466969080 passed and independently retained inventory shows25,280
candidate files, all13 exact new DLLs/original license hashes, and26,196 original
files restored exactly. Artifact14058919638 SHA256
`4dacfa86439b2151c2b9448160fdb7a2567767b19d84d7aa2197521e5827dc04`.
Actual final BAT43467111035 passed87 installed tests, native terrain/PLY/manual,
all13 DLL/notice checks and137 Qt file rollback. Artifact14057988851 SHA256
`f234d162d4780260662ca2065af71e87f8c8354961f18baa6471e8d658db08cb`.
Delivered BAT SHA256`57820debe410138674b540321a47d5d23b1f3c8d06d5b19bb4b8c0061d323242`,
independently reproduced and read back from publication. It pins artifact
e289f71dfa4dc24f970b7ba5ff98b149cbcb72bb, ZIP3,416,234bytes SHA256
`74583407ec709d597ae17610f6f261a10dc89b1c5bb8958a925f118f8fd2dfe8`.

**Open Unicode-install issue; not approved for final Setup:** additional real
GPU testing showed that ONNX1.30's dynamic cuDNN loader uses ANSI PATH functions,
so an installation path containing Persian characters fails neural GPU loading.
The upstream executable also loses non-ANSI model paths. The delivered test BAT
works on the user's current ASCII installation; do not claim full Unicode neural
support. A disposable BSD-executable RT_MANIFEST/activeCodePage UTF-8 prototype
passed GPU model loading, with all non-resource PE sections unchanged. It is
retained as evidence, not included in the delivered candidate, updater or Setup.
Finishing that fix requires explicit hash-bound native-executable patch packaging
and its installed/rollback tests. The user has not approved releasing this
limitation in final1.0.5. Preserve the release gate along with the independent
native corresponding-source/notice gate. No system locale or installed engine
was changed. Legacy behavior and the approved PDF remain unchanged.

### Persian installation path fix (targeted follow-up)

Resolved in the targeted candidate6404d436dbe2391179fc38decf5a67669501e9d2.
Only the two modern BSD COLMAP executables' Windows RT_MANIFEST resources gain
Microsoft's per-process activeCodePage UTF-8 setting. The original unsigned
inputs and deterministic outputs are pinned in reviewed-engine-patches.json;
every non-resource PE section remains byte-identical. No system locale, legacy
engine, model weights, CUDA DLL or numerical source is changed. Modern Windows
1903+ supports this process setting. Full engine preparation uses the same helper.

The updater permits only those two exact before/after pairs, rejects other
native changes/removals and preserves its review plan with rollback.28 focused
updater/launcher tests passed, including rejected altered inputs/outputs/removals.
Actual CLI application in an installation path containing spaces and Persian
characters passed both learned methods on real GPU and CPU, registering all4
public cameras each (GPU165/209 points; CPU167/339). DLLs remained in the private
Persian app directory, not the executable directory. Actual CLI rollback restored
both engines and runtime/provenance metadata byte-exactly. No user installation
was changed during validation. The approved PDF is unchanged.

The4-file targeted patch is24,387,005 bytes, SHA256
f5f299733995fab53a9cc4ba34b0b4606b5672e8afe8dd6e6f9681e06fdfffbb.
It targets the user's authenticated installed neural-runtime candidate and
downloads no Python, engine bundle or NVIDIA archives. Full unrelated suites
were not repeated for this acceptance; numerical code is byte-identical and
the native path behavior and recovery were tested directly. The separate native
corresponding-source/notice gate remains open before final release.

# User steering after Persian-path delivery (2026-11-13)

The user defers remaining item2 (native dependency source/build documentation,
including GLOMAP) to version1.0.6 and explicitly asks to wait for their test result.
Do not perform further changes, tests, Setup builds or publication while waiting.
This scope deferral is not a statement that previously unknown redistribution
conditions have been verified. Retain existing evidence and original license texts;
do not relabel unresolved provenance as cleared. Resume from the user's feedback.

# Reported Unicode Poisson input/output correction (2026-11-13)

User report20261113_215528 fails inside Open3D read_point_cloud before Poisson.
For Windows non-ASCII PLY paths, mesh.py now uses the existing independent PLY
codec to populate Open3D geometry, preserving float64 coordinates/normals and
RGB, and writes mesh output through the same codec. ASCII native I/O, sampling,
Poisson parameters, cleanup, decimation and publication remain unchanged.
The Delaunay-input reader uses the same path-safe conversion. task_env explicitly
sets UTF-8 stdout/stderr to match PipelineRunner decoding and prevent a filename
log from failing after successful publication.

Targeted actual Windows tests: exact point/normal/RGB equivalence to native ASCII
reader, exact vertex/normal/colour output versus native mesh writer, triangle
roundtrip, real2000-point Poisson with Persian input/tmp/output producing1000
faces, simulated failed write preserving previous model, and actual
photomesh.tasks subprocess with Persian config/output/logs all passed. No input
photos, project data, numerical settings, or engine binaries are modified.

## Exact mesh sections and equal-scale fitting (2026-11-13)

The section UI now uses all triangle/vertical-plane intersections clipped to
the endpoint span, retaining floors, vertical faces and reverse overhangs.
Coplanar faces show their clipped boundary, with shared interior edges removed.
Independent segments never acquire artificial connecting lines. The legacy
sampled `MeshSurface.section` method remains for compatibility; the UI uses
`section_segments`. Profile slope picks use the nearest actual segment in
screen space and reject different connected components.

The 3D display uses the same exact intersection segments in model coordinates,
with surface depth testing instead of a straight chord painted over the model.
The middle grip sits on an actual section segment nearest its midpoint; endpoint
and paired translation gestures, navigation, manual coordinates, photo/ortho
picking and existing stale/cancel/session guards remain. `Fit 1:1` fits the full
profile with equal horizontal and vertical units and retains that aspect lock.

Review scope: geometry/BVH, worker results, coordinate transforms, plot picking,
GL display, shared gestures and dock lifecycle; callers and old envelope references
were searched. No alignment, GPS, marker, mesh-building or project-format code
changes. Seven new behavioral cases plus the existing survey/workflow tests:
44 passed offline. Ruff F/E9 and diff whitespace checks passed. On an analytic
80,000-triangle sloped mesh, exact extraction took0.106s versus0.153s for the old
512-sample profile; maximum height error7.11e-15 model units. This is a focused
benchmark, not a capacity guarantee for every mesh. Native OpenGL visual/gesture
acceptance remains the user's test; offscreen rendering does not establish it.

Only five changed application modules go into the test updater. The approved
PDF is retained: user requests updating only its section material after accepting
this test. No Setup or public release is authorized by this candidate delivery.

### Candidate acceptance and focused manual update (2026-11-13)

The user explicitly confirmed successful section/Fit 1:1 testing in PhotoMesh
Studio-4 and approved the previously deferred manual update. Updated only the
Cross Section chapter (pages 116-117): exact multi-layer intersections, coplanar
boundaries/gaps, surface-bound centre handle and 3D line, equal-axis Fit 1:1 and
component-aware slope picks. Replaced its screenshot with the actual tested
panel PNG, embedded losslessly. The manual remains 119 pages; every unaffected
page has identical extracted text and decoded page content to the accepted PDF.
Contents pagination and 72 bookmarks remain unchanged. Both affected pages were
rendered and visually inspected. No application code or installer was changed.

Editable source and original screenshots remain in
`F:/CodexProjects/photomesh-guide-105`; baseline, rendered QA and verification
evidence are retained in
`F:/CodexProjects/Lens2Mesh-validation-evidence/section-manual-update`.

### Final release authorization and branding (2026-11-13)

The user explicitly requests building and publishing the final 1.0.5 installer
and removing obsolete public branding. The repository is renamed to Lens2Mesh;
canonical links, current installation/update pages, root README, issue template
and the project's own licence heading/scope name are updated. Licence conditions
and third-party licence texts are unchanged. Setup removes obsolete per-user
shortcut names and retains its existing upgrade AppId. Internal project/settings
identities and historical evidence remain for compatibility/provenance.

Maintainability review: inspected build/staging and installation workflows, manual
hash checks, generated neural runtime validation, current public download links,
licence copy and shortcut consumers. Updated outdated manual validation pins and
excluded only separately authenticated generated neural runtime files from the
source-file identity comparison; installed DLL/notice checks remain required.
44 targeted branding/documentation/report tests and diff whitespace checks passed.
The final workflow requires successful exact-source general and installed
candidate checks, fresh/custom Unicode installation, upgrade, native processing,
offline Help, shortcut/uninstall and external-data preservation before publishing.
Native build-provenance and point deletion remain deferred as previously agreed.

### Published 1.0.5 installer (2026-11-13)

Validated release source: `2c557669381cc651c4e9ab8ac5ac8aba9cea124b`.
[Final build and publication](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/43486717526)
passed fresh/custom Unicode install, upgrade, shortcut targets, offline native
terrain/PLY/neural runtime/manual checks, uninstall and external-data preservation.
Both installations authenticated all 13 private DLLs and original NVIDIA notices.
The [general checks](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/43486717578)
passed on Linux and Windows; Windows recorded 937 passed and 9 skipped.
The [installed candidate/inventory/rollback](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/43486717574)
also passed with 937 tests and 9 skips. These are automated checks, not a new
claim of complete hardware or native source/build-provenance clearance.

[Public release](https://github.com/behdad-nayyerpour/Lens2Mesh/releases/tag/v1.0.5):
`Lens2Mesh_Setup_1.0.5.exe`, 1,674,504,611 bytes, SHA256
`e4f2b42f33cfcf53b652d9e16228310b3e9b029091725d6985ff18cf5c57b990`.
The authenticated uploaded download was compared byte-for-byte before publishing;
the public checksum and GitHub asset digest independently match the build log.
The release includes the updated 119-page manual with SHA256
`8af845b74331ca66cb28b3fd44af752189d3199c699b28a9ddd754eda448c940`.
Main was fast-forwarded to the validated source and v1.0.5 was marked latest.
Older release titles/descriptions and the archived 1.0.4 asset names are rebranded;
the 1.0.4 installer bytes/hash remain unchanged, with a corrected named checksum.
Future baseline-download workflow names now match that archived asset rename.
Historical tags, internal project/settings identities and original audit evidence
remain available. Exact logs and public asset records are retained under
`F:/CodexProjects/Lens2Mesh-validation-evidence/release-105-job-*.log` and
`Lens2Mesh-1.0.5-publication.json` in that directory.

### Low-risk installer size evaluation (2026-11-13)

The user approves first measuring safe cleanup with all application features and
the single-file offline installer retained. Optional GPU splitting is not part
of this iteration. Scope: installer storage and pinned non-runtime omissions;
no application processing, numerical algorithms, user settings or PDF changes.

Reviewed staging/copy rules, exact release inventory, runtime lock and native/UI
validation callers. Inspected large-file groups and searched runtime callers of
test/debug material. Whole package/test-directory removal is deliberately not
implemented without a stronger dependency contract. The only omission candidates
are exact Python HTML documentation and modern Qt-plugin PDB symbols: 629 files,
214,519,949 uncompressed bytes. The existing pre-neural inventory also identified
314.55 MB of exact duplicate bytes across paths. These figures are not promised
Setup savings. Installed duplicate paths remain separate; Inno references one
canonical source after SHA256 plus exact byte comparison. No native code is edited.

Safety: review plans reject traversal/runtime-file omissions and changed bytes;
linked entries and generated output inside the source stage are rejected. Stage
contents remain untouched. Tests reconstruct installed bytes from generated Inno
entries and verify failure contracts. Ten targeted payload/lock tests and Ruff
F/E9 pass. Manual assessment: no user workflow/control changes, so the approved
119-page PDF is retained unchanged. A remote comparison builds from exact released
1.0.5 and checks installed contents/native processing rather than repeating closed
audits or unrelated reconstruction benchmarks. Public replacement is not automatic.

#### Measured result and compact publication preparation (2026-11-14)

[Comparison run43494082044](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/43494082044)
passed. The compiled complete offline Setup is 1,519,473,594 bytes versus
1,674,504,611: 155,031,017 bytes saved (9.2583%). SHA256:
`4d50eaf5354713ff79aa88aec06237a861287753999e2cb0c1e36b5db8ad207d`.
Of 25,282 original files, all 24,653 retained installed files match byte-for-byte;
629 reviewed documentation/symbol files are omitted. 2,147 duplicate destination
copies share 238,932,076 uncompressed bytes in installer source storage; each
destination remains a separate installed file. Package versions, native PLY/DEM,
offline manual/UI structure and all 13 private GPU DLLs/notices passed.

Initial offscreen QA captures showed missing font glyphs. The installed binaries
and fonts are byte-identical; this is the known offscreen font-discovery issue,
not a runtime-font change. The installed validation helper now explicitly loads
Windows Segoe UI only in offscreen Windows QA, asserts Latin glyph coverage, and
recaptures readable UI as a gate before public replacement. No application font
or PDF content is changed. Compiler FileVersion reported 0.0.0.0, so no claim of
a separately authenticated compiler-version match is made.

The user had authorized final publication and approved this size-reduction work.
After measurement/installed validation, compact storage becomes the build default
with an explicit opt-out. The replacement workflow authenticates the exact tested
EXE, retains the prior public EXE/checksum in a 90-day rollback artifact, checks
readable installed UI, then replaces only the public Setup/checksum and verifies
the downloaded bytes. It preserves the existing 1.0.5 tag and full manual.

### User redirects to compact base plus optional NVIDIA package (2026-11-14)

The user says the compact all-in-one is still too large and explicitly requests
retaining its reduction while separating NVIDIA. Superseded compact publication
run43497570486 was cancelled. The current scope is the same compact storage and
non-runtime cleanup plus separation of only the 13 private CUDA12/cuDNN DLLs for
ALIKED/LightGlue. COLMAP CUDA13, legacy GPU engines, CPU engines and offline model
weights remain in the base. No application processing code is changed.

Inspected `engine.execution_settings` and all feature-argument/probe callers: a
failed GPU compatibility probe already retries the same method on CPU and caches
that decision for the session. Real local probes using the exact pinned modern
engine and synthetic images on RTX3080Laptop confirmed both ALIKED/LightGlue and
SIFT/LightGlue return CPU without optional DLLs, and GPU after adding the exact
13 DLLs. Evidence: `split-neural-local/native-proof.json`; no personal project,
installation, driver, toolkit or settings were changed. These are functional
extraction/matching probes, not a new photogrammetric accuracy benchmark.

The optional installer reuses `apply_patch` path, app-close, hashing, OS-lock,
backup and rollback rules. It accepts only Lens2Mesh1.0.5, adds only missing exact
DLLs/descriptor, does nothing for identical existing files, and refuses differing
GPU files. Original NVIDIA notices and the application licence are preserved.
Base managed deletion rules preserve the private optional directory during
upgrades; normal base uninstall removes it. The review covers these installer
callbacks, shared-updater contracts, generated storage entries and documentation.

The user separately approves updating only installation/add-on material in the
manual. The complete PDF remains119 pages; only page5 content changes, rendered
and visually verified. Other118 page streams/bookmark pagination remain unchanged.
New PDF SHA256 `83bcd31c0ddea7277227045311f5f74117164d7bf96b8dac933296cae02f9faf`.
No screenshots or unrelated chapters are redesigned. Initial two local test
failures were fixture-only (a dynamically recomputed expected hash and Windows
newline translation); fixed fixtures then passed. Targeted payload/add-on/native
engine/runtime/manual tests pass; remote full installer tests will exercise base
alone, detected Unicode targets, add-on repeat/rollback/reapply, base upgrade
preservation, invalid-target rejection and normal uninstall before publication.

First split run43502578265 built the 598,550,777-byte base (64.255% reduction)
and 923,121,476-byte add-on. Base retained24,640 files, with unchanged runtime
bytes; all base CPU/native/UI/manual checks passed. Add-on installation failed
the app-close guard and was NOT published. Diagnostics43505590473/43507077720
showed correct explicit/automatic Unicode target detection; the problem was
not destination selection. `ensure_closed` resolved missing system executable
paths as `Path('')`, i.e. its working directory. Inno starts Python in its own
directory by default, so system PID0 was incorrectly classified as app Python.
The exact failure was reproduced locally with the cwd set to a disposable
root/python; it now passes after ignoring missing executable paths while still
checking app command arguments. Real owned Python jobs and app arguments remain
blocking. No broad ancestor/process exemptions were retained.

Inno also returned0 after an ssPostInstall exception, so a custom nonzero exit
code now accompanies helper failure. The retry reuses the exact verified base,
rebuilds only the corrected add-on, and tests a real active Python job to ensure
the guard still rejects installation without changing DLLs. Targeted updater,
add-on, runtime and payload tests:54 passed. No faulty add-on was published.
