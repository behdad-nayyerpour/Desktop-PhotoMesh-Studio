# Development

[Documentation](../README.md) · [Architecture](architecture.md) ·
[Installer build](../../packaging/RELEASE.md)

## Run from source

Source setup downloads Python packages and needs internet access.
Install a compatible Python and Git first, then use PowerShell:

```powershell
git clone https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio.git
cd Desktop-PhotoMesh-Studio
.\setup.bat
.\run.bat
```

A private repository may require GitHub authentication.
The Setup EXE is the simpler option for normal application use.

## Reconstruction tools

Source installations need a separate COLMAP installation.
Select its path in **Project > Preferences > Advanced**, add it to PATH, or place
it in `tools\colmap` next to the application.
Get builds from [COLMAP releases](https://github.com/colmap/colmap/releases)
and choose one compatible with your GPU and NVIDIA driver.

Dense stereo requires the CUDA build and an NVIDIA GPU.
A non-CUDA build can perform alignment and other supported CPU tasks.

GLOMAP is optional. Place its executable at
`tools\glomap\bin\glomap.exe` or configure its path.
Get builds from [GLOMAP releases](https://github.com/colmap/glomap/releases).

## Tests

Install [development requirements](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/blob/main/requirements-dev.txt) in the
development environment.

```bat
run_tests.bat
run_tests.bat C:\path\to\photos
set "PM_TEST_DENSE=1" && run_tests.bat C:\path\to\photos
```

On Linux, with dependencies and Qt system libraries installed:

```sh
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

The default GitHub Actions job runs the non-GPU suite. Real photo, CUDA, local
project, and real OpenGL checks require the corresponding resources and may be
skipped in CI. The Windows job is available through manual workflow dispatch.

## Repository map

| Path | Purpose |
|---|---|
| `photomesh/` | Application code and resources |
| `main.py` | Application entry point |
| `tests/` | Unit, GUI, integration tests, and required fixtures |
| `packaging/` | Current Setup builder, installer definition, guides, and active shortcut repair helper |
| `docs/` | User and developer documentation |
| `tools/` | Developer utilities; locally supplied reconstruction binaries are ignored |
| `benchmark.py`, `dense_benchmark.py`, `gcp_benchmark.py` | Developer benchmark entry points |
| `setup.bat`, `run.bat`, `run_tests.bat` | Source-environment helpers |

Benchmark scripts remain at their existing paths. They are developer tools,
not part of the normal installation workflow.

## Documentation and maintained tools

The application opens the root `README.md` through **Help > Documentation**.
The Setup builder includes that README, both project screenshots, the `docs` folder,
and the root changelog and update guide.

The English changelog remains in `CHANGES.md`; no parallel changelog is maintained.
User documentation is in `docs/`, with current update instructions in `UPDATING.md`.

Legacy Git updaters, portable ZIP builders, and their obsolete guides have been
removed. Use the complete Setup for installed releases. Source checkouts can be
updated with normal Git commands; resolve or save local changes before updating.

The benchmark and GUI utility scripts remain usable development entry points.
Tests named after earlier versions still protect behavior in the current app;
their versioned names do not mean they are obsolete. Binary shape fixtures and
the application icon are required resources.

See [packaging tools](../../packaging/README.md) for the remaining build files.

## Required release quality review

Every application version includes the [maintainability and release quality
checklist](release-quality.md). Review duplication, dead code, readability and
workflow interactions alongside correctness, compatibility and performance.
The root [contributor instructions](../../AGENTS.md) apply to coding agents as
well. The [1.0.3 baseline review](release-review-103.md) records the repository sweep,
manual findings, cleanup, validation and remaining target-hardware checks.

## Current candidate validation

[1.0.3 release review](release-review-103.md) is the current consolidated review.
The temporary toolbar/error/icon preview notes have been removed after their
relevant findings and evidence were consolidated there. Earlier version-specific
engine/workflow reports remain historical evidence, as do regression tests.

