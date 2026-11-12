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
workflow sections. The approved 105-page PDF remains unchanged: the user declined
PDF changes on 2026-11-12. Do not regenerate unrelated pages or change its branding.

## Evidence

Implementation and validation are in progress. No installer or licensing
clearance is claimed. The exact-runtime evidence and unresolved licensing
work are in [dependency-audit-105.md](dependency-audit-105.md).

- Branding commit `38691f5`: Linux and Windows regression workflows passed.
  The candidate workflow reported 793 passed / 8 skipped on Windows. Its
  installed update check exposed a non-ASCII console message problem, corrected
  in the next revision. This candidate was not delivered.
- Independent PLY commit `c2bd80b`: Linux and Windows regression workflows
  passed; the candidate workflow reported 806 passed / 8 skipped. Its installed
  rollback smoke assertion mistakenly imported the checkout ahead of the installed
  application. The corrected check now asserts the imported module's installed
  path explicitly. An independent complete-file inventory comparison is added.
- Local focused codec/export/numerical/updater checks passed (110 tests).
  Local full-suite execution used an old development environment missing dash
  and ezdxf and hit long temporary paths; that run is not full-suite acceptance.
  One marker-filter failure was also reproduced on the untouched source baseline;
  the fresh remote test environment passes it. Do not change marker calculations
  or weaken tests to hide that environment discrepancy.
- One-million-vertex scalar PLY comparison, three repeated writes: local medians
  0.00502 s (development reference) and 0.00517 s (independent writer), with
  exact attribute equality via the separate reader. This is a warm-cache local
  microbenchmark, not an end-to-end GPU or peak-memory benchmark.
- Updater fixtures cover modified baselines, corrupt payloads, path traversal,
  running processes, a failed second replacement, power-loss temporary files,
  deliberate dependency removal and preservation of later user edits on rollback.

## Verified initial incremental candidate

Source `0fcdf3c9fb4b4dd6b3d77b884004048364b2b063` passed the Linux and Windows
[Tests workflow](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43235599291).
The [candidate workflow](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43235599102)
also passed: 806 tests passed and 8 hardware/data-dependent tests were skipped.
Installed module-origin, new icon, dependency removal and rollback identity
checks passed using the exact corrected public 1.0.4 baseline in a path with
spaces and Persian letters. The independent runtime comparison verified all
26,190 candidate files against the baseline plus the explicit patch manifest;
no unlisted Python or engine file changed.

The one-million-vertex remote comparison preserved every tested attribute;
median write times were 0.01270 s for the separate development reference and
0.01218 s for the independent writer (three repetitions, warm-cache fixture).

Candidate ZIP: `Lens2Mesh_TestPatch_0fcdf3c9fb4b.zip`, 1,693,777 bytes, SHA256
`5cfafb3ec8a2530e2003189696390b18ebd2f6e6bd60eb3bdab1147e143ad110`.
The enclosing evidence artifact is `13952263599`, SHA256
`a43b362489c92d13bdd63b0bfc7fd0adb1f9d786ad25cf73fff24d3f59cb5cbf`.
The ZIP is preserved on the artifact-only branch at commit
`dddd2d6c11da6dbefd345fba4edbdb6c895fba9e`; the downloader binds to that exact
commit rather than a moving branch.

The actual standalone download/apply/recovery-BAT test is tracked separately in
[run 43251700970](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43251700970).
Do not deliver the BAT until that test succeeds. No full Setup or final release
has been built or published, and no user acceptance has been recorded.

Remaining: actual downloaded-BAT validation, full licensing
review, complete rename/documentation/shortcut migration, and the remaining
approved next-version scope. Real CUDA reconstruction and surveyed target-data
checks have not been run for this candidate.
