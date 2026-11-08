# Contributor instructions

These instructions apply throughout this repository.

## Required review for every version

Read [the release quality checklist](docs/development/release-quality.md) before
planning a version, changing application code, or preparing a release.

- Include a maintainability review in every version's work plan, alongside
  functionality, numerical accuracy, hardware compatibility and performance.
- Review changed code, its callers and affected workflows in detail. Also sweep
  the repository for duplicated logic, stale references, unused paths/resources
  and inconsistent responsibilities; inspect findings before changing them.
- The baseline repository sweep and targeted contract review are recorded in
  docs/development/release-review-103.md. Keep that evidence and perform the
  per-version review below for subsequent changes. Earlier engine/regression
  validation alone did not establish the absence of duplication or dead code.
- Prefer focused, behavior-preserving cleanup. Never merge similar-looking
  calculations, remove legacy compatibility or delete resources merely because
  a text search or static tool finds no callers.
- Keep shared rules in one appropriate module, names and units explicit, and
  comments focused on intent, assumptions and numerical constraints.
- Validate affected behavior and interactions after refactoring. Compare
  equivalent processing workloads when changing hot paths; preserve accuracy,
  cancellation, project compatibility and offline operation.
- Record the review scope, findings, cleanup, validation and remaining work in
  the release/PR notes. Distinguish manual review from automated checks. Do not
  claim a whole-repository audit or zero remaining bugs from passing tests alone.

See the [development guide](docs/development/README.md) for the repository map
and existing test commands. Documentation-only changes do not require a new
application version or Setup.

## User manual maintenance (approved 2026-11-08)

- For every application update, assess whether changed menus, settings,
  workflows, defaults or installation/export behavior affect the user manual.
- If an update is needed, explain the affected sections and ask the user before
  editing the manual. Approval of application changes is not approval to rewrite
  the manual. If no manual change is needed, retain it unchanged.
- After approval, update only the affected text, screenshots and necessary
  version/index/cross-reference metadata. Preserve approved unaffected content;
  do not regenerate or redesign the whole manual for a small application change.
- Preserve the complete English 1.0.4 manual approved by the user as the baseline,
  not the superseded short example guide. Retain editable sources and original
  screenshots. Keep screenshots sharp and lossless; render and visually verify
  affected PDF pages and any pagination/index changes before delivery.
- The next-version checklist includes offline access to the bundled PDF from
  Help. Follow that checklist for implementation and installed-build validation.
