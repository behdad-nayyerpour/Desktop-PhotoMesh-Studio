# Lens2Mesh 1.0.5 candidate review

## Approved scope and delivery

Source baseline: `0650aadca18fa66554bd1abf29955d6bc4503dc4`.
The complete approved scope remains in release-quality.md. Work starts with
priority-one branding and dependency licensing, then the remaining numerical,
editing, classification, measurement and progress items. None of the remaining
items is considered complete merely because this candidate exists.

The selected artwork is `Lens2Mesh-L2M-v6b-icon.png`, approved 2026-11-12.
Incremental candidates must use the exact corrected public 1.0.4 installer
SHA256 `059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f`.
No full Setup may be built before explicit user acceptance; no public release
or repository rename is authorized by candidate approval.

## Maintainability and compatibility review plan

- Inventory display branding separately from persisted IDs, package/module
  names, project formats and third-party notices. Retain the original QSettings
  namespace, `.pmsx`, `photomesh-studio/2`, installation AppId and internal paths.
- Inspect icon callers (window, taskbar, splash, shortcuts, installer), export
  generators and captions. Retain script action IDs while changing captions.
- Review all PLY readers/writers before replacing `plyfile`; verify ASCII and
  both binary endiannesses, list properties, custom attributes, truncation,
  round trips, reflected face winding and world-coordinate precision.
- Audit the exact published runtime on a remote disposable runner, never using
  user projects or an installed personal runtime as the licensing audit source.
- Validate updater baseline binding, path containment, hashes, closed-app check,
  backup/rollback, interruption and unchanged runtime components. Test using
  disposable installations including paths with spaces and non-ASCII letters.
- Run focused checks, existing regressions and numerical acceptance; inspect
  final changes and affected callers. Separate automatic, manual and hardware
  evidence. Passing tests does not prove absence of bugs or license clearance.

## Manual assessment

Branding and later UI additions affect cover/About/Help and corresponding
workflow sections. The approved 105-page PDF remains unchanged pending separate
manual-edit approval. Do not regenerate unrelated pages.

## Evidence

Implementation and validation are in progress. No installer or licensing
clearance is claimed. Record actual results and remaining limitations here.
