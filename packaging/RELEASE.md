# Build the Windows installer

[Packaging overview](README.md) · [Development guide](../docs/development/README.md)

Each release produces one offline file: `PhotoMeshStudio_Setup_<version>.exe`.
It contains the app, Python, Python packages and COLMAP, with optional legacy
GLOMAP. Users run
the new Setup on the existing installation; it replaces the managed app,
Python, and tools folders. Projects, source photos, and processing results
should be kept outside the installation folder.

Build from the repository checkout with Inno Setup (the 1.0.3 candidate was verified with Inno Setup 6):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging/build_release.ps1 `
  -RuntimeSource "C:\path\to\installed\PhotoMesh Studio" `
  -ISCC "C:\path\to\Inno Setup\ISCC.exe" `
  -OutputDir "C:\path\to\release-output" `
  -StageDir "C:\path\to\fresh-stage"
```

`RuntimeSource` may point to a tested development folder containing
`photomesh-studio\.venv`, `tools\colmap`, and `tools\glomap`; or to an
existing installer-based PhotoMesh Studio installation containing
`python\python.exe`, `app\runtime.id`, and the two tools folders.
The source is read but not changed. The builder validates copied Python
packages, creates the Setup EXE, and writes a matching `.sha256` file.
Choose a fresh stage directory for each build.

Before preparing a new release, complete the [release quality
checklist](../docs/development/release-quality.md) and retain the review evidence
with the version's existing review document or PR/release notes. Passing tests
alone does not establish a maintainability or duplicate-code audit.

Before publishing, install the new Setup over a test installation, confirm
Help > About shows the new version, and run a small real photo project on
the target hardware. The automated test suite does not exercise a full
COLMAP/GPU reconstruction. The EXE is not code signed.


## Engine bundle retained from 1.0.2

The builder prepares COLMAP 4.2.1 CPU/CUDA engines plus the local ALIKED/LightGlue
models with fixed SHA256 digests. The tested source COLMAP is retained as a legacy
GPU SIFT/dense fallback; legacy GLOMAP is optional. Python packages are reused from the
tested RuntimeSource as before.

Initial preparation needs internet access on the build machine. Downloads are
cached in `%LOCALAPPDATA%\PhotoMeshStudioBuild\engine-cache`; use `-EngineCache`
to choose another folder. A subsequent build can use `-OfflineBuild` when all
verified cache entries are present. Target users receive the engines and models
inside the complete Setup and processing needs no network access.

Native CPU integration and numerical benchmarks are documented in the
[engine review](../docs/development/engine-modernization-102.md). GPU behavior
must additionally be checked on target hardware before distributing a release.

## Verified 1.0.3 distribution

[Actions run 42310283579](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42310283579)
built the complete candidate from `127c682c6d05d61093843f5a1ed8a23f833005d8`.
It reused the SHA256-verified 1.0.2 runtime, checked runtime identity and staged
imports, then installed the new Setup over a disposable 1.0.2 installation.
All 68 application module names and hashes matched; obsolete managed code was
removed and an external project-metadata fixture was preserved. Installed
version, About, resources and split-button captions passed.

The user approved the installed candidate for public distribution on 2026-11-07.
The public release reuses that exact Setup/checksum. Remaining target-hardware
checks are recorded in the [release review](../docs/development/release-review-103.md).
Documentation-only follow-ups do not alter that tested executable or require a
new Setup; a later source build will include the updated documentation.

The one-time 1.0.3 publication and archive workflows were retired after success;
use the production builder above for later versions. Historical Actions evidence
remains in the release review. Retired workflows are recoverable from Git history
and are not current release instructions.
