# Packaging tools

## Current release

Use **[build_release.ps1](https://github.com/behdad-nayyerpour/photomesh-studio-improved/blob/main/packaging/build_release.ps1)** and **[release.iss](https://github.com/behdad-nayyerpour/photomesh-studio-improved/blob/main/packaging/release.iss)**
to produce one complete `PhotoMeshStudio_Setup_<version>.exe` and its SHA256.
Follow the [release guide](RELEASE.md). No separate Update EXE is produced.

The installer includes the English README, screenshot, and documentation folder
so **Help > Contents** can open the local guide without a network connection.

## Legacy compatibility

These scripts and templates remain because older portable/source installations
and packaging workflows use them:

| Files | Purpose |
|---|---|
| `build_dist.ps1`, `build_portable.ps1` | Previous portable distribution builders |
| `build_update.ps1`, `UPDATE_README.txt`, `check_update.bat` | Previous portable code-update packages |
| `update.ps1` | Git-based updater used by root batch wrappers |
| `README_FIRST.txt`, `install_offline.bat`, `PhotoMesh Studio.bat` | Previous portable first-run workflow |
| `check_install_path.py`, `create_shortcut.ps1`, `fix_shortcut_icon.ps1` | Compatibility helpers |
| `run_tests_offline.bat` | Portable-environment test helper |

They are not the update method for an EXE installation.
See [archived portable instructions](../docs/archive/portable-installation.md).
