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
The retired Git updater and portable ZIP tooling are no longer distributed.
Existing portable users should install the complete Setup and open their projects
from their separate data folders.

## 1.0.3 project and reference compatibility

1.0.3 reads older projects and preserves their existing result paths. New saves
use project schema 2; keep a separate copy if an older application version is
still needed. Save As can create a new copy with processing workspace names.

New marker XML exports use PhotoMesh reference XML 2.0. Legacy reference XML
and text/CSV import remain supported. Tab-separated reference reports can still
be exported for exchange.

[Back to the main page](README.md)
