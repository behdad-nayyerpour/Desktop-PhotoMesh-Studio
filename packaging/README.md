# Packaging tools

Use **[build_release.ps1](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/blob/main/packaging/build_release.ps1)**
and **[release.iss](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/blob/main/packaging/release.iss)**
to produce one complete `PhotoMeshStudio_Setup_<version>.exe` and its SHA256.
Follow the [release guide](RELEASE.md). The same Setup installs a new copy or
replaces an existing EXE installation. No separate Update EXE is produced.

## Files in this folder

| File | Purpose |
|---|---|
| `build_release.ps1` | Stage the app and tested runtime, validate imports, build Setup and its checksum |
| `release.iss` | Inno Setup definition, managed installation folders, shortcuts, and launch action |
| `fix_shortcut_icon.ps1` | Repair the icon of an existing shortcut; called by `photomesh/shortcut_icon.py` in source installations |
| `RELEASE.md` | Installer build and release validation instructions |
| `README.md` | This overview |

The installer includes the English README, screenshot, and documentation folder
so **Help > Contents** can open the local guide without a network connection.
The shortcut repair helper is retained because the application calls it when
available. Setup itself creates shortcuts with the application icon.

The obsolete portable ZIP builders and Git update scripts have been removed.
Use [Installing a newer version](../UPDATING.md) for the current workflow.
