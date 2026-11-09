# Release quality checklist

[Development guide](README.md) · [Installer build](../../packaging/RELEASE.md)

Maintainability review is required for every new application version. Include it
in the work plan at the start and check it again after the final implementation.
It complements functional tests; it is not established by a green CI result.

## Baseline review

The repository-wide baseline sweep and targeted contract review were performed
for [1.0.3](release-review-103.md), with explicit scope, findings and remaining
hardware checks. Earlier versions did not establish that baseline. Each later
version still requires the review below; a green test run is not proof of the
absence of duplication, dead code or bugs.

## Review before each release

- [ ] Review the changed functions, their callers and affected workflows for
  clear responsibilities, explicit data contracts, units and error handling.
- [ ] Sweep the repository for repeated calculations, validation, configuration,
  file handling and UI/task orchestration. Consolidate only when behavior,
  assumptions, precision, lifecycle and performance requirements actually agree.
- [ ] Inspect large or difficult modules and functions. Extract cohesive
  responsibilities where it improves understanding; avoid splitting files or
  introducing abstractions solely to reduce line counts.
- [ ] Check names, comments, type/data-shape assumptions, paths and references
  against actual behavior. Keep developer documentation in English and update
  explanations when an implementation changes.
- [ ] Identify unused imports, unreachable branches, obsolete helpers, settings
  and files. Before removal, inspect dynamic imports, Qt signals/slots, menus,
  command entry points, installer lists, runtime resources and compatibility
  paths. A search with no matches is not sufficient evidence of dead code.
- [ ] Preserve useful shared code in one suitable module; remove redundant
  wrappers and copies where their behavior has been shown equivalent. Preserve
  deliberate CPU/GPU or old/new-engine variants and document why they differ.
- [ ] Check dependencies between alignment, calibration/GPS, control markers,
  point clouds, meshes and raster products. Preserve coordinate frames, units,
  source identities and stale-result invalidation.
- [ ] Verify project save/load compatibility, failed/cancelled-task behavior,
  UI responsiveness and offline execution for affected paths.
- [ ] Run existing compilation/static checks and the relevant regression and
  integration tests. Add focused tests for changed behavior or meaningful
  refactoring risks; do not create tests that merely repeat the implementation.
- [ ] For processing hot paths, compare equivalent inputs/settings and measure
  accuracy and runtime/memory as appropriate. Do not replace a correct method
  with a less accurate shortcut to satisfy a timing target.
- [ ] Recheck the final diff for temporary code, debug output, duplicated
  documentation and outdated references. Update developer/release instructions
  affected by the final change.
- [ ] Record evidence and unresolved limitations. Separate automated results,
  manual code review, native-engine tests and target-hardware checks.

Use the existing tests and workflow documented in the development guide.
Static diagnostics and duplicate-code tools provide leads for inspection;
they cannot decide whether a dynamically used file or a numerical variant is
redundant. Do not enable new blanket formatting/lint rules or broad rewrites
without assessing the existing code and the resulting diff.

## Evidence to retain with a version

Use the version's existing review document or PR/release notes; a second
changelog is unnecessary.

- **Scope:** modules/workflows reviewed and the extent of the repository sweep.
- **Findings:** duplicated/dead/unclear code found and the evidence for it.
- **Changes:** cleanup performed and behavior or compatibility intentionally kept.
- **Validation:** tests, numerical checks and applicable performance comparisons.
- **Remaining work:** deferred findings, reasons and checks not executed.

An unchecked item is not a completed review. Report any remaining work accurately
and resolve release-critical correctness, compatibility or performance findings
before preparing the version for release.

This checklist changes development practice, not application behavior. Updating
it alone does not require rebuilding the Setup or increasing the app version.

## User manual review for each update

- [ ] Assess the update against the approved complete English PDF manual:
  menu/submenu commands, dialogs and option choices, defaults, workflows,
  installation, reference behavior and export formats.
- [ ] If documentation changes are needed, list the affected sections and obtain
  the user's approval **before editing the manual**, as required by
  [AGENTS.md](../../AGENTS.md#user-manual-maintenance-approved-2026-11-08).
  If no change is needed, retain the current approved PDF.
- [ ] After approval, revise only affected material and necessary version,
  contents/index and cross-reference metadata. Preserve unrelated approved text,
  layout and screenshots. Verify sharp lossless screenshots, current option
  semantics, affected page rendering and any changed pagination/links.
- [ ] Record which manual revision is bundled with the application and whether
  affected sections were reviewed, approved and updated. Keep the editable source
  and original screenshot evidence alongside the approved manual archive.

The approved baseline is `PhotoMeshStudio_1.0.4_Complete_User_Manual.pdf`
(105 pages, approved 2026-11-08), not the superseded example-focused guide.

## Approved scope for the next version (2026-11-08)

The user approved the following work areas for the release following 1.0.4.
Start with the confirmed EXIF and calibration defects, then validate the
coordinate-frame and height-reference changes numerically. The F identifiers
refer to the external review discussed with the user.

- [ ] Fix invalid EXIF rational/GPS decoding so corrupt metadata cannot become
  plausible zero coordinates (F7). Correct intrinsic fit presets so the named
  coefficients match the coefficients optimized for each camera model (F9).
- [ ] Evaluate and implement a suitable Cartesian adjustment frame, including
  ENU, with independent numerical comparisons (F1). Extend supported coordinate
  systems and make camera/control height references explicit (F3). Preserve
  existing project frames and provide tested migration for frame changes.
- [ ] Add camera-model selection, supported DJI/RTK metadata and per-camera
  accuracy handling, and optional GPS constraints during alignment (F2/F6/F8).
  Validate defaults against representative data. Record unknown height sources
  and verify camera metadata semantics before assigning survey-grade weights.
- [ ] Add streaming LAS/LAZ export with coordinate-system metadata (F4), ground
  classification and DTM generation (F5). Retain the existing DSM workflow and
  distinguish measured ground from interpolated surfaces.
- [ ] Improve large-project capacity with a sparse camera-optimization solver
  (F10), efficient GPS-neighbor pair selection (F14), and DEM median aggregation
  (F15). Compare accuracy, deterministic behavior, peak memory and runtime on
  equivalent workloads before adopting each optimization.
- [ ] Improve actionable errors and script tracebacks while respecting Qt thread
  ownership and existing script behavior (F21/F22). Introduce locked runtime
  dependencies and a reusable validated release workflow (F25/F26). Add installer
  signing when signing credentials and infrastructure are available (F27).
- [ ] Implement incremental test delivery (approved 2026-11-10): for each app
  change, provide a runnable Windows `.bat` updater that fetches only changed
  installed components and necessary dependencies from an exact candidate
  artifact. Verify the installed baseline, download checksums and install path;
  require the app to be closed, back up replaced files and support rollback.
  Preserve projects, photos and user settings. Include added/removed dependencies
  deliberately and test the actual packaged layout, custom paths and an
  interrupted/failed update. Do not redownload unchanged Python/engine bundles.
- [ ] Deliver the incremental candidate for the user's test and wait for explicit
  acceptance before building the complete Setup. Build from the accepted
  revision, then validate the full installer. Public publication still requires
  separate authorization; see [AGENTS.md](../../AGENTS.md).
- [ ] Add **User Manual (PDF)** access in the **Help** menu in the next version.
  Open the bundled approved English PDF offline using a suitable local viewer.
  Include the PDF in application resources and the final installer; resolve its
  installed path reliably and show an actionable message if it cannot be opened.
  Preserve existing Help commands. Verify opening it from the installed build,
  including a custom install location and an offline session. Carry this entry
  forward in later releases and apply the manual-review approval policy above.
- [ ] Ship the next Windows Setup with **Select Destination Location** visible
  during both fresh installation and reinstall/upgrade. The source now sets
  `DisableDirPage=no`; an existing installation directory remains the initial
  suggestion. Before release, verify browsing to a custom folder, reinstalling,
  and the installed shortcut and launcher paths. Keep project/photo data outside
  managed installation folders.
- [ ] After each successful build/rebuild, automatically load and activate the
  resulting product's display (approved 2026-11-10): alignment/tie points,
  point cloud, mesh, texture, tiled model, DEM and orthomosaic. Show the result
  in the appropriate **3D View** or **Plan View**; a completed texture build
  selects the textured mesh display. Keep the related toolbar, menu and Project
  tree visibility/selection states consistent. Switch only after the output is
  successfully published and available to display; failed or cancelled work
  must not activate an incomplete result. Verify completion callbacks cannot
  switch another project's view and retain unrelated overlay preferences.
- [ ] Review progress reporting across alignment, camera optimization, cloud,
  mesh, texture, DEM, orthomosaic, import and export operations. Use one progress
  bar when it communicates the operation clearly; show overall and current-stage
  bars together only when each represents useful, distinct measured progress.
  Label their meaning clearly and remove redundant bars.
- [ ] Base percentages on available work counters and meaningful stage estimates.
  Show indeterminate progress when a total cannot be measured. Handle long
  preparation/finalization stages, cached work, retries and cancellation
  consistently, and report completion only after outputs are successfully
  published.
- [ ] Improve remaining-time estimates using observed throughput and stage
  duration, with sufficient samples before displaying an estimate. Update or
  suppress unreliable estimates when stages or workloads change. Compare the
  displayed percentages and ETA with actual completion times on representative
  small and large workloads, including CPU/GPU and cached/rebuild paths.
- [ ] Before releasing numerical changes, verify independent surveyed check
  points and controlled synthetic fixtures, calibration behavior, compatible
  horizontal/vertical reference systems, old-project load/export, affected
  downstream products and stale-result invalidation. Retain test and benchmark
  evidence and identify target-data/hardware checks still outstanding.

## Approved scope for 1.0.4 (2026-11-07)

The following scope shipped in 1.0.4 after the user reviewed the test installer and authorized publication.
The numerical review and later photo-only marker editing approval are recorded in
[release-review-104.md](release-review-104.md), which retains final validation evidence.

- [x] Rename the left Workspace tab/panel to **Project**. Replace the combined
  **Reference** tab with separate **Markers** and **Cameras** tabs, moving each
  table and its relevant controls into its own tab.
- [x] Use exactly two central tabs: **3D View** and **Plan View**. Plan View
  displays the selected photograph or orthophoto. Remove the separate Photo
  tab while preserving photograph interaction and marker placement/editing.
- [x] Put **Photos** on the right in the default layout. Hide **Console** and
  **Jobs** by default; opening either from the menu shows it as a floating
  window.
- [x] Remove the small local action strip above the Project tree (the four
  controls marked in the approved reference screenshot). Preserve access to
  required commands through the main toolbars and menus.
- [x] Remove the per-camera reference-use checkboxes from Cameras. Use valid
  photo GPS by default and add one global **Use Photo GPS** option in
  **Settings**. Adding markers must not automatically disable photo GPS.
  Disabling this option affects GPS reference use only; photographs remain
  included in alignment. Preserve the distinction between control and check
  points and review existing project/reference settings during implementation.
- [x] Persist and restore the latest appearance settings, panel layout,
  sizes/positions, active tab and last file/folder selection paths across
  application restarts. Use the new default layout on first launch.
- [x] Implement the approved About content below, with actual application
  metadata and offline access to the bundled LICENSE. Keep third-party
  licensing distinct and verify the installed application.
- [x] Perform the maintainability and affected-caller/workflow review required
  above, with focused cleanup only after confirming behavior and dynamic uses.
  Validate existing-project compatibility and preservation of project data,
  GPS/reference behavior, markers, failure/cancellation and offline operation.
- [x] Verify layout and text in Dark and Light themes at supported display
  scales; update affected user/developer documentation and retain validation
  evidence and unresolved hardware limitations.
- [x] Build a **1.0.4 test installer** for the user's review. Public release
  requires the user's separate approval after that review; scope approval is
  not publication authorization.

## License notice shipped in 1.0.4

- [x] Add a concise license notice to Help > About PhotoMesh Studio: personal
  and educational non-commercial use; commercial use, including company
  evaluation, requires prior written permission. Provide access to the full
  bundled LICENSE text and keep third-party licenses distinct. Verify readable
  layout in both themes and that the license can be opened offline in the
  installed application.

### Approved About content (2026-11-07)

Version 1.0.4 includes the following user-approved content. Retain it in subsequent versions. Use the actual application name/version
from application metadata; the license itself has no version number.

> **PhotoMesh Studio — [Application version]**
>
> Desktop photogrammetry application.
> Runs fully offline; no network connection is required for processing.
>
> Reconstruction: COLMAP (BSD), with optional GLOMAP (BSD) for compatible legacy workflows.
> Processing pipeline: fastpipe.
> User interface: PySide6 / pyqtgraph.
>
> **License**
>
> Free for personal and educational, non-commercial use. Commercial use, including evaluation for company workflows, requires prior written permission from Behdad Nayyerpour.
>
> Third-party components retain their respective licenses.
>
> **[View full license]**
>
> © 2026 Behdad Nayyerpour.

The View full license control must open the bundled LICENSE offline. Render
these as readable paragraphs with complete text in both themes. Keep version
and copyright metadata current without changing the approved licensing meaning.
The installed 1.0.4 acceptance run verified the approved About content and offline license viewer.
