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

Subsequent review reproduced one valid-format incompatibility: a scalar vertex
attribute literally named `list` was confused with the internal list-property
tag. The independent reference reader accepted it. A shared declaration-shape
check now distinguishes the two in the fast reader, general codec and reflected
face streaming. ASCII and both binary byte orders are covered through load,
rewrite, coordinate transform and world export. The affected local regression
group passed 127 tests. The `0fcdf3c` archive is superseded and must not be delivered;
the corrected source requires new candidate validation and a new immutable ZIP.

The earlier standalone download/apply/recovery-BAT test is tracked separately in
[run 43251700970](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43251700970).
Do not deliver the BAT until that test succeeds. No full Setup or final release
has been built or published, and no user acceptance has been recorded.

Remaining: actual downloaded-BAT validation, full licensing
review, complete rename/documentation/shortcut migration, and the remaining
approved next-version scope. Real CUDA reconstruction and surveyed target-data
checks have not been run for this candidate.

## Windows 2022 follow-up

The default Windows runner queue delayed acceptance, so the candidate and BAT
workflows now pin the supported Windows 2022 image. This changes CI configuration,
not application code. Its first full run exposed a timing-dependent pre-existing
test in photo staging: a rapid same-size rewrite did not reliably advance the
host filesystem's observed modification timestamp. `prepare_images` and its
metadata-stamp cache are unchanged from the source baseline. The test now advances
source and staged-file mtime explicitly by two seconds; all original copy-count
and byte-content assertions remain. This verifies the intended invalidation
contract deterministically without sleeps or a retry-to-green rule.

The separate existing limitation remains open: a source changed while preserving
all cached identity/size/timestamp fields cannot be detected by that metadata-only
cache. Review source freshness and its performance/accuracy tradeoff before final
release; do not describe this test correction as fixing that application behavior.

## Initial milestone ready for user testing

Application source `0f112b74f09dbeb99673a473cc7b6bb8918389f2` passed
[candidate run 43256088287](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43256088287):
809 passed / 8 skipped, exact installed icon/identity/dependency checks,
whole-runtime hash comparison and rollback. The PLY benchmark retained exact
tested attributes; warm-cache medians were 0.01193 s (reference) and 0.01343 s
(independent writer), so no generic speedup is claimed.

Delivery-only follow-up fixed two issues before handoff: Windows PowerShell did
not expose `Get-FileHash` in the inherited runner environment, so the bootstrap
now uses framework SHA256 and ZIP APIs; and the same candidate could not be
reapplied after rollback because its recovery directory already existed. New
attempts now retain distinct journals instead of overwriting previous evidence.
The new regression was reproduced failing before the fix and passes afterward.
The focused updater/branding/codec group passed 33 tests.

Updater revision `defc97310563b6c11228271ea1cfafd596c6ccb5` was repacked separately.
Every verified application/resource/dependency entry and original application
manifest field was compared byte-for-byte unchanged. R2 is 1,694,003 bytes,
SHA256 `f3b3486073a3f64f7df98d8abf1bfb8c67c35d75441eb7ff1e68b9d39aca5f7f`.
Artifact commit: `6da996b744a655247d9655db579de17da89214b0`.

[Actual BAT run 43265345704](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43265345704)
passed download/apply, offline installed PLY mesh/RGB/faces/coordinate-transform
and world-export checks, actual ROLLBACK.bat, reapplication of the same candidate,
preservation of the first journal, and a second actual rollback to 1.0.4. Both
applications used the installed Python and a custom path with Persian letters
and spaces. No personal projects or installed user application were touched.

The delivered single BAT was downloaded from that successful run and reproduced
byte-for-byte by the generator. The enclosing BAT artifact is `13966421668`, ZIP
SHA256 `b047ddcfc3a3764b73b7c9583dbe2ff2717398da8ae08fd01c478912219c277a`.
Candidate acceptance is pending user feedback. No complete Setup, final release,
repository rename or PDF update is authorized/completed by this milestone.
All remaining approved next-version work and open licensing/hardware checks stay
open; this is not a claim that the complete checklist has shipped.


### Reported BAT path handoff failure (2026-11-12)

The user's Inno registry InstallLocation ends in a backslash. Windows PowerShell
5.1 native argument quoting combined --root with --payload; Python failed resolving
that malformed path before any managed-file replacement. Previous acceptance
passed an explicit root without a final backslash and missed registry discovery.
The bootstrap now transports both paths through process environment variables
and constructs argv within Python, preserving drive/UNC roots and Unicode paths.
Four real Windows PowerShell child-process tests pass, including the reported
path, Unicode/spaces/apostrophe/ampersand, drive root and UNC with trailing slashes.
The actual BAT acceptance workflow now exercises registry discovery first and an
explicit trailing-backslash root on reapplication. Application/payload bytes are
unchanged. Reviewed generator, child entry point and acceptance callers; no PDF
or application/numerical changes are needed for this bootstrap-only fix.

Actual BAT run [43269518547](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43269518547) passed registry-discovered apply, installed offline PLY checks, rollback, explicit trailing-backslash reapply and second rollback. Verified BAT artifact 13966643906 matches local generator bytes; BAT SHA256 `3ad0a82d96b30bebb7e6e91603bfc9039f559298e760304ff1912cc12ce3a7f1`.


### Splash artwork quality iteration (2026-11-12)

The approved 1280-pixel artwork is retained. Painter-only minification aliased
terrain/mesh detail; appicon.draw now smooth-resamples at the painter device
resolution before drawing. Reviewed splash, About/window icon and ICO callers;
logical size, alpha, settings, project formats and processing remain unchanged.
Splash subtitle is exactly Desktop Photogrammetry App. Rendered and visually
checked at 100/125/150/200 percent; six existing startup/splash tests pass.
No user manual text/screenshots are edited, per the user's explicit instruction.
This small delta targets the already-applied first 1.0.5 candidate, with backups
and rollback; it is not acceptance/completion of the broader next-version scope.

Splash delta baseline is reconstructed from the SHA256-authenticated R2 manifest
plus its replacements/removals (106 app files), copied into a disposable stage
only after all installed hashes match. Local extra development files are excluded
from the baseline, not weakened or removed from the installation. The first
remote delta attempt rejected an extra baseline file before replacement; the
corrected archive is 12,794 bytes and still changes only appicon.py/splash.py.
