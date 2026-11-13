# Installation and requirements

[Documentation](README.md) · [User guide](user-guide.md)

## Windows installer

Lens2Mesh 1.0.5 has a complete offline base Setup and an optional GPU add-on. Existing
installation folders remain supported. Setup offers destination selection on
fresh installs and upgrades.

1. Open [Releases](https://github.com/behdad-nayyerpour/Lens2Mesh/releases/latest).
2. Download `Lens2Mesh_Setup_<version>.exe`.
3. Run Setup and choose an installation folder. The default is
   `%LOCALAPPDATA%\Programs\Lens2Mesh`.
4. Start Lens2Mesh from its Start menu or desktop shortcut.

The installer includes Python, its packages and COLMAP; compatible legacy
GLOMAP is optional.
Installation and processing can run offline after the file is downloaded.
You do not need to install Git or Python separately.

## Optional NVIDIA acceleration

The base Setup includes the offline ALIKED/LightGlue models. Without the add-on,
these methods automatically fall back to CPU. Standard COLMAP GPU processing is
retained in the base package; it still requires compatible hardware and a driver.

For GPU acceleration of ALIKED/LightGlue, close Lens2Mesh and run
`Lens2Mesh_NeuralGPU_Addon_1.0.5.exe`. Select the existing installation folder.
It installs only the reviewed private runtime DLLs, verifies hashes and records
a rollback command in `.lens2mesh-patches`. It does not install an NVIDIA driver,
CUDA Toolkit, Python environment or models. A normal base upgrade preserves an
already installed add-on. Both installers can be used offline after downloading.

To install a later version, close the app and run its complete Setup.
See [Updating](../UPDATING.md).

## Usage license

Lens2Mesh's own materials are provided for personal and educational
non-commercial use under the [project license](../LICENSE). Commercial use,
including company evaluation and client projects, requires prior written
permission. Third-party components keep their own licenses.

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
Get-FileHash -LiteralPath 'C:\path\to\Lens2Mesh_Setup_<version>.exe' -Algorithm SHA256
```

Compare the hash with the value in the checksum file. They should match,
ignoring letter case. A checksum checks file integrity, not publisher identity
or application safety. The installer is not code signed.

## Other installation methods

- Developers: [run from source](development/README.md).
- Problems: [troubleshooting](troubleshooting.md).
