# Installing a newer version

1. Download `PhotoMeshStudio_Setup_<version>.exe` from the
   [latest release](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/latest).
2. Save your project and close PhotoMesh Studio.
3. Run Setup. For an existing EXE installation, use the same installation
   folder if prompted.
4. Launch the app and check **Help > About**.

The same complete offline Setup is used for both new installations and later
versions. It replaces the managed application, Python runtime, and bundled
tools. No separate Update EXE, ZIP extraction, Git, or system Python is needed.

Keep `.pmsx` projects, their result folders, and source photos **outside the
installation folder**. Setup does not delete those external files.
Keep a project backup before processing it with a newer version.

A matching `.exe.sha256` file is published with Setup. It verifies downloaded
file integrity; see [Installation](docs/installation.md#verify-a-download).

Developers running from source should follow the
[development guide](docs/development/README.md).
The older Git/portable update scripts remain for compatibility and are not the
update method for an EXE installation.

[Back to the main page](README.md)
