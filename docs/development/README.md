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
Select its path in **Tools > Preferences > Advanced**, add it to PATH, or place
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
| `packaging/` | Current Setup builder and retained legacy distribution tooling |
| `docs/` | User and developer documentation |
| `tools/` | Developer utilities; locally supplied reconstruction binaries are ignored |
| `benchmark.py`, `dense_benchmark.py`, `gcp_benchmark.py` | Developer benchmark entry points |
| `setup.bat`, `run.bat`, `run_tests.bat` | Source-environment helpers |
| `update.bat`, `rollback.bat`, `setup_git_update.bat` | Legacy source/portable update compatibility |

Benchmark scripts remain at their existing paths. They are developer tools,
not part of the normal installation workflow.

## Documentation compatibility

The application opens the root `README.md` through **Help > Contents**.
The Setup builder includes that README, its screenshot, the `docs` folder,
and the root compatibility guides.

`CHANGES.md`, `UPDATING.md`, and `INSTALL_OTHER_LAPTOP.md` retain their
original names because older scripts refer to them.
The English changelog remains in `CHANGES.md`; no parallel changelog is maintained.

See [packaging tools](../../packaging/README.md) before removing an apparently
old script. Required test fixtures and runtime resources must remain in place.
