# PhotoMesh Studio 1.0.3 release review

Review date: 2026-11-07. This record replaces the pending baseline maintainability review. Publication remains separate from preparing an installer.

## Scope and method

The repository sweep inventories all 68 application modules, Python entry points, developer tools and tests. It records imports, function sizes, mutation sites, exact-body duplication leads and names without lexical references. Ruff undefined-name, unused-import, redefinition and unused-local findings are inspected as leads, rather than deletion instructions. See the workflow audit artifact and PR #7 for the final revision's machine-readable inventory and outcomes.

Detailed manual review concentrates on changed code and its callers, UI/task/project ownership, source identity, coordinate frames, project migration, destructive cleanup, product publication/rollback, native-engine binding, raster handles, installer staging and runtime resources. Large numerical modules retain their existing algorithms and bounded-processing variants. This is a repository-wide maintainability sweep and targeted contract review, not formal proof of every numerical path.

## Findings and changes

- Split-button captions: native size hints did not reserve enough width for the menu indicator, and the previous test only compared widget width with that same hint. Reserve the measured caption plus indicator and padding. Test the actual caption space in selected/unselected states, both themes, and DPI/window-size variants; retain native body/arrow behavior.
- Memory contracts: several resource planners multiplied a possibly unknown available-RAM value. Require a measured budget for these planners and stop clearly before large allocations if it is unavailable. Preserve CPU-count fallback for worker estimates. Move psutil and pyproj into the application requirements so source installations match required runtime capabilities.
- Project ownership: prevent New, Save/Save As and Close from replacing or moving project state while a pipeline or project preparation is active. Opening already had a processing guard.
- Cleanup: protect project metadata, products, photos and resolved linked targets. Filter referenced folders before offering stale-copy cleanup and recheck after confirmation. Keep all existing confirmation steps.
- Legacy temporary data: do not remove migrated temporary results until the project JSON has been committed successfully. Retain referenced source photos and linked targets. A failed metadata write leaves the original source in place.
- Older raw-cloud projects: preserve a referenced raw fusion cloud and its visibility file before rebuilding. Restore them on failure/cancellation; current filtered-cloud projects incur no legacy-copy cost. Keep backups and report their locations if restoration is blocked.
- EXIF: centralize rational and altitude-reference decoding. Integer and byte-valued below-sea-level references now agree between photo-import paths. Preserve partial-GPS handling and existing stored project coordinates.
- Raster resources: close TIFF readers when header/metadata parsing fails, normalize malformed/truncated metadata errors, and close DEM readers if sidecar/frame setup fails.
- Obsolete routes: remove the unused COLMAP point-cloud/mesh builders and their private preset tables after tracing the active dense.py, mesh_steps.py and task-command routes. The obsolete mesh route deleted the prior output before processing.
- Installer resources: validate imports from the staged application rather than the checkout, include the shortcut-repair helper in the production builder, and verify an actual upgrade removes obsolete managed source while keeping external user metadata.
- Focused cleanup: remove 33 unused imports, 13 unused local assignments, the obsolete image-worker wrapper, pixmap canvas and shape-colour wrapper. Share quaternion conversion through colmap_io. Existing format readers, public numerical helpers, Qt hooks, command aliases, native-engine fallbacks and required icon/shape resources are retained.

## Deliberate boundaries

Unreferenced-name findings include Qt event overrides, special methods, utility entry points and public format/numerical helpers. They are not established dead code. Console/script compatibility and old-project readers remain. Vertex-normal helpers have different input conversion/allocation contracts; reference CRS parsing and shape-source CRS parsing also have different semantics. They are not merged merely for textual similarity. CPU/CUDA and modern/legacy engine variants remain required compatibility paths.

Large orthomosaic, texture, optimization and view modules remain maintenance candidates. Splitting their algorithms immediately before this release would add risk without establishing equivalent lifecycle, precision and memory behavior. No unresolved release-critical finding was intentionally deferred; new failures in final validation block packaging/delivery.

## Acceptance evidence

The following checks passed for candidate commit `127c682c6d05d61093843f5a1ed8a23f833005d8` in
[Actions run 42310283579](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42310283579):
- compilation and static checks; full Linux and Windows regression suites;
- real native toolbar captures and caption/body/arrow tests;
- old/new project and XML round trips, failure/cancellation, file preservation and linked-path tests;
- same-runner processing comparisons against the previous preview: exact raster arrays, lossless atlas pixels and UV arrays with one visibility worker for deterministic scheduling, plus photo-output hashes and timings;
- native CPU synthetic reconstruction and numerical checks using the verified released engine bundle;
- copied-runtime checks and installation of the newly built Setup into an isolated runner directory, checking installed source location, version, About and layer controls.

Synthetic checks do not replace installation and a small real project on the target NVIDIA/OpenGL hardware. GPU dense reconstruction, real display rendering and issue #6's user dataset remain target-machine checks. The installer is not published automatically. New project saves use schema 2 and independent reference XML 2.0; older application versions may not read new saves.

## Recorded candidate results

- Linux and Windows: each **680 passed, 8 skipped**. The skips require real
  survey/project fixtures, CUDA or a real OpenGL display. The runner's Dash
  plugin produced one unrelated deprecation warning on each platform.
- Compilation and undefined-name checks passed. The inspected inventory covers
  68 application modules; selected Ruff static leads are empty. Unreferenced
  names and large-function candidates remain review leads, not established bugs.
- Dark/Light caption and body/arrow checks passed at DPI scales 1/1.5/2 and
  window widths 1280/1920. The installed capture shows complete product and
  Transparency labels. Shared caption sizing and tighter view/zoom side padding
  preserve the compact row.
- Photo outputs/JPEG hashes matched; current/baseline timing ratio was 0.935.
  Raster arrays and controlled lossless texture/UV outputs matched; timing
  ratios were 0.981 and 1.016, below the existing 1.08 gate.
- CPU synthetic reconstruction passed for the calibrated and calibration-free
  routes, including the large-image ALIKED probe. Calibrated 16-view camera RMS
  was about 0.012 m for SIFT and 0.041 m for ALIKED/LightGlue; these are synthetic
  fixture results, not survey accuracy claims.
- The full Setup upgraded disposable 1.0.2 successfully. Installed version/About,
  resources and all 68 application source names/hashes matched. Obsolete managed
  source was removed and an external metadata fixture was unchanged.

[Candidate Setup and validation records](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42310283579/artifacts/13547844488)
are an artifact ZIP containing `PhotoMeshStudio_Setup_1.0.3.exe`, its checksum,
native/installed validation JSON and screenshots. The artifact is retained for
14 days. [Machine-readable review inventory](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42310283579/artifacts/13547653087)
is separate. Publication and installed-user acceptance remain pending.

## Consolidated preview findings

Three temporary preview documents were retired after consolidation here.
Their historical revisions remain in Git history; they are not current release
instructions.

- Issues #2/#3: bounded Windows sharing/lock retry retains rollback and completed
  staged output on persistent publication failure. ALIKED's 2048-pixel extraction
  bound and one extraction worker prevent the reported full-resolution ONNX
  allocation route; original camera/keypoint coordinates are restored.
  Earlier native evidence is in Actions runs 41702934208 and 41716099953.
- Toolbar review: two rows separated by rules, complete under-icon captions,
  cube views, additional-only Layers menu, shared visibility actions and an
  immediate conditional neural-method warning. The final controls supersede the
  old Hidden submenu design.
- Independent icons: target, four-tile mosaic and unfilled vector designs share
  existing Qt rendering/resource consumers. Theme-aware icon cache keys prevent
  stale palette pixels after switching theme. This does not certify provenance
  or legal clearance for every asset; retain the [project notes](project-notes.md).
- Issue #6: nested project output below a common photo root is allowed, while
  source images inside a mutable workspace, unsafe model names and linked
  managed outputs are rejected before destructive writes. Synthetic preservation,
  resume and alias regressions pass; the real user dataset/GPU check remains open.
- Workflow integration: Project/Edit/Process/Display/Survey/Export/Help reuse
  authoritative QActions. Historical qualified command names remain aliases for
  scripts without restoring removed menus or duplicate signals.

The later documentation-only cleanup updates the README, guides and review
status and removes the three superseded preview notes. It does not change
application sources, runtime or the tested Setup. A future source build includes
the revised docs; the candidate already downloaded remains byte-for-byte unchanged.
