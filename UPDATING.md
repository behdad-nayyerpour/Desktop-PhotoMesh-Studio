# Installing a newer version

## Lens2Mesh 1.0.5 candidate

PhotoMesh Studio is becoming Lens2Mesh. The public release remains 1.0.4 until
the test candidate is accepted and a complete installer is separately published.
For candidate testing, close the application and run the exact BAT supplied for
your installed baseline. It downloads only changed components, checks hashes
and creates a recovery receipt in `.lens2mesh-patches` inside the installation.
Follow the printed rollback command if you need to restore that baseline.
Do not manually mix files from different candidates or run the patch over
locally modified application files. Projects and user settings are not patched.

The old installation folder and `.pmsx` project extension remain valid. The
candidate can rename this install's per-user legacy shortcuts to Lens2Mesh and
retains their original bytes next to the shortcut as `.lens2mesh-backup`.
It does not overwrite an existing Lens2Mesh shortcut. The current PDF is the
unchanged approved 1.0.4 manual; see [candidate additions](docs/candidate-105.md).

## Published complete installers

1. Download `PhotoMeshStudio_Setup_<version>.exe` from the
   [latest release](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/latest).
2. Save your project and close the application.
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

## 1.0.4 marker and reference compatibility

Version 1.0.4 keeps existing project/result paths and survey coordinates. Marker
measurement edits are available on the original photographs and in Markers;
3D and orthophoto views display/select flags only.

Predicted locations and legacy unpinned placements without measurement provenance
remain visible, but are excluded from adjustment and error measurements until
pinned on the photographs or refined from image content. Confirm the same feature
on at least two different aligned photographs. Imported XYZ alone is insufficient.

The project-wide Use Photo GPS setting gates GPS use without excluding photos.
Turning it off does not undo an existing coordinate frame. Camera optimization
invalidates camera-derived products; rebuild dense/mesh/raster outputs as described
in the [user guide](docs/user-guide.md#rebuild-after-optimizing-cameras).

Project schema 2 and PhotoMesh reference XML 2.0 remain readable. New saves/exports
retain prediction/refinement provenance and marker status. Legacy reference XML,
text and CSV imports remain supported. Keep a separate project copy when older
application versions are still needed.

[Back to the main page](README.md)
