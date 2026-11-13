# Packaging tools

Use **[build_release.ps1](https://github.com/behdad-nayyerpour/Lens2Mesh/blob/main/packaging/build_release.ps1)**
and **[release.iss](https://github.com/behdad-nayyerpour/Lens2Mesh/blob/main/packaging/release.iss)**
to produce one complete `Lens2Mesh_Setup_<version>.exe` and its SHA256, after candidate acceptance.
Follow the [release guide](RELEASE.md). The same Setup installs a new copy or
replaces an existing EXE installation. No separate Update EXE is produced.

## Files in this folder

| File | Purpose |
|---|---|
| `build_release.ps1` | Stage the app and tested runtime, validate imports, build Setup and its checksum |
| `release.iss` | Inno Setup definition, managed installation folders, shortcuts, and launch action |
| `engine-assets.json` | Pinned engine/model download URLs and SHA256 values |
| `fix_shortcut_icon.ps1` | Repair the icon of an existing shortcut; called by `photomesh/shortcut_icon.py` in source installations |
| `migrate_shortcuts.ps1` | Rename only this install's per-user legacy shortcuts, with backup and collision protection |
| `requirements-runtime-win313.lock` | Exact Windows CPython3.13 wheel versions and official SHA256 pins |
| `verify_runtime_lock.py` | Reject staged version drift or unexpected packages before Setup compilation |
| `RELEASE.md` | Installer build and release validation instructions |
| `README.md` | This overview |

The installer includes the English README, both theme screenshots, and the documentation folder
so **Help > Documentation** can open the local guide without a network connection.
The shortcut repair helper is retained because the application calls it when
available. Setup itself creates shortcuts with the application icon.

The obsolete portable ZIP builders and Git update scripts have been removed.
Use [Installing a newer version](../UPDATING.md) for the current workflow.
