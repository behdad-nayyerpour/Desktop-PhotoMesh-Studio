# Survey numerical verification, 2026-11-14

Scope: review and verify marker residuals/RMSE, checkpoint isolation, WGS84
ECEF/UTM/ENU and mesh sections. This is a follow-up verification of 1.0.5, not
an application release. Baseline source:9a6e02c50e342dfc28090d1ee2e925800e9d1c64.
No application, installer, user project, photo, setting or manual was changed.
No manual update or incremental application updater is necessary for these
read-only developer/test tools. The user's distributed-processing work remains
stopped and is unrelated to this verification.

## Existing evidence rerun

135 tests passed in26.37 seconds, with no skips, in these suites:

- test_numerical_reference_104.py (camera equations, adjustment, residuals,
  reference validation and UI/report lifecycle).
- test_coordinate_frames_105.py.
- test_survey_geometry_105.py and test_section_exact_105.py.
- test_survey_metadata_105.py.
- test_survey_interaction_105.py, test_section_workflow_105.py and
  test_reference_lifecycle.py.

The Qt tests used the offscreen platform and temporary settings/reports, with
outgoing networking blocked. They are not native OpenGL acceptance tests.

## Gaps addressed

Some existing allclose assertions combine an absolute limit with NumPy's default
relative tolerance; at large map origins this can permit excessive differences.
New independent checks use absolute error only. The existing ENU test also uses
the application's origin/basis in its expected result; the new comparison uses
PROJ's full cartesian/topocentric pipeline instead, independently checking axes,
origin and scale. Existing tests remain unchanged.

tools/verify_survey_math.py records expected/actual values, maximum absolute
error, tolerance and units in HTML/JSON, with imported file hashes and runtime
versions. Wrong module origins are rejected. A missing independent comparator is
an ERROR, never an implied pass. The CLI rejects reports under the application
directory, suppresses bytecode writes and disables PROJ network retrieval.
It runs synthetic inputs in memory and never opens a user project or GUI.

30 comparisons passed both against source and the installed Windows application:

| Contract | Absolute numerical tolerance |
|---|---|
| Signed residuals, separate control/check RMSE and counts |1e-12 (metres for residuals) |
| Known 3-4-12 triangle, reversal, translated origin, unavailable vertical slope |1e-12 for finite metrics; exact boolean checks |
| Literal WGS84 equator/pole ECEF coordinates |1e-8 m |
| ECEF forward/inverse vs independent PROJ |2e-7 m;2e-10 degrees |
| UTM forward/inverse vs independent PROJ, north/south/high latitude |0.001 m;1e-8 degrees |
| ENU vs independent PROJ topocentric pipeline |2e-7 m |
| Analytic oblique plane section, reversed direction and large origins |2e-8 m |

These are numerical regression limits for the stated synthetic inputs, not
accuracy guarantees for surveyed products or arbitrary coordinate domains.
UTM inputs are deliberately selected within the chosen zone's area of use.

Six additional pytest cases passed in1.42 seconds. They run the independent
harness, prove an intentionally wrong 3D-RMSE denominator is detected, and test
actual georeferencing with and without bundle adjustment. Changing only a check
point's reference, or only its measured image positions, leaves adjusted points,
camera poses and initial similarity unchanged within1e-10; check residuals change
to their independently computed expected values. No optimizer is mocked.
During test development, an assumed minimum change in residual norm was wrong;
it was replaced by an analytic answer. That answer requires an undistorted
pinhole fixture, so its radial coefficient was explicitly set to zero. These
were test-fixture corrections, not evidence of an application defect.

## Maintainability review and limits

Reviewed georef.marker_errors/rmse/run_task and their check/control selection,
coordinates frame conversion, survey_geometry distance/section contracts, and
existing numerical and interaction callers/tests. The new tool consumes the
public calculation functions; it does not duplicate processing implementations
or modify their behavior. Separate analytic equations/PROJ supply oracle answers.
Ruff F/E9 passed on the new Python files. No processing hot path was changed;
no performance improvement or whole-repository dead-code audit is claimed.

Evidence is retained outside source in
F:/CodexProjects/Lens2Mesh-validation-evidence/numerical-audit-20261114/:
baseline.log/xml, additional.log/xml, numerical-report.html/json, installed.log,
installed-report.html/json. Installed application files were read only.

## Repeat and remaining work

For source, run with the existing development Python environment:

```powershell
python tools/verify_survey_math.py --app-dir . --output F:/Lens2Mesh-QA/math
python -m pytest -q tests/test_survey_math_audit.py
```

For installed code, keep Check_Survey_Math.bat and verify_survey_math.py together
outside the installation. Run the BAT and enter the installation root containing
app/python/tools. The BAT uses that installation's Python, writes HTML/JSON under
reports beside the BAT, and exits nonzero on failed/incomplete checks. This is a
read-only numerical checker, not a patch installer. It needs no download/pytest.
The delivered BAT was also executed successfully with the installed application's
Python: all30 checks passed, exit0. The report is under checker/reports/ in the
external evidence directory. None of the three measured application-module hashes
changed during verification.

Remaining: independent surveyed checkpoints and known-height surfaces on an
end-to-end real project; reference-measurement uncertainty and required product
accuracy must be specified first. Broader DEM/DTM, orthomosaic, area/volume,
export, ground-classification and native-engine numerical comparisons are not
completed by this focused run. Existing gap/overhang/lifecycle tests passed, but
no blanket correctness or survey-standard certification is asserted.

## Follow-up without a user-supplied surveyed project

The user has no project with independent surveyed checkpoints. This does not
block synthetic verification. Reran test_shapes.py, test_ortho.py and
test_terrain_bundle_105.py:44 passed in23.67 seconds, no skips. These existing
regressions cover area/perimeter/cut-fill volume, distorted-camera projection,
shape import/export, synthetic orthomosaic pixel placement and raster exports,
DEM heights, ground labels, DTM coverage and LAS/LAZ attributes. They are not
new independent surveyed-project accuracy evidence, and their pre-existing
tolerances/definitions remain in force.

The first attempt had31 passes,2 skips and11 fixture errors because the old
development environment's Open3D lacked its Dash dependency. No numerical result
was produced by the failing fixtures. The successful run used the installed
runtime's existing site-packages via process-local PYTHONPATH, while conftest
selected this source checkout and isolated settings/reports. No dependencies or
application files were installed/replaced. Evidence: products.log and products.xml
in the same external evidence directory. Required testing then completed; there
is no pending product-test job.

Public benchmark discovery (metadata only; no dataset downloaded or evaluated):

- https://isprs.org/resources/datasets/benchmarks/ lists the ISPRS/EuroSDR
  multi-platform calibration/orientation and dense-matching benchmarks. Its
  detailed MultiPlatformPhoto page failed to load during this review, so data
  access, completeness and licence have not been confirmed.
- DLR AerialRefMatch describes51 images, reference true-ortho data and independent
  checkpoint evaluation for single-image pose estimation. This is not yet selected
  as a substitute for a complete multi-image reconstruction/checkpoint project:
  https://www.dlr.de/en/eoc/about-us/remote-sensing-technology-institute/photogrammetry-and-image-analysis/public-datasets/aerialrefmatch-a-benchmark-dataset-for-testing-matching-algorithms

Before a public real-data run, verify access/licence, imagery and observations,
independent check coordinates, CRS/vertical datum, reference uncertainty and a
fixed control/check split. Do not infer surveyed accuracy from inter-software
agreement or from a dataset's title alone. No accuracy certification is claimed.

### Small real-image input prepared

MicMac Gravillons (four images, listed8.3M) was identified but its official HTTP
and HTTPS endpoints timed out for both agent and user; no test result is claimed.
The alternative Esri legacy tutorial describes12 images, but its download alias
now resolves to public item d99cc2563beb4208a3db4e60e9384b43:195 images,1,721,966,073
bytes. The revised item's actual inventory/metadata were inspected by HTTP ranges.

Prepared a private QA subset from18 original images selected by camera proximity
to12 supplied reference points. Only156,881,452 compressed image bytes plus small
metadata were downloaded, not the full archive. Originals, hashes, item metadata
and scripts are retained under external evidence real-reference-light/.
Images in Esri_BuildingE_Light_18.zip are resized to at most2048 pixels with
updated EXIF dimensions; this is explicitly a derived lightweight input.
The16,516,954-byte ZIP has SHA256
32576ae1a964b308021f101f37484fb79b485918b6a9aa1fe13f444a27a16b36.

JPEG integrity and ZIP CRC passed. Lens2Mesh parsed the derived reference CSV as
12 unchanged XYZ positions, with a proposed fixed6-control/6-check split.
No image observations were invented. Reference heights are EGM96 orthometric;
the matching Esri developer tutorial explicitly labels the horizontal coordinates
EPSG:26911. Original accuracy fields and item usage terms are retained verbatim;
their statistical confidence interpretation is not assumed for adjustment weights.

Alignment connectivity, target visibility/measurement and actual checkpoint
accuracy are still unverified. Do not confuse this prepared input with a passed
real-project benchmark. Data/originals were not published to the repository.
Source: https://developers.arcgis.com/python/latest/guide/create-trueortho-dsm-from-drone-imagery/

### Superseding input: native alignment failure and corrected connected subset

The user ran the18-image input and obtained5/18 cameras and941 tie points.
Inspected only the explicitly supplied BuildingE_Test project; queried a copied
database snapshot in evidence space, never writing the user project/database.
All18 images had features, but strong matches clustered into weakly connected
groups. Re-running the installed incremental-mapper policy on the copied DB
reproduced exactly5 cameras/941 points. The initial subset was not adequately
validated before delivery and is superseded for the real-project test.

Added11 original bridge-candidate images (95,779,419 compressed bytes) selected
from short GPS-proximity paths and resized consistently. Native validation of
the29-image candidate produced two reconstructions,10 and20 images; it did NOT
pass a29/29 acceptance check and was not delivered as a successful full block.
The larger coherent component supplied a20-image candidate. The existing
incremental export path names sparse/0; the29-image test illustrates why first
output and largest output are not interchangeable. No application selection
logic was changed in this data-repair task.

Validated that20-image candidate from scratch with the installed app's actual
colmap.align_steps, calibration sharing, native feature extraction/matching,
incremental mapping and export, in an owned workspace, without inherited DB:
20/20 cameras;9496 tie points; median observation reprojection0.2804373814 pixels,
RMS0.6375670110 pixels. Settings: SIFT/Exhaustive/Incremental/Full, key limit24000,
compatible calibration sharing on, guided matching off, no camera GPS constraints.
A temporary CLI harness initially mistook a pipeline log entry for an engine
command; its dispatch was corrected before the successful fresh run. No app code
was implicated by that harness error.

Deliverable: Esri_BuildingE_Connected_20.zip,18,853,856 bytes, SHA256
54aaeab07582d2dbf226e79a63dbf6e0cae1ba90dff75f10ecffbceaa9a269e7.
Contains only20 selected images, source/terms, exact preserved XYZ references,
hash manifest and alignment-validation.json. ZIP CRC and image hashes pass.
Use a new project, not the combined18/29-image inputs. Evidence:
mapper-reproduction.json/log, bridge-validation.json, connected20-validation.json,
connected20-*.log and connected20-package.json in real-reference-light/.
All files in the user's existing sample project and installed app were unchanged.
Reference-target identification, image measurements, checkpoint XYZ accuracy and
surface/section comparisons remain outstanding; reprojection alone does not
certify ground accuracy.

### Measured Building E controls, holdouts and adjustment investigation

Read the user's saved BuildingE_20_Test project without modifying it. Original
GDB attachment GlobalID joins supplied 36 ground-identification photographs.
The user measured controls 10/12/15 and checks 9/13/14/2 on three photos each.
Only controls were included in optimization. Source GDB geometry is a different
native CRS from the supplied UTM/EGM96 CSV; this audit follows the CSV and matching
Esri tutorial, not an independently certified datum conversion.

Three-check RMS (XY/Z/3D metres) was .07499/.18787/.20228 for similarity only,
and .13455/.12518/.18378 after fixed-calibration bundle adjustment. The additional
previously unused check 2 had Z error +.47063 m; all four checks then yielded
.12677/.25909/.28844 m. Independently implemented pinhole/radial projection with
SciPy point optimization reproduced the saved marker estimates (largest tested
coordinate discrepancy below 1e-7 m). This confirms the arithmetic, not absolute
survey accuracy. Free image triangulation and constrained optimizer marker XYZ
are distinct estimates; the existing report displays the former.

Repeated alignment from the 20 retained original images registered 20/20 with
8828 points. Using the existing manual pixels rescaled to original dimensions,
four-check 3D RMS was .15131 m for similarity only and .19639 m after adjustment.
This is an approximate resolution comparison, not fresh full-resolution target
measurement. Exploratory calibration changes also failed to establish a reliable
accuracy improvement. Never optimize settings or discard checks to manufacture
a favourable benchmark.

An independent small noisy bundle oracle uses SciPy's differently parameterized
least-squares solver and explicit pinhole equations, including vector Huber loss
on automatic observations. It exposed a separate write-back defect: after the
accepted LM solution, all tie points were unconditionally replaced by unweighted
ray intersections. Cameras were unaffected, so this does NOT explain the marker
holdout errors above. Before the fix, sum-of-squared equivalent robust residuals
was 123.68169 versus the oracle's 114.03655 in the outlier case (and 1.67715 versus
1.67465 without the outlier). Preserve jointly optimized selected tie XYZ and
re-intersect only the remaining ties; refresh error metadata for every point.
The two oracle cases now agree within 1e-5 objective units and camera positions
within 2e-4 m. Existing marker/control/check calculations are unchanged.

On the real saved sample, tie observation RMS changes from .6617260 to .6608608
pixels; marker estimates/camera poses retain the prior values. Do not describe
this fix as eliminating the 47 cm holdout error. Further reference coverage and
fresh target measurements are required before a ground-accuracy acceptance.

Maintainability review: inspected gcp_bundle_adjust, retriangulate, their direct
callers, marker diagnostics, Schur solve and incremental-patch boundaries. Kept
the existing triangulation implementation and added an optional preservation
argument; no duplicate adjustment engine, unrelated cleanup or legacy removals.
No claim of a new repository-wide dead-code audit. No UI, installation workflow
or manual text changes; the approved manual is unchanged. Application delivery
is an incremental test candidate only, with exact hashes, close-app guard,
backup and rollback. No Setup or public release is authorized by this audit.

Validation: 166 tests passed in 12.34 s across the independent oracle, numerical
reference, survey audit/capacity, reference lifecycle, dense/GCP and patch suites.
The first patch-suite attempt hit Windows path-length limits in the sandbox's
deep default temporary directory; rerunning the complete selection with an
explicit short evidence-workspace temp directory passed. Ruff is not installed
in the selected development environment; no Ruff-pass claim is made. Python
syntax and git whitespace checks are separate checks.

### Known-answer section reference models (2026-11-14)

Added tools/verify_section_reference.py and four focused regression cases in
tests/test_section_reference_models.py. No application calculation or installed
component changes were necessary. Generated independent ASCII double-precision
PLY inputs for a plane, flat/rise/flat ramp, three-metre hole and vertical wall.
The numerical oracle is explicit closed-form geometry, with absolute tolerances
and no default relative tolerance. A deliberately inverted height sign is
detected by the harness mutation test.

Both the actual installed engine and source passed 46 comparisons: horizontal
and 3D distance, signed height, positive/reversed slope, coincident/vertical
endpoints, exact section elevations/coverage, surface intersection, submillimetre
coordinate detail after double PLY load at a large survey origin, disconnected
holes and vertical segments. Invalid NaN endpoints and zero section span were
rejected. The 3-4-12 reference returns horizontal 5, height 12 and 3D chord 13.
The broken ramp has horizontal 10, height 4, endpoint chord sqrt(116), and surface
profile length 3+5+4=12. The UI 3D length describes the chord, not profile length.

56 related regression tests passed in 16.10 s, without skips: reference models,
survey geometry, exact sections, section workflow, interaction, UI and metadata.
Two source Qt cases exercise the actual section worker and numeric labels.
Separate installed-Python/installed-MainWindow runs opened generated projects,
used the section controls/workers and confirmed both reference endpoint metrics
and displayed text in metres. Isolated settings and report directories avoided
personal application state. Offscreen Qt lacks usable font/OpenGL rendering in
the captured panels: this is numeric/control-path evidence, not native on-screen
rendering or physical mouse-picking certification.

Evidence: external section-reference-20261114/{installed,source}/report.json/html,
regression.xml, installed-ui-result.json and package-verification.json.
Lens2Mesh_Section_Reference.zip (10711 bytes, SHA256
1471f2dd94ca619e46d7119ba5c7b00fa0959f178af6257d36a2ff5e78eae8c3)
contains portable reference meshes/projects, reports and an optional offline
BAT checker. Relative model paths survive relocation; archive CRC passed. The
checker writes results beside itself and does not patch the application. Its
PowerShell entry point passed against the real installed Python with the install
root explicitly supplied; sandbox-local AppData/registry discovery did not locate
the personal installation, and stopped before running the audit.
No Setup, manual changes, reconstructed-field-accuracy claim, area/volume
acceptance or whole-application correctness guarantee follows from these tests.

### Area and height-volume reference audit (2026-11-14)

Added 21 known-answer cases in tests/test_area_volume_reference.py. Supported
volume semantics are sampled height above/below the least-squares plane fitted
to the polygon boundary's surface elevations. This is not arbitrary watertight
solid volume or overhang integration. A boundary on a roof defines a different
reference plane from a ground apron around that roof.

Analytic cases cover translated small/large parcels, outer-minus-hole area,
flat/sloping surface area, raised blocks/depressions, triangular height prisms,
balanced and unbalanced cut/fill, large-origin volume, missing/partial surface
coverage and boundary-cell error under grid refinement. A real closed 2x2x2 mesh
with surrounding ground, through HeightSampler.from_mesh/Open3D at an explicit
0.1 m integration resolution, returned 8.00001144 m3 versus exactly 8. Float32
ray-height accumulation is bounded explicitly by four height ulps times the
16 m2 apron area (6.11e-5 m3); the scalar analytic tests use stricter absolute
tolerances. Grid integration remains approximate; coarse meshes may require a
finer sampling resolution than their median edge length.

Three defects were reproduced before correction:
- Cross-products on absolute UTM coordinates changed a 0.01 m2 square to
  0.009765625 m2. Translate coordinates locally before signed-area products.
- Relative allclose ring closure treated metre-separated UTM endpoints as
  identical, losing a polygon edge (1 m square perimeter 3 instead of 4 m).
  Use exact endpoint equality, and normalize local polygon measurement copies
  without modifying source/saved vertices. Preserve hole/orientation conventions.
- A one-row surface grid raised in numpy.gradient. Return an explicit
  insufficient-resolution result instead of crashing or inventing zero volume.

Validation: 118 passed, one explicitly native-OpenGL style case skipped, in
27.99 s. Coverage includes the reference cases, shapes import/export/mesh sampling,
shape styles, photo projection, world exports, PLY codec, metadata and patch
apply/rollback contracts. No application library installation was changed; the
test process used existing installed site-packages to exercise Open3D. An initial
run with a missing temp parent and one collection attempt with nonexistent test
filenames were harness setup errors, corrected before the recorded final run.

Maintainability review covered _close, signed area, measure, file-reader/writer
call sites and shape_metrics UI/cache. Existing shape/export/style tests cover
these interactions; no parallel measurement engine or unrelated cleanup was
introduced. New reference oracles are independent closed-form answers, not
copies of the production formulas. No workflow/control change or approved user
manual edit is needed; the manual remains unchanged. This is a hash-bound
single-module incremental test candidate with backup/rollback, not a Setup or
public release. Existing bundle fix must remain installed.

Evidence: external area-volume-reference-20261114/{baseline,candidate}/report.*,
regression.xml and packaged apply/rollback verification. Installed baseline
shapes.py SHA256 is 65c24ff08b95344e061164523940db27a6b8c528c417dcb7968a993c455618fa.

### Retrospective real-reconstruction leave-one-marker-out validation

Executed the actual installed georeferencing task on fresh owned copies of the
original-image 20-camera sparse model. Seven markers have three image-only
refined observations each. In each of seven folds, six markers are controls and
the seventh is wholly excluded (XYZ and image observations) from adjustment.
Ran the fixed settings both for similarity only and fixed-calibration bundle
adjustment, with recorded receiver RMS weights, GPS off and no further tuning.
The user project and reference measurement files were unchanged.

Across the seven held-out residuals, similarity-only RMS XY/Z/3D was
0.12583579/0.08571885/0.15225757 m; maximum observed 3D residual 0.21331840 m.
Bundle-adjusted RMS XY/Z/3D was 0.11649262/0.11171687/0.16140381 m; median 3D
0.14595885 m, maximum observed 3D 0.23498877 m (BldgE-2), maximum absolute Z
0.16297171 m. One of seven bundle holdouts was within 0.1 m; five within 0.2 m.
This does not establish sub-10-cm accuracy. Bundle did not improve all accuracy
components on this dataset; do not automatically equate lower optimization cost
with lower external ground error.

On an actual fold, changed only the held-out XYZ by (+100,-80,+60) m and its
image observations by (+5,-4) px, and re-ran adjustment from the original sparse
model. Camera centres and selected tie XYZ were unchanged exactly (maximum
coordinate difference zero), confirming real-data holdout exclusion.

The earlier 0.136084 m value describes four checks under one fixed three-control
model. It is not the same statistic as seven-fold cross-validation with six
controls per fold. Pairwise lengths from the four-check review model were also
compared with reference-coordinate lengths; maximum absolute discrepancy was
0.214310 m over a 92.833583 m line. These are derived from the same check points,
not six additional independent surveyed distances.

Limitations: one retrospectively inspected dataset; automatic image-only pixel
refinement and experimentally interpreted GNSS RMS weights; datum/reference
uncertainty; seven targets do not cover every model region. Tests concern sparse
camera/marker geometry, not dense mesh/DEM/orthomosaic acceptance or other
projects. No production changes, Setup or public release. External evidence:
real-reference-light/reconstruction-cross-validation/report.json/html with
per-fold task/result/report/log and holdout-isolation copies.

### Independent Metashape end-to-end comparison

Found installed, activated Metashape Professional 2.4.0 build 23155 and ran its
native documented Windows -r scripting interface. No installation/license
changes or purchases. The offscreen Qt plugin was absent; the initial offscreen
probe was stopped, then the documented Windows command-line path succeeded.
The sandbox denied native preference saving on exit; processing/project outputs
were saved only in the owned evidence workspace. The first successful alignment
save was followed by a calibration.todict metadata error; calibration scalar
readback recovered metadata without re-running image alignment.

Independently reconstructed the same 20 original photographs in Metashape:
20/20 registered, one sensor, 28051 valid ties, High/downscale 1, exhaustive
matching (generic/reference preselection disabled), keypoint limit 24000,
per-megapixel limit disabled and tiepoint limit disabled. GPS was disabled.
This is an independent native reconstruction, not another invocation of COLMAP.

Used exactly the same seven refined image observations and recorded receiver
RMS weights. For the fixed three-control split and every six-control holdout
fold, only training markers were added to Metashape before optimization: the
withheld XYZ AND photo observations were absent. All calibration fitting flags
were disabled during final GCP optimization. Held-out coordinates were then
estimated from native camera unprojection/projection using independent pixel
least squares, without using reference XYZ. No fit presets were selected after
seeing these results.

Metashape rejected the custom local datum during reference update, including
after removing camera GPS. Those failed attempts supplied no valid results.
Successful runs used the supplied EPSG:26911 horizontal CRS and the same supplied
heights, without external geoid/GPS transformations. Lens2Mesh uses projected
Cartesian fitting. Native alignment calibration/feature detection/tie rejection
differ: Metashape initially fits more Brown coefficients than the Lens2Mesh
SIMPLE_RADIAL camera. This is an end-to-end comparison, not isolation of a
single solver or camera model.

Seven-fold held-out RMS XY/Z/3D (metres):
- Lens2Mesh: .11649262/.11171687/.16140381; maximum observed 3D .23498877.
- Metashape: .05312829/.14054278/.15024942; maximum observed 3D .22575129.
Thus native Metashape improved horizontal RMS here, while Lens2Mesh had lower
vertical RMS. Both total results remain around 15–16 cm; no new arithmetic bug
or sub-10-cm accuracy acceptance follows. The separate fixed three-control,
four-check split gave .13608420 m for Lens2Mesh and .10806944 m for Metashape.
Neither software is the ground-truth source; the supplied survey coordinates
remain the reference, with the previously documented datum/uncertainty limits.

Original user project SHA256 still matches the pre-comparison snapshot. No
production code, Setup or release changed. Private evidence is under external
real-reference-light/independent-metashape/: alignment project/log/settings,
eight independent native comparison projects/results, reference-comparison.json,
comparison-summary.json and comparison-report.html. Dense mesh/DEM/ortho accuracy
and other datasets were not assessed by this comparison.
Official command-line source:
https://agisoft.freshdesk.com/support/solutions/articles/31000133141-how-to-run-the-script-in-headless-mode-from-the-command-line
