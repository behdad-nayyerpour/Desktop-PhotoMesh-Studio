# Reported errors and toolbar review

Scope: GitHub issues #2 (Windows orthomosaic directory publication) and #3
(ALIKED full-resolution ONNX allocation), alignment callers, product transaction
callers (orthomosaic/DEM/texture/tiles), layer state, menus and predefined views.
No version change or release is included.

- ALIKED extraction now uses a shared 2048 px maximum in Fast, Exhaustive and
  Sequential alignment and one extraction worker. Feature-count limits alone
  do not bound dense ONNX intermediates. Original-coordinate calibration and
  keypoint restoration stay in their existing order before sensor grouping.
  SIFT and SIFT+LightGlue extraction resolution is preserved. The dialog and
  Fast pipeline log disclose the limit; this can reduce fine feature detail.
- Output publication retries only Windows access/sharing/lock errors with a
  bounded delay. It retains rollback and keeps completed staged files after
  persistent publication failure instead of deleting expensive results.
  The truncated issue does not establish which process held the Windows lock;
  retries mitigate transient locks, while persistent locks remain explicit.
- Processing, Display and View have named, text-labelled toolbars. One menu per
  tie-point/cloud/mesh product includes Hidden plus its render modes and mirrors
  Workspace/menu visibility. Other layers remain in one Layers menu. Predefined
  views include Isometric and activate the Model tab without resetting zoom.
- Toolbar composition moved out of MainWindow into one module. Existing shared
  QAction handlers remain authoritative; no duplicate processing or layer sink.
  Shared publication policy also covers multi-output alignment activation.
- Review covered changed code and directly affected callers/resources. Existing
  CPU/GPU and old-engine compatibility paths are retained. The repository-wide
  baseline maintainability audit remains pending before the next release.

Validation: regression tests cover all alignment command builders, retry and
rollback, retaining completed output, GUI visibility synchronization and view
actions. CI results are recorded in the associated change. No local user PC
execution, real quarry reconstruction, target-GPU validation or installed Setup
test has been performed.
