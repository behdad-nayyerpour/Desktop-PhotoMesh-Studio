# Exact-runtime dependency review for 1.0.5

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

- Review exact native/Qt/model licensing evidence and collect required notices
  and version-matched source/replacement information. Do not claim the complete
  bundle is cleared because the direct GPL Python dependency was replaced.
- Retain the corrected candidate's inventory and installed smoke/rollback results.
- Complete remaining approved numerical/UI scope and applicable hardware checks.
- Obtain explicit candidate acceptance before building a full Setup, and separate
  authorization before public publication. This test branch is not a release.
