# PhotoMesh Studio

**Source version 1.0.2** — offline engine compatibility checks, maintained global mapping, optional neural matching, and explicit GPS framing.
Windows installers are published separately in Releases; check their version before downloading.

PhotoMesh Studio is a free desktop photogrammetry application for processing aerial
imagery locally, without a cloud service.

Built with Python and PySide6, it uses COLMAP for photo alignment and dense
reconstruction, alongside application code for project management, visualization,
and surveying workflows.

**[Download for Windows](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/latest)** ·
[User guide](docs/user-guide.md) · [Installation](docs/installation.md) ·
[Changelog](CHANGES.md) ·
[Report a problem](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/issues/new?template=bug_report.md)

## Screenshots

**Dark theme**

![PhotoMesh Studio 1.0.2 displaying a reconstructed aerial survey in dark mode](screenshot.png?v=f4ca6d10)

**Light theme**

![PhotoMesh Studio 1.0.2 displaying a reconstructed aerial survey in light mode](screenshot-light.png?v=2f117e4e)

## Install

Download `PhotoMeshStudio_Setup_<version>.exe` from
[Releases](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/releases/latest)
and run it. The offline installer includes Python, its required packages, COLMAP,
and optional legacy GLOMAP; a separate Python or Git installation is not needed.

For a later version, close PhotoMesh Studio and run the newer Setup over the
existing installation. There is no separate Update EXE.
Keep projects, processing results, and original photos outside the installation folder.
See [installation and requirements](docs/installation.md) and [updating](UPDATING.md).

## Main features

- Photo alignment with COLMAP, integrated global mapping, and legacy-engine fallback.
- Optional offline SIFT/LightGlue or ALIKED/LightGlue matching; SIFT remains the default.
- Dense point clouds, filtering, meshes, textures, and tiled 3D models.
- Ground control and check points, camera optimization, and error reports.
- Orthomosaic and DEM generation with georeferenced raster export.
- Mesh contour export to DXF with `minor` and `major` layers.
- Import and export of survey shapes and common 3D formats.
- Local processing without a cloud service.

Dense reconstruction from depth maps requires an NVIDIA GPU and a compatible
CUDA build of COLMAP. Alignment and mesh generation from existing point clouds
can run on the CPU. The 3D viewer requires an OpenGL-capable driver.

## Quick start

1. Save a new project outside the application installation folder.
2. Choose **Workflow > Add Photos...** or **Add Folder...**.
3. Run **Align Photos...**, then inspect the cameras and tie points.
4. Add ground control and optimize cameras when required.
5. Run **Build Point Cloud...**, **Build Model...**, and the required texture,
   DEM, or orthomosaic steps.
6. Use **File > Export** to save your deliverables.

For settings, marker editing, rebuilding after camera optimization, and contours,
see the [user guide](docs/user-guide.md).

## Documentation

| I want to... | Read |
|---|---|
| Install, check requirements, or move a project | [Installation](docs/installation.md) |
| Install a newer release | [Updating](UPDATING.md) |
| Process photos and export results | [User guide](docs/user-guide.md) |
| Diagnose a failed step | [Troubleshooting](docs/troubleshooting.md) |
| Run the source or contribute | [Development](docs/development/README.md) |
| Understand the processing pipeline and benchmarks | [Architecture and performance](docs/development/architecture.md) |
| Build the Windows installer | [Release guide](packaging/RELEASE.md) |
| Review changes by version | [Changelog](CHANGES.md) |


## Project

PhotoMesh Studio uses [COLMAP](https://colmap.github.io/) for reconstruction,
with the application's `fastpipe` orchestration pipeline and a Python/PySide6
interface using pyqtgraph.

Optional components include LightGlue and ALIKED for local feature matching,
and [GLOMAP](https://github.com/colmap/glomap) for compatible legacy workflows.
Third-party components retain their respective licenses.

PhotoMesh Studio is an independent project and is not affiliated with or endorsed
by Agisoft. See [project notes and third-party components](docs/development/project-notes.md)
for interface references and component information.
