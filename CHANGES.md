# Lens2Mesh changelog

Changes are listed from newest to oldest. Installation instructions in older
entries describe the release at that time; current releases use one full Setup
EXE. See [Updating](UPDATING.md).

### 1.0.5 (test candidate; Setup pending acceptance)

- Rename current branding to Lens2Mesh; retain project extensions, settings and installer identity for compatibility.
- Add strict EXIF/XMP decoding, camera models, calibration presets, opt-in GPS accuracy and explicit horizontal/vertical reference controls.
- Add ground classification, class display, ground-only DTM and LAS/LAZ export with coordinate/class provenance.
- Combine measurement and cross section in Survey > Cross Section, in a closable bottom panel with live drawing, endpoint/midpoint editing and background mesh processing.
- Improve measured progress, ETA suppression, automatic successful-product display and large-project solver/GPS/DEM capacity.
- Replace the PLY dependency independently, remove reviewed unused Qt addons and add offline third-party notices and unchanged approved PDF access.
- Report complete user-script tracebacks, preserve source encoding and validate exact Windows runtime package versions against hashed wheel pins.
- Test upgrades using incremental BAT packages and byte-exact rollback; full Setup is not yet published.
- Direct point selection/deletion remains deferred. The approved complete English PDF remains unchanged.

### 1.0.4 (2026-11-07, corrected installer 2026-11-08)

- Validate control coordinates before Optimize Cameras and name the invalid marker and CRS in the error.
- Right-click a photo to place any existing marker directly from the marker list.

- Reset Ortho/DEM selection when opening a photo, allowing one-click return to a raster in Plan View.
- Use the project filename in exported processing reports instead of legacy dataset names.
- Separate Project, Markers and Cameras panels; Photos on the right and floating Console/Jobs.
- Use 3D View and shared Plan View for photographs and orthophotos/DEMs. Edit markers only on source photos and in Markers; spatial views only display/select them.
- Exclude predicted and unconfirmed legacy unpinned placements from adjustment/error measurements; preserve pin/refinement provenance in projects and PhotoMesh XML.
- Respect marker and GPS switches in local/global optimization; keep check points independent and retain fewer than three controls when GPS supplies initialization.
- Preserve all supported COLMAP camera models and their actual calibration parameters during bundle adjustment; validate inverse distortion and reference weights.
- Recompute current marker residuals after edits/Undo/Redo; reject behind-camera intersections, conflicting duplicate observations and incompatible photo/calibration pixel dimensions.
- Preserve photo aliases across re-alignment, removal and reordering; validate GPS pair selection and date-line distances.
- Replace camera reference checkboxes with project-wide Use Photo GPS; preserve legacy opt-outs conservatively.
- Remember window/panel layout, render styles and successful file/folder picker directories.
- Add the approved offline About/license text and full bundled license viewer.
- Clear stale photo identity when a newly requested image cannot be opened.
- [Release validation](docs/development/release-review-104.md) records the numerical checks, upgrade test and checksum of the published installer.

### 1.0.3 (2026-11-07)

- Widen Tie Points, Cloud, Mesh and Transparency captions, including selected states; retain native split visibility/style controls and compact icon sizes. Keep the display row within 1280 logical pixels by tightening view/zoom side padding.
- Use complete processing labels and reorganized Project/Process/Display/Survey/Export menus with independent layer icons.
- Remove Full Screen/F11 and the inactive Measure Shape command; retain shape metrics in Properties.
- Use project-data terminology, processing workspace names and project schema 2. Read existing project records and paths; older application versions may not read new saves.
- Export independent PhotoMesh reference XML 2.0 while retaining legacy reference import.
- Protect project context during processing, referenced files and linked targets during cleanup, and temporary sources until metadata is saved.
- Preserve older raw-cloud projects across failed/cancelled rebuilds and close failed TIFF/DEM readers.
- Handle byte-valued EXIF altitude references consistently and validate available memory before large allocations.
- Fix the reported dense-workspace nesting case without allowing processing to overwrite input photos.
- Complete the [baseline maintainability review](docs/development/release-review-103.md), remove obsolete processing routes and unused imports/locals, and retain required compatibility paths.
- Build and verify the complete 1.0.3 Setup, including an upgrade over 1.0.2. Linux and Windows each pass 680 tests; native CPU synthetic reconstruction and installed-source/version checks pass. Installed-user appearance review was approved on 2026-11-07; full real-data CUDA reconstruction remains a separate target-hardware check.

### 1.0.2 (2026-11-02)

- Pin the offline Windows engine bundle to COLMAP 4.2.1, with CPU/CUDA builds, SHA256-verified local neural models and retained legacy compatibility.
- Prefer the maintained integrated global mapper when available. Keep incremental fallback; do not enable experimental bundle-adjustment backends automatically.
- Probe CUDA driver/device compatibility and real feature extraction/matching in child processes. A failed GPU feature probe retries the same method on CPU.
- Isolate native engine DLL/Qt settings from the application's PySide6 environment.
- Add explicit optional SIFT + LightGlue and ALIKED + LightGlue modes with visible, bounded feature counts and local model validation. No processing-time downloads.
- Apply checked, valid, non-collinear camera GPS to the initial model frame when selected. Preserve existing project frames; use Optimize Cameras for later changes.
- Reject invalid geographic regions and filter GPS positions before selecting a metric projection zone.
- Synchronize modern frame/rig metadata and pose-prior camera links after calibration grouping, optimization, registration and coordinate transformations.
- Validate reconstruction geometry/observation tracks in an isolated worker before activating an alignment. Publish adjusted sparse models and dependent geometry together with rollback on failure.
- Match current/legacy solver option names, invalidate depth reuse when the engine changes and allow CPU Delaunay meshing from existing fusion data.
- Restore original calibration dimensions before grouping cached working photos, preventing different sensors from merging after downscaling.
- Match all pairs when both preselection methods are explicitly disabled.
- Disable coarse-camera pose reuse when focal priors are unavailable; reconstruct at target resolution to avoid biased self-calibration.
- Add native Windows reconstruction benchmarks with known geometry, calibration-free comparisons and point-cloud/mesh checks. Neural methods are not assumed faster or more accurate for every dataset.
- Fix the reported Properties exception when filter statistics are saved as JSON pairs rather than dictionaries. Read old formats without changing counts and write a canonical schema.
- Retain compatible legacy GPU SIFT for older drivers; route optional neural commands to the modern CPU engine with matching command capabilities.
- Rebuild the full Setup EXE. Preparation downloads pinned assets once into a reusable build cache; target-machine processing remains offline.

### 1.0.1 (2026-11-01)

- Reviewed alignment, dense-cloud, mesh, texture, tiled-model, DSM and orthomosaic workflows together; see the [77-item scope](docs/development/workflow-review-101.md).
- Show effective settings, grid/texture resource estimates, source freshness, real units and mesh triangle targets (including the disabled target field).
- Remove duplicate alignment resolutions and the ineffective reset checkbox. Use one visible feature limit; the default is 24,000 to retain the former fine-stage workload without a hidden secondary cap.
- Preserve the existing project frame and previous results during re-alignment; failed/cancelled builds do not publish partial products.
- Validate depth-map reuse against photo, calibration and all relevant depth settings. Legacy caches without input identity require one rebuild.
- Make terrain filtering opt-in, expose local-filter thresholds and report supporting-photo counts and removal statistics.
- Stream large PLY point inputs, enforce meshing point limits, expose component thresholds and disable source-inapplicable controls.
- Rasterize actual mesh triangles for DSMs, retain coverage masks and sample DEM surfaces directly for orthomosaics.
- Keep pixel limits, texture page limits and tile limits explicit; bound pathological atlas/partition cases and correct parent bounds/global transforms.
- Provide transactional texture/raster/tiled product sets and invalidate caches when their source photos or geometry change.
- Add right-click **Align Selected Photos from GCPs**: calibrated camera resection from at least six distinct, well-spread measured controls; existing poses remain fixed and visible shapes refresh on the new photo.
- No additional runtime dependencies. Rebuild the full Setup EXE for distribution.
- Automated validation includes regression tests, software OpenGL and same-runner processing benchmarks. A full real-data COLMAP/CUDA reconstruction is still a release check on target hardware.

### 1.0.0 (2026-11-01)

- Workspace/Reference now extend to the status bar; Photos/Console/Jobs align beneath the viewport to their right.
- Follow-up fixes within 1.0.0: rasterized all 3D overlay labels and legend text before GL composition; integrated coordinate/pixel RMSE into the final table rows; embedded compact Properties inside Workspace; suspended the wait cursor while interactive settings are visible.

- Applied and persisted Dark/Light themes and the preferred loaded-product view.
- Removed ineffective alignment/mesh controls and unsupported chunk-management commands.
- Unified camera GPS and ground-control/check tables in Reference. Camera reference checkboxes are independent of row selection and alignment enablement.
- Replaced marker targets with consistent green/blue/grey flags anchored by a precise ground point in Photo, Model and Ortho views and marker tables.
- Kept two progress bars in task dialogs/relevant panes. The status bar now contains Ready/Busy and CPU/GPU load only.
- Acknowledged commands immediately with a counted busy cursor; retained explicit native-dialog fallback settings.
- Moved project preparation off the GUI thread and made failed/cancelled opens transactional.
- Preserved photo-list items, selection and scroll position during marker edits.
- Kept the legacy single-dataset file format; multi-chunk legacy projects require separation in an older release instead of silently losing data.
- No new runtime dependencies. Build a new complete Setup to distribute 1.0.0.

### 0.1.17 (2026-10-30)

- Repository maintenance: removed retired Git updaters, portable ZIP builders, and obsolete guides. Full Setup remains the installation/update method; source launch helpers, active shortcut repair, benchmark tools, and applicable regression tests are retained. This maintenance does not change the application version or rebuild published installers.

- Progress dialogs open before work starts, separate observed stage progress from the weighted overall estimate, and show elapsed time plus measured-rate ETA where available. Unknown totals remain indeterminate.
- Pipeline planning callbacks run off the GUI thread. Partial process output is buffered so split progress lines are retained.
- Background view, texture, Ortho tile and thumbnail jobs report activity in the status bar with a busy cursor, without clearing another active job's status.
- Added Delete / Pin / Ignore / Use / Move marker actions in Photo, Ortho and Model views. Move uses a crosshair and Escape cancels. Ignore is separate from Control/Check classification.
- Larger, thicker marker symbols and labels share green pinned, blue placed/used and grey unused/ignored states.
- Camera refinement marks camera-derived products stale and displays rebuild notices above the 3D and Ortho views.
- Added Control/Check filter tabs and per-group and overall coordinate/pixel RMSE summaries to the Markers pane. Missing error measurements are shown as a dash.
- No runtime dependency changes.

### 0.1.16 (2026-10-29)

- Fixed marker overlays and marker undo/redo history leaking into a new/opened project or another chunk; queued edits from the previous view are discarded.
- The Ortho tab no longer draws the model point cloud or camera positions as a substitute for an orthomosaic/DEM.
- Added Place Marker for the single selected marker in the Ortho context menu. It reuses that marker and preserves its reference, accuracy, control/check setting and manually pinned photo observations. Add Marker still creates a new marker.
- Optimize Cameras checks usable references before starting. Insufficient controls/GPS now offer an explicit local-only bundle adjustment, retaining the input camera frame/scale without claiming georeferencing. Existing dense products must be rebuilt after camera optimization.
- Fixed EXIF GPS conversion for UTM projects and duplicate-photo/degenerate marker triangulation. Added regressions for issue #1 and these GUI workflows.

- Added a dedicated File > Export > Export Mesh Contours command beside Export Model. The user chooses a positive contour interval, and horizontal mesh sections are exported to DXF as elevation-bearing 3D polylines.
- Contour polylines use separate minor and major CAD layers: four intermediate levels are minor and multiples of 5 times the interval in world Z are major. Both layers are explicitly defined in the DXF.
- Contours use world coordinates, preserve closed loops and separate components, and split at ambiguous mesh section junctions. Export runs off the UI thread and cancellation preserves the previous destination.
- Added analytic geometry, cancellation, GUI and independent DXF-reader tests. The application needs no additional runtime packages or AutoCAD/Civil 3D installation.

### 0.1.15 (2026-10-27)

- Fixed File > New leaving the previous photo visible after the workspace becomes empty.
- Cleared stale Ortho points, markers, raster work and view position when creating or opening a project or switching chunks. Background view results from the previous project are ignored.
- Added a GUI regression test for clearing the Photo and Ortho tabs.
- No dependency changes. Releases now use one complete Setup EXE; running a newer Setup replaces the managed app, Python, and tools folders in the existing installation. No Update EXE is built.

### 0.1.14 (2026-10-27)

- Keypoint selection now loads one image's feature and descriptor BLOBs from SQLite at a time, avoiding a memory spike proportional to the whole photo set. In a 40-image synthetic read, peak Python memory fell from about 22 MiB to 1.1 MiB; the read took 0.035 s instead of 0.021 s.
- When Windows cannot create photo links, unchanged staged photo copies are reused on later runs. Changed sources, replaced photos, and modified staged copies are refreshed.
- No dependency changes. The versioned update EXE contains the app changes; the full installer remains available for new installations.

### 0.1.13 (2026-10-27)

- Fixed CUDA detection when COLMAP fails to return a help banner: the app now reports CPU-only instead of assuming CUDA is available.
- Fixed reuse of a working folder after replacing a photo with another file of the same name; COLMAP now reads the current photo.
- New Windows setup and versioned update EXE build. The full installer includes Python, COLMAP, and GLOMAP; code-only updates check runtime compatibility and include the runtime when it has changed.
- Updated issue and update links for the new independent repository. The original repository is unchanged.
- Fixed first-run launcher behavior after a failed setup and made Windows path/link tests portable.

### 0.1.12 (2026-10-25)

- The loading screen (splash) now appears right after start, about 0.2 s instead of about 1.3 s, and stays until the main window is up.
  - Cause: Qt's built-in splash screen waits up to 1 s inside its own "show" step before it can appear. The splash is now a plain window that shows at once.
  - The system information line in the log (Python, NumPy, Pillow, GPU) is written after the splash is visible, not before it.
  - The main window is also ready about 1 s sooner.
- Simpler menus: every command that only said "not implemented yet" was removed, about 240 entries.
  - Examples: File > Cloud, masks, selection and drawing tools, region and transform tools, basemaps, laser scans, classification, batch processing, most Tools sub-menus, and the empty Timeline and Animation panes.
  - The Edit > Snap toggles were removed too; they did not snap anything.
  - Duplicate entries were removed: File > Import > Import Reference (same as Import Markers), Help > Online Knowledge Base (same as Contents), Model > DEM and Model > Orthomosaic (they remain in the Ortho menu).
  - The toolbar's navigation/selection button was removed; selection tools never existed, and navigation is always on.
  - Nothing that does work was removed. Processing (align, point cloud, mesh, texture, tiled model, DEM, orthomosaic, markers/GCPs, export) is unchanged. Shortcuts, saved view settings and projects work as before.
- Desktop and Start menu shortcut: it now uses the PhotoMesh Studio icon (photomesh\resources\photomesh.ico), not the Python icon.
  - An existing "PhotoMesh Studio.lnk" with the wrong icon is fixed automatically, once, the first time 0.1.12 starts, and by later updates. Only the icon is changed.
- No new dependencies. What to do: run update.bat.

### 0.1.11 (2026-10-24)

- Fixed: rebuilding the orthomosaic of a georeferenced project stopped with "exit 0x00000001 (generic failure)" / "Orthomosaic would be 197054x189531 px (37.3 Gpx)" (GitHub issue #3).
  - Cause: the texture had been built before Optimize Cameras (georeferencing) and kept its photo resolution in the old model units. Build Orthomosaic used that value as the default pixel size, about 10x too fine, and the size was only checked after the task had started.
  - Now Optimize Cameras rescales the texture's photo resolution and texel size to the new frame. The orthomosaic, DEM and tiled model built in the old frame are marked "outdated, rebuild".
  - The default pixel size comes from the cameras; the texture's value is used only when it agrees with them.
- The Build Orthomosaic dialog shows the total size in pixels (like Metashape) and warns when it is too large or finer than the photos. A size that cannot be built is caught before the task starts, with a suggested pixel size ("Use ..." or Cancel).
- The orthomosaic extent ignores stray geometry far outside the photos (mesh outliers), so a few bad triangles no longer make the raster huge. A Region still decides the extent when it is set.
- When a processing step stops with its own message, the error dialog and the report title show that message instead of "exit code 1 (generic failure)".
- A failed or cancelled rebuild of the orthomosaic or DEM shows the previous result again (it was never deleted).
- No new dependencies. What to do: run update.bat, then run Build Orthomosaic again. The dialog now proposes the right pixel size (about 2-3 cm for this project, not 0.0021 m). Rebuild the DEM and tiled model too if they were made before the last Optimize Cameras.

### 0.1.10 (2026-10-23)

- Build Model no longer loses the existing model. Prerequisites are checked first. The new mesh is built into a temporary file and replaces model.ply only when it is complete and has faces. A failed or cancelled build keeps the old model and its texture/product info.
- After a successful rebuild the old texture is dropped, and the tiled model, orthomosaic and DEM made from the old model are marked "outdated, rebuild" in the Workspace.
- Photos with the same file name in different folders (e.g. two IMG_001.JPG) are now matched to the right camera. Texture, orthomosaic and DEM used one photo for both and skipped the other. After Optimize Cameras / georeferencing both got the same pose. The exact link is saved in the project and survives save/open, moving the project folder and Change Image Paths.
- Older projects: the link is recovered from the working folder when possible. Otherwise photos that cannot be told apart are left out with a warning ("run Align Photos again") instead of being mismatched.
- Saving copies no longer re-links a photo copy to another photo with the same name and size.
- The active chunk is restored when a project is opened (it always came back as the first chunk). Invalid values and files without chunks are handled.
- Note: projects saved with 0.1.10 cannot be opened by 0.1.9 or older (rollback).
- No new dependencies. What to do: run update.bat. Projects whose photos share file names: run Align Photos again if the warning appears.

### 0.1.9 (2026-10-23)

- Save As into a sub-folder of the old data folder no longer copies the copy into itself ("File name too long").
- Build Point Cloud: new "Keep depth maps" option, off by default (like Metashape). After fusion the depth/normal maps and consistency graphs are deleted, but only once the point cloud has been checked as written. "Reuse depth maps" still works when they were kept.
- Save As shows a size breakdown (results, depth maps, photo copies). It offers "Copy results only (skip depth maps, can be recomputed)", the default, or "Copy everything".
- New Tools > Clean Up Intermediate Data...: lists the size of each part with checkboxes and asks before deleting. Finished products and photos are never deleted.
- Plain copies of photos in images\ are linked back to the original photos instead of being copied again, where possible.
- Saving a project inside a OneDrive, Dropbox or Google Drive synced folder shows a warning and suggests a local folder. You can still continue.
- A stale chunkN.partial or incomplete copy left by this app in the destination is detected, and you are asked before it is deleted.
- No new dependencies.
- What to do: run update.bat. On the next Save As of Test-Lot3-Drone, accept deleting the old chunk0.partial (or delete it yourself). Use Tools > Clean Up Intermediate Data... to free the depth maps of old projects. Prefer a local, non-synced folder for projects.

### 0.1.8 (2026-10-23)
Needs **no new Python packages**. Update with `update.bat`.

- **Fixed: Save As stopping with "Copying the project data failed … PermissionError: [WinError 5] Access is denied … chunk0.partial -> chunk0"** (GitHub issue #2).
  - **Cause:** the project data was copied into `chunk0.partial` and the folder was renamed at the end. In a OneDrive (or Dropbox) folder the sync client, and often the virus scanner, still has the new files open, and Windows then refuses to rename the folder.
  - **Now:** the data is copied straight into its final folder (`<name>.files\chunk0`); nothing is renamed afterwards. Until the copy is complete the folder holds `PHOTOMESH_COPY_INCOMPLETE.txt`. If a copy is cancelled or fails, that folder is removed again and the project keeps using its current data. A later attempt reuses an unfinished copy; a folder with other files is never overwritten.
  - Files that are locked for a moment (sync, virus scanner, indexer) are retried a few times. Read-only files no longer block the clean-up. If something cannot be removed, the error message names the folder.
  - A `chunk0.partial` folder left by 0.1.7 inside `<name>.files` is not used and can be deleted.

### 0.1.7 (2026-10-23)
Needs **no new Python packages**. Update with `update.bat`.

- **Project data lives next to the project file.**
  - Everything a project computes goes into `<name>.files` beside `<name>.pmsx`, one folder per chunk: alignment, point cloud, mesh, texture, tiles, orthomosaic, DEM, shapes and caches.
  - **Save the project before processing.** Align Photos and every other processing step asks you to save an unsaved project first, with the Save As dialog right there. Cancel = the step does not start. Temporary folders are no longer used.
  - The `.pmsx` stores paths **relative to its folder**, so the whole project folder can be copied or moved to another disk or computer.
  - Photos are referenced, never copied: relative when they are inside the project folder, otherwise absolute.
  - **Save As** to a new place offers to copy the project data into the new `<name>.files`. It checks free disk space first and shows progress with Cancel; a cancelled or failed copy leaves nothing behind. The originals are kept; only data in the old temporary folder of an unsaved project is moved.
  - **Older projects** open as before. On the next Save their paths are written relative. Data outside the project folder can be copied in or left where it is (you are asked). Data already inside the project folder, such as `bench_drone5\fast`, stays where it is.
  - Photos not found when a project opens: you are asked to locate their folder (Change Image Paths).
- **GCPs in the orthomosaic view.** Right-click > **Add Marker** in the Ortho tab places a marker at that point. Its X/Y come from the raster's georeferencing and its height from the DEM or the orthomosaic height (otherwise from the model below). It is projected into every photo that sees it, like markers added on photos or on the model. Then enter its reference coordinates, refine or pin it on photos, and run Optimize Cameras as usual. Markers without coordinates are now also shown in the Ortho tab.
- **CPU and GPU load in the status bar**, updated every 1.5 s in the background.
  - The GPU value (and GPU memory) comes from the NVIDIA driver (NVML) and is hidden without an NVIDIA GPU. `nvidia-smi` is never started.
- **Busy indicator.** While a step runs, the mouse shows the busy cursor and the status bar shows "Working: <step>..." with a small progress bar. The window stays usable; the cursor comes back after success, error or cancel.
- **Window title** shows the version: `PhotoMesh Studio 0.1.7 - <project>`.
- **App icon** (our own design) in the title bar, the taskbar (own taskbar button on Windows) and the desktop shortcut.
- **Splash screen** with progress messages while the program starts.

### 0.1.6 (2026-10-23)
Needs **no new Python packages**. Update with `update.bat`.

- **Fixed: Build Tiled Model failing with "texture atlas packing failed"** (exit code 1, GitHub issue #1).
  - **Cause:** on dense drone meshes the coarser levels of detail split into thousands of tiny texture pieces. Every piece needs a small border, whatever its size, and the tile texture was sized without counting those borders. The pieces could then never fit, however much they were shrunk.
  - **Now:** the tile texture size counts the borders, grows when needed (up to the maximum texture size), and as a last resort gives every triangle its own small cell. Coarse levels always finish; leaf tiles keep their full detail.
  - **Build Texture** has the same safety net: if the pieces do not fit in the chosen number of pages, more pages are used instead of failing.
- **Fixed: `setup_git_update.bat` stopping with "pms_update_setup.ps1 does not exist"** when the folder was already a git checkout without `packaging\update.ps1` (an older or unfinished checkout; the 0.1.4 portable zip has no `packaging` folder).
  - It now adds the GitHub remote if missing, downloads, and sets the program files to the GitHub version. Changed program files are kept in `git stash`; `.venv`, projects and other data are not touched. Then it runs the normal update.
  - If the download fails, the existing checkout is left as it was.

### 0.1.5 (2026-10-23)
Needs **no new Python packages**. Update with `update.bat`.

- **Error reports.** Every crash or failed step now opens one error dialog and saves a report on this computer: `%LOCALAPPDATA%\PhotoMeshStudio\reports\report_YYYYMMDD_HHMMSS.md`, plus a `.zip` with the logs.
  - **Covered:** COLMAP/GLOMAP or other step processes that end with an error code, Python errors in commands and background workers, threads and QThreads, out-of-memory (MemoryError), and serious Qt errors (these are saved without a dialog).
  - **Contents:**
    - time, app version and git commit;
    - the step and its settings, and the command line;
    - the exit code in decimal and hex, with its Windows meaning (e.g. 0xC0000409 = fail-fast, usually out of memory; 0xC0000005 = access violation);
    - the traceback and the last 300 lines of that step's log;
    - project statistics: photos, aligned, products, CRS name;
    - system info: Windows version, CPU, threads, RAM, GPU/VRAM/driver (nvidia-smi), free disk, Python and package versions, COLMAP version.
  - **Privacy:**
    - no photos and no coordinates (only the CRS name);
    - the user folder becomes `%USERPROFILE%`, and project and photo folders become `<project>` / `<photos>`; other paths keep only the drive and the file name;
    - user and computer names are removed.
- **Error dialog** with **Details**, **Copy report**, **Open report folder** and **Report to GitHub**. The dialog also has an optional box for "What were you doing?".
  - **Report to GitHub** opens your browser at a new GitHub issue with the title and report filled in (label `bug`). Nothing is sent until you press *Submit*; the app itself never sends anything and contains no token.
  - If the report is too long for a link, it is shortened and asks you to drag the `.zip` in.
  - No internet? The report stays saved; send it later.
- **Help > Report a Problem...** makes a report of the current session at any time.
- GitHub issue template (`.github/ISSUE_TEMPLATE/bug_report.md`) in the same format.
- The issue address is a setting in `photomesh/report.py` (`ISSUES_URL`; `PHOTOMESH_ISSUES_URL=off` hides the button).

### 0.1.4 (2026-10-22)
Needs **no new Python packages**. The update zip goes over an existing install, just like 0.1.3.

- **Fixed: Build Point Cloud failing in "Building point cloud (fusion)" with exit code -1073740791 (0xC0000409).**
  - **Cause:** at least one depth or normal map was an empty or cut-off file, for example after a full disk or a cancel while COLMAP was writing. COLMAP's fusion then stops with "Check failed: width_ > 0". COLMAP's own resume treats such a file as finished.
  - **Now:** before depth maps and before fusion, every map is checked (header, size, file length). Unusable maps are removed and **only those views** are recomputed, together with the neighbour photos they need. All valid depth maps are kept.
  - Views that still have no valid map are left out of the fusion and listed in the Console.
- **Disk-space check before depth maps.** Ultra high on 640 DJI photos needs about 400 GB while the depth maps are built. The app now stops at the start with a clear message instead of failing hours later.
- **Fusion is memory-aware.**
  - COLMAP's default loaded every full-size depth map, normal map and photo at once: about 250 GB for 640 Ultra-high views.
  - The fusion size, threads and cache are now chosen from the free RAM; the log line "Fusion plan" shows them.
  - After a crash the fusion is retried automatically with less memory. The depth maps are never recomputed for that.
- **Resume:** if a Build Point Cloud with the same settings did not finish, the next run reuses its depth maps, even if "Reuse depth maps" is not ticked.
- **Progress:**
  - The depth-map step shows the photometric and geometric pass, the view number and the remaining time.
  - Fusion shows the image number and the points so far.
  - The bar moves in 0.1 % steps.
- Clearer error messages for COLMAP crashes (exit code explained).
- **Updates from GitHub:** `update.bat` downloads and installs a new version (no more zips), `rollback.bat` goes back to an earlier one, and `setup_git_update.bat` switches an existing install over once. `.venv` and projects are kept. See UPDATING.md.

### 0.1.3 (2026-10-22)
Needs **no new Python packages** (same 74 pinned wheels as 0.1.2). An existing portable install can take the update zip; a new laptop uses the full portable zip.

- **Exports:** model and point cloud export in local coordinates (DXF, PLY) for CAD/Rhino, plus OBJ, glTF and 3D Tiles. Build Texture and Build Tiled Model are included too.
- **Orthomosaic and DEM:** Build Orthomosaic and Build DEM, an Ortho tab, and GeoTIFF + world file output, with placement notes and a Rhino placement script.
- **Import Shapes:** DXF, SHP, GeoJSON, KML and CSV, shown in the 3D view, on the orthomosaic and on every photo.
  - Per-layer and per-shape style: colour, width, dashed lines, fill and fill transparency, point symbols and labels.
  - Hidden parts are drawn dashed in the transparent view.
- **Markers and GCPs:** place and pin markers manually on photos, with predicted positions, a Reference pane and marker refinement.
- **Shading and overlay:** lighting for the 3D view, and readable labels with a background.
- **Toolbar:** original icons, 30 % larger (21 px); marker and shape toggles in the Photo tab.
- **Fixed: Build Point Cloud "MemoryError" during undistortion.**
  - Undistortion maps are now float32 and shared between workers.
  - The number of workers is capped by free RAM.
  - A failed image is retried on its own.
  - An interrupted run resumes where it stopped.
  - The log shows the peak memory.
- **Fixed:** the "Tie point statistics: … no attribute 'sparse_stats'" error when opening a project. Properties now shows projections, mean projections per photo and mean track length. Opening a project no longer marks it as modified.
- **Faster:** drawing shapes on a photo now takes about 0.16 s instead of 7–13 s for about 6000 shapes.
  - Projection is vectorised.
  - Styles and geometry are cached per version.
  - Occlusion is computed in the background after a fast first draw.
  - Lines are drawn as one path per pen.

<div dir="rtl">
