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
