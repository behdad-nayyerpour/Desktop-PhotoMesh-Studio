# Installation and requirements

[Documentation](README.md) · [User guide](user-guide.md)

## Windows installer

1. Open [Releases](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/latest).
2. Download `PhotoMeshStudio_Setup_<version>.exe`.
3. Run Setup and choose an installation folder. The default is
   `%LOCALAPPDATA%\Programs\PhotoMesh Studio`.
4. Start PhotoMesh Studio from its Start menu or desktop shortcut.

The installer includes Python, its packages and COLMAP; compatible legacy
GLOMAP is optional.
Installation and processing can run offline after the file is downloaded.
You do not need to install Git or Python separately.

To install a later version, close the app and run its complete Setup.
See [Updating](../UPDATING.md).

## Requirements

| Component | Requirement or guidance |
|---|---|
| Operating system | Windows 10/11, 64-bit, for the distributed installer |
| Dense reconstruction | NVIDIA GPU, a compatible driver, and a CUDA-enabled COLMAP build |
| CPU processing | Alignment and meshing from existing points can run without CUDA |
| 3D display | OpenGL-capable graphics driver |
| Memory | 16 GB is a practical starting point; large surveys may need 32 GB or more |
| Storage | Room for the app, source photos, and processing data; dense maps can require tens or hundreds of GB |

Memory and disk use depend on photo count, resolution, quality, and the chosen
products. The bundled COLMAP build and the installed NVIDIA driver must be
compatible. **Project > Preferences** can select another COLMAP installation.

## Store projects separately

Keep projects, source photos, and processing results outside the application
installation folder, for example in a dedicated survey folder on a data drive.

A project includes its `.pmsx` file and its associated working/result folders.
Current projects commonly use a neighboring `<project>.files` folder; older
projects may refer to another working-folder layout. Copy the actual result
folders used by your project.

## Move a project to another computer

1. Save the project and close the app.
2. Copy the project file and its complete working/result folders.
3. Copy the original photos.
4. Open the copied `.pmsx`.
5. If photos cannot be found, choose **Project > Relocate Photos...** and
   select their new folder.
6. Save the project to retain the new paths.

Also copy texture or tiled-model outputs that were stored outside the project
working folder. Keep a backup until the copied project opens correctly.

## Verify a download

Download the matching `.exe.sha256` file. In PowerShell, replace the example
path with your downloaded Setup path:

```powershell
Get-FileHash -LiteralPath 'C:\path\to\PhotoMeshStudio_Setup_<version>.exe' -Algorithm SHA256
```

Compare the hash with the value in the checksum file. They should match,
ignoring letter case. A checksum checks file integrity, not publisher identity
or application safety. The installer is not code signed.

## Other installation methods

- Developers: [run from source](development/README.md).
- Problems: [troubleshooting](troubleshooting.md).
