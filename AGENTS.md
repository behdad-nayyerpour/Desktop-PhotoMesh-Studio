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
