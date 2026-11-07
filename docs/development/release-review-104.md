# 1.0.4 implementation and review

## Scope and status

Implementation and automated candidate acceptance are complete on the isolated
release branch. User acceptance is pending; no public publication is authorized. The approved scope is in [release-quality.md](release-quality.md).
The review includes maintainability, functional and numerical contracts,
project compatibility, failure/cancellation, offline operation and performance.

## Changes under validation

- Project, Markers and Cameras side panels; Photos on the right.
- Two central tabs with shared Plan View and retained photo/ortho renderer state.
- Console/Jobs initially hidden and opened as floating panels.
- Removed Project's local action strip; existing menu/context commands remain.
- One project-wide Use Photo GPS setting controls pair preselection and camera
  references without removing photographs from alignment. Markers do not toggle it.
- Legacy GPS opt-outs conservatively disable the global policy until explicit
  opt-in; serialized per-camera legacy fields remain readable and unchanged.
- Saved window layout, active central tab, Plan View renderer and render styles;
  per-operation file picker directories.
- Approved About and full bundled offline license viewer.
- Fixed failed photo-open retaining the previously opened photo identity.
- Route GPS references through exact model aliases, including images sharing a
  stem with different extensions; ambiguous legacy stem-only GPS matches are
  excluded. Ambiguous legacy marker stems are also excluded rather than
  assigned to an arbitrary camera. Unresolved duplicate legacy
  photo names are excluded instead of swapping coordinates.
- Retain selected-photo enable/remove commands in Edit after removing the local
  strip, and block those commands during project preparation/processing.

## Validation

Intermediate code commit `baac917801dfaf6894df6280bf167ef76ea7e5ac` passed
[Tests run 42372739642](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42372739642):
692 passed, 8 skipped on Linux and Windows; Linux compilation/static checks,
Mesa overlay smoke and the existing equivalent-workload performance gates passed.
The skips remain explicit hardware/data requirements. The follow-up palette/table head `10977974c75ab9ce4ca408578e1d2d4a0a0cece1`
passed 694 tests with 8 skips on Linux and Windows in
[run 42373162703](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42373162703).
Its Light screenshots were manually inspected after resetting existing styled
widget palettes; the toolbar, Photos, Properties and view background now switch
consistently. Dark/Light About and full license were inspected, with automated
wrapped-label height checks at scale factors 1, 1.5 and 2.
Final application commit:
`bc4f35f205b96c9a6666010cc9c86dcb510e26db`.

- [Final Tests run 42373636315](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42373636315):
  **696 passed, 8 skipped** on Linux and Windows; compile/undefined-name checks,
  Mesa overlay smoke and equivalent-workload performance gates passed.
- Final inventory: 134 Python files including tests/tools, 72 app modules,
  zero static findings or exact nontrivial function-body duplicate candidates;
  35 zero-text-reference leads remain for the reasons described below.
- [Candidate run 42373636312](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42373636312):
  **696 passed, 8 skipped** again on Windows, real COLMAP 4.2.1 CPU numerical
  acceptance with known/self-calibration fixtures, SIFT incremental/global and
  fastpipe plus ALIKED/LightGlue; bounded large-image and downstream checks passed.
  Synthetic camera RMS ranged from approximately 0.012 to 0.042 m across those
  fixtures; these are not claims of real survey accuracy.
- Production builder reused the SHA256-verified public 1.0.3 runtime and pinned
  offline engines/models. The complete test installer upgraded a disposable
  1.0.3 installation; obsolete managed-code probe was removed, external metadata
  fixture was unchanged, installed application hashes matched source, and offline
  About/full LICENSE passed in Dark/Light.
- Manual review of final-head layout captures and wrapped-dialog checks at scale
  1/1.5/2 completed. The installed acceptance captures are in the candidate artifact.

## Test installer identity

- EXE: `PhotoMeshStudio_Setup_1.0.4.exe`
- Size: 860525023 bytes.
- EXE SHA256: `99b4e3cd99314649eccb081e5f5192eabc8950a38556ffdd0fd2790eacd1e774`.
- [Candidate artifact 13575311053](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42373636312/artifacts/13575311053):
  860319281-byte ZIP, includes Setup/checksum, test-build notes, native-engine
  evidence and installed acceptance/screenshots.
- ZIP SHA256: `79f8ffabe075c0ec948a2ed287b3a145030bcf77eac50c469fb0b8421fa8a37d`.
- Artifact expires 2026-11-21. No GitHub Release/tag was created or existing
  public asset replaced. Later documentation-only evidence updates do not
  rebuild or change this installer.

## Remaining acceptance

The user should close the app, install the test Setup and review the layout,
photo/ortho selection, markers, Use Photo GPS and restart persistence on a copy
of a project. Real CUDA processing, real-data accuracy/performance and target
driver/OpenGL behavior remain hardware acceptance tasks. Public publication
requires the user's separate approval.

New tests exercise Plan View/marker interaction, failed
photo opens, GPS settings and legacy policy, picker cancellation and UI restore.
Existing tests for superseded UI behavior are updated to the approved contracts.

## Review evidence and limits

The AST/static inventory covered 133 Python files including tests/tools and
72 application modules at that intermediate head. It reported no F401/F811/F841
or undefined-name findings and no exact nontrivial function-body duplicate
candidates. Its 36 zero-text-reference candidates include Qt virtual methods,
Python protocol methods and retained public/legacy helpers; none were deleted
just for lacking textual references. This is an inventory plus targeted manual
contract review, not proof that every path is bug-free.
The obsolete local Project-strip builder and the camera checkbox signal/slot
were removed only after checking their Qt connections and affected tests.
Selected-photo actions remain in Edit, and legacy action IDs alias current
commands without recreating the old menu layout.

Found/fixed during review: failed-photo stale identity, model-name/GPS alias
mismatch, a dock visibility/menu feedback loop introduced by the new floating
behavior, GPS-preselection feedback overriding the global policy, stale palettes
on theme switches, and repeated per-row evaluation of project GPS policy.


Read the main window and its reference, marker, shape, toolbar and registration
callers, project serialization, GPS frame validation and fastpipe pair selection.
Existing CPU/GPU processing variants and numerical methods are retained.
No user files or local working copies were inspected or modified.
Real CUDA reconstruction, actual survey accuracy and driver-specific displays
remain target-hardware checks; passing synthetic tests cannot establish these.
