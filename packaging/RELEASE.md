# Build the Windows installer

[Packaging overview](README.md) · [Development guide](../docs/development/README.md)

## Required test-and-approval order

For application changes, first deliver a Windows `.bat` updater that downloads
only changed installed components and required dependencies for the user's test.
Use an exact baseline/candidate, verify file hashes, require the app to be closed,
and preserve backups and user data. See the repository's
[incremental delivery policy](../AGENTS.md#incremental-test-delivery-before-setup-approved-2026-11-10)
and the [next-version checklist](../docs/development/release-quality.md).

Do not build a complete Setup until the user explicitly accepts that tested
candidate. Build from the accepted revision and validate the installer afterward.
Public publication remains a separate authorization. The commands below describe
the full installer stage after candidate acceptance.

Each release produces one offline file: `PhotoMeshStudio_Setup_<version>.exe`.
It contains the app, Python, Python packages and COLMAP, with optional legacy
GLOMAP. Users run
the new Setup on the existing installation; it replaces the managed app,
Python, and tools folders. Projects, source photos, and processing results
should be kept outside the installation folder.

Build from the repository checkout with Inno Setup:

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


## Destination selection in the next installer

The next build explicitly sets `DisableDirPage=no` so the destination page is
shown during fresh installation and reinstall/upgrade. `UsePreviousAppDir`
still supplies the previous installation folder as the initial suggestion.
Before release, verify a custom destination and the resulting Start menu and
desktop shortcut targets, including paths with spaces and non-ASCII characters.

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

## Verified 1.0.4 distribution

[PhotoMesh Studio 1.0.4](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/tag/v1.0.4) includes the full offline Windows Setup and its checksum. The corrected 1.0.4 Setup is 861,743,162 bytes. Its SHA-256 digest is `059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f`.

The original [installer run](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42383383859) tested upgrading 1.0.3. The corrected [installer run](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/42411192019) tested replacing the installed 1.0.4. The [publication workflow](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/blob/main/.github/workflows/replace-104-setup.yml) verifies the public executable byte-for-byte against the corrected candidate. The [release review](../docs/development/release-review-104.md) records the validated source and numerical results.

The 1.0.3 installer used in the original upgrade test has since been removed from its public release. For a new build with the same runtime layout, install the current release in a staging environment and supply its installation directory as `-RuntimeSource`. Reproducing the historical upgrade test requires a retained copy of the original 1.0.3 Setup.

Documentation and screenshot changes appear on GitHub immediately. The offline documentation in each Setup reflects its build date.

## Application license

The builder copies the root `LICENSE` into the staged application. Inno Setup
shows that file as the application's license agreement. Preserve the separate
third-party license notices; the application license does not replace them.
The 1.0.4 installation also provides offline access to the bundled license through Help > About.
