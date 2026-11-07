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
