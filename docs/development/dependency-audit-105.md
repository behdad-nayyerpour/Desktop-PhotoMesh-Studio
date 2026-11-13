# Exact-runtime dependency review for 1.0.5

## Performance/manual iteration review (2026-11-13)

The user requested completion of the engineering review and one combined BAT.
Fresh static PE inspection of the exact published installer ran on a disposable
Windows runner in [run43382179244](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43382179244).
It read1378 PE files. Artifact14016927512 SHA256
`38de00358b370f8da5ea10d44b4f22eaf155b3f0f64c36a1857282ba34f25a2f`
is retained locally. Application/pyqtgraph imports, native consumers and QML
families were reviewed together; absence in a text search alone was not used.

The explicit removal plan covers881 unchanged PySide6 optional files (47.8MiB),
including78 PE files: GPL-only addon families, their transitive static consumers,
associated QML resources and binding stubs. Core/Gui/Widgets/OpenGLWidgets and
the app's image/platform plugins remain. These optional families are not part of
Lens2Mesh's documented application or script API. The updater permits only the
reviewed paths, validates exact baseline hashes, never replaces a Python binary,
and keeps the allowlist with each rollback journal. Existing engine bytes remain.
Full installed UI/processing/rollback validation is required below before delivery.

The approved unchanged PDF and a separate offline Third-party Notices entry are
added to Help; About also links notices. The notice index collects197 upstream
texts for76 named Python distributions plus full GPL/LGPL/GCC exception and
COLMAP/ALIKED/LightGlue texts. Source/replacement information is separate from
the application's own license, which is unchanged. Exact inventory/evidence hashes,
native/model hashes and outstanding provenance are retained in its review.json.

Primary-source review:
- [Qt module terms](https://doc.qt.io/qt-6/licensing.html) distinguish GPL-only
  addons from modules available under LGPL; top-level PySide metadata is not
  sufficient. [Qt's LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations)
  were checked for notice, license text, shared-library replacement/debugging and
  corresponding-source access. [PySide6 6.12.0 source archives](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/)
  exist, but that does not establish provenance of the split6.12.0.140 packages.
- [COLMAP4.2.1 build recipe](https://github.com/colmap/colmap/blob/4.2.1/.github/workflows/build-windows.yml)
  explicitly removes install/share. Its [vcpkg registry baseline](https://github.com/colmap/colmap/blob/4.2.1/vcpkg-configuration.json)
  is127402f1c75bb3d5ff6bce04b285faa4930a5aca. Restoring only COLMAP's BSD text
  cannot establish all linked native dependencies' redistribution conditions.
- [LightGlue ONNX](https://github.com/colmap/LightGlue-ONNX#license) explicitly
  covers pretrained LightGlue weights with Apache-2.0, including the bundled
  ALIKED/SIFT variants. [ALIKED ONNX](https://github.com/colmap/ALIKED-ONNX/blob/main/LICENSE)
  supplies BSD-3-Clause. The known hashes remain in the engine asset manifest.
- [CUDA13.2 EULA](https://docs.nvidia.com/cuda/archive/13.2.0/eula/index.html)
  was collected. The PE evidence also shows ONNX's CUDA provider imports CUDA12
  libraries while the legacy engine contains CUDA11 runtime libraries; the
  modern engine's toolkit label alone cannot clear all those binaries. Existing
  optional provider probing/fallback is unchanged in this iteration.

Engineering findings and remediation are recorded, but **complete redistribution
clearance remains open**: exact matching native source/build records, split Qt
package provenance and version-specific CUDA evidence are still required before
the final public Setup. No engine is silently removed or replaced, and no claim
of legal clearance follows from the BAT tests. Retained unresolved gates below
are historical context and remain subject to these newer findings.

Final validation at281db7d succeeded:908 Windows tests,904 Linux tests,
80 actual installed tests, native mesh DEM offline, complete25384-file candidate
inventory and full26196-file rollback comparison. The actual BAT independently
restored all881 Qt targets twice. See release-review-105.md for immutable artifact
hashes and run links. These checks close the cleanup/runtime compatibility gate,
not the unresolved native-source/provenance redistribution gates above.

This is an engineering inventory and an unfinished redistribution review, not
legal clearance. The application's own license has not been changed.

## Verified evidence

The corrected public 1.0.4 Setup (861,743,162 bytes; SHA256
`059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f`)
was installed on a disposable GitHub Windows runner. No user installation,
photo or project was used for this audit.

The [initial audit run](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43230465128)
retains per-file hashes for **26,196 files**, metadata for **75 Python
distributions**, and collected license/NOTICE/metadata evidence. Its artifact
ID is `13951355419`; ZIP SHA256 is
`025db010f0b4f05ab7ac1bbe83baea07c41ed5e234c29099cd9f7c106fc1347c`.
That run's first patch smoke check failed on console encoding and was not
approved for delivery. The evidence itself was collected before applying it.

## Findings and actions

| Component | Exact evidence | Status |
| --- | --- | --- |
| plyfile 1.1.5 | Installed metadata labels GPL v3 or later; direct application imports existed in PLY display, cloud, export and georeference paths | Replaced by independent `plycodec.py`; cross-reader tests use plyfile only in development. Candidate removal is limited to verified installed RECORD files, with baseline hashes, backup and rollback. |
| PySide6 / Essentials / Addons / shiboken6 6.12.0; Pdf / WebEngine 6.12.0.140 | Installed metadata lists alternative LGPL/GPL/commercial terms. The collected wheel evidence includes commercial license-reference texts | Full module-by-module terms, missing license texts, corresponding-source and replacement/relinking material still require review; metadata is not proof of compliance. |
| COLMAP 4.2.1 CPU and CUDA | Exact engine manifests and hashes were collected; legacy COLMAP and GLOMAP are also present | Native dependency provenance and redistribution notices remain open. The inventory did not find standalone license/NOTICE/COPYING-named files under `tools/`; that filename observation is not a conclusion about embedded notices or rights. |
| Three ONNX models in each modern engine | Exact model hashes match the engine manifest names: ALIKED and ALIKED/SIFT LightGlue | Weight-specific provenance and redistribution terms remain open; a code repository's license alone does not establish weight permissions. |
| CUDA and native DLLs | Exact file hashes retained | Verify the applicable version's redistribution list and notices before a final release. |

The candidate inventory is collected again after patching. An independent
comparison must establish that only manifest-listed app files and the replaced
PLY dependency changed; unchanged Python and engines are not downloaded again.
Recovery backups are intentionally excluded from the distributed-file inventory.

## Release gates still open

The exact inventory also includes `PySide6/Qt6Charts.dll`, `Qt6Graphs.dll`,
`Qt6Quick3D.dll` and `Qt6VirtualKeyboard.dll`. The official Qt 6.12 documentation
lists commercial or GPLv3 terms for [Qt Charts](https://doc.qt.io/qt-6/qtcharts-index.html)
and [Qt Graphs](https://doc.qt.io/qt-6/qtgraphs-index.html). Therefore the package's
top-level alternative-license metadata must not be treated as evidence that
every bundled Qt addon is LGPL. Review actual module dependencies, plugins/QML
and runtime usage before removing unnecessary modules; a text-search absence
alone is not a dependency review. This finding remains open and is not a claim
of legal clearance or a decision to change the application's own license.

- Review exact native/Qt/model licensing evidence and collect required notices
  and version-matched source/replacement information. Do not claim the complete
  bundle is cleared because the direct GPL Python dependency was replaced.
- Retain the corrected candidate's inventory and installed smoke/rollback results.
- Complete remaining approved numerical/UI scope and applicable hardware checks.
- Obtain explicit candidate acceptance before building a full Setup, and separate
  authorization before public publication. This test branch is not a release.
