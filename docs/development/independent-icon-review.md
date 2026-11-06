# Independent layer icon preview

## Scope

Replace the Markers/marker-label, Ortho and Shapes toolbar/tree artwork with the approved survey-target, four-tile mosaic and unfilled-vector designs. Keep the 32-unit grid, existing logical icon sizes, actions, menus and workflow behavior. Marker symbols inside Photo/Model/Ortho views are outside this change.

## Review

Reviewed icons.py, palette application in theme.py, shared toolbar consumers, icon/toolbar/workspace tests, installer staging and the repository-wide reference search from the provenance review. Shared layer_icon callers receive the new drawings without duplicated assets. The themed icon engine cache must distinguish light and dark palettes; otherwise a live theme switch keeps stale pixels. Existing icons retain their previous cache keys and rendering behavior. No processing or project-format change is included.

## Validation

The preview workflow compiles sources, runs the existing Windows non-GPU suite plus palette-switch regressions at tree/toolbar display sizes, and captures actual toolbar images in both themes. Results must be read from the workflow run; this document does not claim that pending checks passed.

## Test installer

Artifact only; do not publish a GitHub Release or merge before the user's installed review. Reuse the SHA256-verified v1.0.2 released runtime and replace application sources with this branch. Keep application version 1.0.2 and use a clearly named test installer. This tests artwork changes, not reconstruction engines. No public installer is replaced.

## Remaining work

User installation and appearance review; inspect toolbar screenshots and test results. The broader interface/provenance work, third-party redistribution review, binary runtime audit and pending baseline maintainability audit remain outstanding. This preview is not a legal clearance or a new application release.

## Issue #6: dense workspace below the photo root

The old folder-containment check rejected valid project folders under the common source-photo root. The replacement checks referenced image paths, sparse model input, output paths and directory aliases before both planning cleanup and worker writes. Nested project output is allowed; source images inside the mutable workspace, unsafe model names and linked managed output folders are rejected before mutation. Reviewed prepare_workspace, dense_steps, undistortion temporary-file replacement and reuse invalidation. Regression coverage includes an actual nested synthetic-image build, byte-for-byte original preservation, resume, rejection before destructive cleanup, unsafe paths and source/output aliases. No reconstruction math or quality settings changed.

Windows application-code validation before adding #6: 621 passed, 8 skipped (run 42270641010). Its screenshot step failed because a temporary Python script did not add the repository to sys.path; corrected in the workflow. Full tests run again for the added processing-path fix. User installation review and real-data GPU processing remain pending.
