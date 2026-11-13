# Workflow review — 1.0.1

This checklist records implementation of the user-approved scope for 1.0.1.
A checked item means its implementation and integration were reviewed; it does
not mean every hardware/dataset combination has been tested. Work and automated
validation run through GitHub and GitHub Actions, without access to the user's computer.

Normal-size workloads retain optimized paths. Resource estimates are approximate;
oversized requests are rejected before known expensive allocations. Correctness
fixes, changed quality and first-time rebuilding of legacy caches can change the
amount of work. Timing evidence below covers equivalent synthetic workloads only.

## Alignment

- [x] 1. Transactional replacement and remove ineffective reset
- [x] 2. Four distinct image resolutions
- [x] 3. Feature limit and explicit engine-default semantics
- [x] 4. Review/edit calibration groups
- [x] 5. Show effective coarse/fine stages
- [x] 6. Explain Auto solver and fallback
- [x] 7. GPS availability and reference/pair distinction
- [x] 8. Contextual setting guidance and effective summary

## Dense cloud

- [x] 9. Depth reuse validates every relevant input/setting
- [x] 10. Keep old cloud until success
- [x] 11. Real Disabled depth filter, retain fusion validation
- [x] 12. Supporting-photo counts validated and reported
- [x] 13. Map inventory and retention semantics
- [x] 14. Respect neighbour cap including fallback
- [x] 15. Adjustable local-density filters
- [x] 16. Terrain filter off by default with adjustable frame/thresholds
- [x] 17. Resolution/resource estimates before heavy work
- [x] 18. Per-filter completion statistics and guidance

## Mesh

- [x] 19. Disable source-inapplicable controls
- [x] 20. Explain Poisson/Delaunay prerequisites
- [x] 21. Honest trimming labels
- [x] 22. Bounded large-cloud loading and memory preflight
- [x] 23. Enforce point limit including manual-voxel conflict
- [x] 24. Voxel units reflect project scale
- [x] 25. Visible target faces even in disabled field
- [x] 26. Expose absolute component threshold
- [x] 27. Exact edge-filter criterion and removal statistics
- [x] 28. Validate mesh source and camera compatibility

## Texture

- [x] 29. Validate texture size without silent coercion
- [x] 30. Explicit automatic page policy/hard limit
- [x] 31. Bound page memory
- [x] 32. Validate UV identity beyond face count
- [x] 33. Keep-UV page count read-only
- [x] 34. Invalidate visibility on photo changes
- [x] 35. Strict working-image resolution
- [x] 36. Distinguish colour fill from geometry
- [x] 37. Ghosting eligibility/removal coverage
- [x] 38. Warn for planar mapping on steep surfaces
- [x] 39. Rasterize large UV triangles without dropping faces
- [x] 40. Transactional texture product set

## Tiles

- [x] 41. Exact displayed point/face limit
- [x] 42. Only supported point/mesh formats
- [x] 43. Disable irrelevant controls for points
- [x] 44. Show effective auto/manual texel resolution
- [x] 45. Enforce texture-size cap
- [x] 46. Bound pathological dense leaves
- [x] 47. Bound memory and worker count
- [x] 48. Validate source texture identity
- [x] 49. Consistent frame/up/global transforms
- [x] 50. Parent bounds include descendants
- [x] 51. Recoverable output swap and previous display
- [x] 52. Preflight source state and report output statistics

## DEM

- [x] 53. Rasterize mesh triangles rather than vertex means
- [x] 54. Explicit DSM semantics
- [x] 55. Selectable point-height aggregation
- [x] 56. Resolution/grid preview tied to source
- [x] 57. Bound resources and raster memory
- [x] 58. Reject invalid/outside regions
- [x] 59. Bounds in selected projection frame
- [x] 60. Honest units/CRS validation
- [x] 61. Explicit fill distance/smoothing units
- [x] 62. Measured/interpolated/nodata masks
- [x] 63. Finite/nonempty/current source validation
- [x] 64. Transactional TIFF/metadata set

## Orthomosaic

- [x] 65. Enable only active sizing mode
- [x] 66. Surface-dependent output plan
- [x] 67. True half-resolution photos
- [x] 68. Disable ineffective seamline refinement
- [x] 69. Honest single-photo mode and skip unused work
- [x] 70. Block-independent bounded hole fill
- [x] 71. Ghost filter grid/eligibility report
- [x] 72. Use DEM directly without hidden decimation
- [x] 73. Surface/camera frame validation and units
- [x] 74. Full resource preflight
- [x] 75. Refill occluded candidate pools only where needed
- [x] 76. Transactional image/height/metadata set

## Added photos

- [x] 77. Context-menu registration from sufficient well-spread measured GCPs; keep existing poses and show shapes



## Implementation map

| Scope | Settings and integration | Processing |
| --- | --- | --- |
| 1–8 Alignment | [dialogs](../../photomesh/dialogs.py), [workflow UI](../../photomesh/workflow_ui.py), [main window](../../photomesh/mainwindow.py) | [fast pipeline](../../photomesh/fastpipe.py), [COLMAP adapter](../../photomesh/colmap.py), [frame preservation](../../photomesh/registration.py) |
| 9–18 Dense cloud | [workflow UI](../../photomesh/workflow_ui.py) | [dense planning/reuse](../../photomesh/dense.py), [filters](../../photomesh/pcfilter.py), [worker commands](../../photomesh/tasks.py) |
| 19–28 Mesh | [workflow UI](../../photomesh/workflow_ui.py), [pipeline steps](../../photomesh/mesh_steps.py) | [meshing](../../photomesh/mesh.py), [bounded input helpers](../../photomesh/workflow.py) |
| 29–40 Texture | [dialogs](../../photomesh/dialogs.py), [workflow UI](../../photomesh/workflow_ui.py) | [texture generation](../../photomesh/texture.py), [publication](../../photomesh/workflow.py) |
| 41–52 Tiled model | [workflow UI](../../photomesh/workflow_ui.py), [main window](../../photomesh/mainwindow.py) | [tile generation](../../photomesh/tiles.py) |
| 53–64 DEM | [workflow UI](../../photomesh/workflow_ui.py) | [DSM engine](../../photomesh/dem_engine.py), [publication](../../photomesh/workflow.py) |
| 65–76 Orthomosaic | [dialogs](../../photomesh/dialogs.py), [workflow UI](../../photomesh/workflow_ui.py) | [orthomosaic](../../photomesh/ortho.py), [direct DEM surface](../../photomesh/raster_surface.py) |
| 77 Added photos | [registration UI](../../photomesh/registration_ui.py), [photo/workspace menus](../../photomesh/mainwindow.py) | [GCP pose resection](../../photomesh/registration.py) |

## Validation

Validated processing commit: `122f3918c2c4e25c126db0a154009ddc8f6efaeb`.
[GitHub Actions run](https://github.com/behdad-nayyerpour/Lens2Mesh/actions/runs/41331848677):

- Linux: **534 passed, 8 skipped**; new workflow regressions **29 passed**.
- Windows: **534 passed, 8 skipped**.
- Separate software-OpenGL overlay run: **1 passed**.
- Python compilation and undefined-name/export checks passed.
- Same-runner rasterization median: 0.086753 s before / 0.083616 s after
  (ratio 0.964); output arrays matched exactly.
- Full synthetic texture median: 0.331441 s before / 0.330501 s after
  (ratio 0.997). Both comparisons passed the performance gate.

The eight standard-suite skips require COLMAP/CUDA, local aerial/project data or
a real GL display. The overlay GL test was additionally executed under Mesa;
the transparent-shape GL test remains a target-display check. One warning came
from the runner's unrelated Dash pytest plugin, not a failed application test.

The [new regression suite](../../tests/test_workflow_101.py) exercises transactional
publication/rollback, real mesh-triangle DSM heights, point aggregation, input
identity, source controls, explicit limits, large UV triangles, degenerate tile
partitioning, parent bounds, metric frames, actual calibration partitioning,
occluded-view replenishment and GCP registration without moving the original
cameras. Existing tests cover the rest of the integrated project/UI/export paths.

The [same-runner benchmark](../../tools/benchmark_workflow_101.py) compares equivalent
rasterization and full synthetic texturing against 1.0.0, checks rasterization
output equality and rejects a median slowdown above 8%. This tolerance accounts
for shared-runner noise; it is not a promise of identical runtime on every PC.

## Remaining release checks

- Full COLMAP/CUDA reconstruction on a representative aerial dataset and target GPU.
- Manual Windows visual review of settings and actual project output, including
  survey-coordinate accuracy and the installer built from this source.
- Rebuild the complete Setup EXE as 1.0.1. No separate updater or runtime dependency
  was added.
