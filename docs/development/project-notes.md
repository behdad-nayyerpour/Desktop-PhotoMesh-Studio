# Project notes and third-party components

[Development guide](README.md) · [Main page](../../README.md)

PhotoMesh Studio is an independent Python/PySide6 desktop photogrammetry project.

Reconstruction uses [COLMAP](https://colmap.github.io/) (BSD) and optionally
[GLOMAP](https://github.com/colmap/glomap) (BSD). The project's own processing
pipeline is described in [Architecture and performance](architecture.md).
Dependencies are listed in [requirements.txt](../../requirements.txt).

The menu layout follows publicly documented photogrammetry commands, including
the *Menu commands* appendix of the public
[Agisoft Metashape Professional manual](https://www.agisoft.com/pdf/metashape-pro_2_3_en.pdf).
PhotoMesh Studio is not affiliated with Agisoft.

The project describes its code, styling, and icons as original, using Qt standard
icons where applicable. No third-party application files were inspected or copied.

Third-party components retain their own licenses. Their license terms must be
reviewed when redistributing a bundled runtime; this page is not a substitute
for those licenses.
