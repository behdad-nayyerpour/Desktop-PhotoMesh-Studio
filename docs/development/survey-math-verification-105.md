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
