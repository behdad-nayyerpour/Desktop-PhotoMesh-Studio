# Offline engine modernization — 1.0.2

## Implementation

- [Engine policy](../../photomesh/engine.py): executable capabilities, isolated
  native compatibility probes, conservative device selection, local model hashes,
  feature/matcher consistency, global solver selection and observation validation.
- [CUDA probe](../../photomesh/engine_probe.py): driver initialization is performed
  in a disposable child process, not through native libraries in the GUI.
- [Sparse model codec](../../photomesh/colmap_io.py): independently posed photos
  receive synchronized modern rigs/frames as well as legacy image poses.
  Modern COLMAP reads frame poses preferentially, so these are updated together.
- [Alignment](../../photomesh/fastpipe.py): integrated global mapper, legacy and
  incremental fallback, modern/legacy option aliases, compatible calibration
  partitioning and descriptor isolation.
- [GPS](../../photomesh/georef.py): initial reference framing uses validated,
  registered camera positions, non-collinear fitting and a metric projection.
  A circular longitude mean handles dateline surveys. Polar/widely separated
  references are rejected rather than assigned an inappropriate map frame.
- [Publication](../../photomesh/workflow.py): prepare all adjusted outputs first;
  failed renames roll back the model/cloud/mesh set.
- [Builder](../../tools/prepare_engine.py) and [asset pins](../../packaging/engine-assets.json):
  official 4.2.1 CPU/CUDA archives and three neural ONNX models have fixed SHA256
  digests. Downloads occur only in the build tool, never in processing code.
- [Native benchmark](../../tools/benchmark_engine_102.py): known-calibration
  synthetic reconstruction, independent frame re-read by the actual engine,
  calibration-free comparisons, point filtering and Poisson geometry.
- [Regression tests](../../tests/test_engine_102.py): device/driver rejection,
  GPU-to-CPU retry, model checksum changes, modern frame binary layout,
  calibration/pose-prior links, geographic fitting, safe extraction and rollback.

## Safety and numerical policy

SIFT stays the default. A faster label is not used to reduce quality invisibly.
Neural methods have explicit feature limits and their own databases. Experimental
Caspar is not automatically selected because its camera/prior support differs.
A CUDA-enabled executable is not proof of Ceres/cuDSS support; packaged modern
Ceres GPU solvers remain disabled unless the bundle is explicitly certified.
Feature extraction/matching and dense processing use compatible GPU paths.

The official pinned CUDA archive uses CUDA 13.2 and Turing-or-newer architectures.
The bundled policy conservatively requires a matching driver API and device
generation. The CPU engine and retained legacy dense engine cover other
supported configurations. A native failure is reported by a child process;
results are not activated from a failed generation.

Frame application is distinct from constrained adjustment. A low reprojection
error alone does not prove metric accuracy in a poorly calibrated/near-planar
scene. The native tests therefore distinguish known-calibration and
calibration-free cases; actual survey work still requires independent controls.

## Validation evidence

VALIDATION_PENDING

No user computer or dataset is used for development validation. Tests run in
GitHub Actions. Full real-data CUDA reconstruction and driver-specific behavior
remain target-hardware release checks; automated CPU tests do not establish
their performance or precision.

## Offline build and redistribution

The builder caches verified downloads under the user's local build cache.
Pass `-EngineCache` to change its location, or `-OfflineBuild` once the cache is
complete. Processing supplies local model paths and rejects missing/corrupt
weights instead of asking COLMAP to download them.

License notices are included for [COLMAP](../licenses/COLMAP-4.2.1.txt),
[ALIKED](../licenses/ALIKED.txt) and [LightGlue](../licenses/LightGlue.txt).
Other runtime dependencies retain their respective licenses.
