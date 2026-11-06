# Project notes and third-party components

[Development guide](README.md) · [Main page](../../README.md)

PhotoMesh Studio is an independent Python/PySide6 desktop photogrammetry project.

Reconstruction uses [COLMAP](https://colmap.github.io/) (BSD), including its integrated global mapper.
Standalone [GLOMAP](https://github.com/colmap/glomap) is retained only for compatible legacy engines.
Optional local neural matching uses ALIKED (BSD) and LightGlue (Apache 2.0);
[license notices](engine-modernization-102.md#offline-build-and-redistribution) accompany the bundle. The project's own processing
pipeline is described in [Architecture and performance](architecture.md).
Dependencies are listed in [requirements.txt](../../requirements.txt).

Earlier versions arranged menus using publicly documented photogrammetry commands, including
the *Menu commands* appendix of the public
[Agisoft Metashape Professional manual](https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf).
The current preview groups commands by Project, Edit, Process, Display, Survey,
Export and Help. Command identifiers remain compatible with earlier scripts;
their historical paths are aliases, not extra menus.
PhotoMesh Studio is not affiliated with Agisoft.

Toolbar icons are drawn with Qt. The current preview replaces the Markers,
Ortho and Shapes icons with the user-approved target, mosaic and vector-path
designs. Other artwork and interface provenance remain under review; this note
does not certify independent authorship of every asset.

Third-party components retain their own licenses. Their license terms must be
reviewed when redistributing a bundled runtime; this page is not a substitute
for those licenses.
