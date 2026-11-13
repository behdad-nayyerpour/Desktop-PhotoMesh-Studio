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

Coarse pose reuse is guarded by the engine database focal-prior flags. A native
calibration-free regression exposed biased geometry despite low reprojection
error; that route now uses target-resolution mapping instead of inheriting
coarse camera poses. The same counterexample remains in the native benchmark.

SIFT stays the default. A faster label is not used to reduce quality invisibly.
Neural methods have explicit feature limits and their own databases. Experimental
Caspar is not automatically selected because its camera/prior support differs.
A CUDA-enabled executable is not proof of Ceres/cuDSS support; packaged modern
Ceres GPU solvers remain disabled unless the bundle is explicitly certified.
Feature extraction/matching and dense processing use compatible GPU paths.

The official pinned CUDA archive uses CUDA 13.2 and Turing-or-newer architectures.
The bundled policy conservatively requires a matching driver API and device
generation. The CPU engine and retained legacy GPU SIFT/dense engine cover other
supported configurations. A native failure is reported by a child process;
results are not activated from a failed generation.

Frame application is distinct from constrained adjustment. A low reprojection
error alone does not prove metric accuracy in a poorly calibrated/near-planar
scene. The native tests therefore distinguish known-calibration and
calibration-free cases; actual survey work still requires independent controls.

## Validation evidence

Validated code: `427ed36cd2fbe3e9a644cfa1cc509afb752783ef`.
[GitHub Actions run](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/41515504654)
completed successfully on Linux and Windows: **581 passed, 8 skipped** on each.
The skipped tests require local survey/GPU fixtures or a real display; the
separate Mesa OpenGL overlay test passed. Compilation, undefined-name checks
and the PowerShell builder parser passed.

The pinned Windows CPU binary reconstructed the deterministic 16-view,
two-sensor synthetic scene with these measured results:

| Features | Mapping | Calibration | Cameras | Centre RMS (m) | Reprojection RMS (px) | Time (s) |
|---|---|---|---:|---:|---:|---:|
| SIFT | incremental | Known | 16 | 0.0118 | 0.223 | 4.91 |
| SIFT | global | Known | 16 | 0.0116 | 0.214 | 4.96 |
| ALIKED + LightGlue | global | Known | 16 | 0.0439 | 0.372 | 15.46 |
| SIFT | fast-coarse-fine | Known | 16 | 0.0228 | 0.227 | 11.79 |
| SIFT | incremental | Estimated | 16 | 0.0134 | 0.221 | 5.98 |
| SIFT | fast-coarse-fine | Estimated | 16 | 0.0249 | 0.222 | 12.19 |

The coarse threshold was deliberately reduced to 256 px to exercise both
stages on this small fixture. It is not a representative speed comparison for
large aerial surveys. Neural matching was slower here and remains optional.
The calibration-free comparison retains the original regression scene and
passes the fixed geometry/registration gates; low reprojection error alone
is not accepted as evidence of correct geometry.

Native model conversion re-read the transformed modern frame/rig files and
agreed with camera centres and tie points to 1e-7. SIFT + LightGlue passed its
separate offline extraction/matching probe. A 30,000-point filtering/Poisson
check produced 1,999 faces with median distance 0.00334 m from the known
synthetic surface. Its timings and the reconstruction measurements are in the
[benchmark artifact](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/41515504654/artifacts/13174934324).

On the same Linux runner, rasterization time was 0.975x and synthetic texturing
1.019x the 1.0.0 baseline; both passed the existing 1.08x regression limit.
This gate does not imply identical timing for different requested workloads.

The reported cloud Properties exception has old pair-list/dictionary schema,
invalid-count and project-save/reopen regressions. Original sensor dimensions
are restored before grouping working photos; a collision test prevents mixed
sensors from being combined after downscaling.

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
