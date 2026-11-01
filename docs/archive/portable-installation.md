# Legacy portable installation

> Historical ZIP-based workflow. Current releases use a complete Setup EXE.
> See [Installation](../installation.md) for current instructions.

### 1. What is in the package
`PhotoMeshStudio_portable_<date>.zip` (e.g. `PhotoMeshStudio_portable_20261022.zip`) holds the exact version that runs on the development PC. It needs no internet, either to install or to run.

| Folder / file | Contents |
|---|---|
| `photomesh-studio\` | App code |
| `python\` | CPython 3.13 (64-bit). Nothing needs to be installed system-wide. |
| `wheelhouse\` + `requirements.lock` | Every Python package at its pinned version: PySide6, pyqtgraph, PyOpenGL, numpy, scipy, open3d, plyfile, Pillow, pyproj, pytest and their dependencies |
| `tools\colmap\` | COLMAP 3.8, CUDA build (CUDA 11 runtime `cudart64_110.dll` included) |
| `tools\glomap\` | GLOMAP (fast global alignment, CPU) |
| `redist\` | Visual C++ 2015-2022 x64 installer (if it was available when the package was built). App-local copies of the VC++ DLLs are already in `tools\*\bin`. |
| `install_offline.bat` | Creates the Python environment from `wheelhouse\` (pip `--no-index`) and a desktop shortcut |
| `PhotoMesh Studio.bat` | Starts the app (runs the installer on first start) |
| `run_tests_offline.bat` | Self-test |
| `create_shortcut.ps1` | Re-creates the desktop and Start-menu shortcut |

### 2. Requirements
- **Windows 10 or 11, 64-bit.** The app does not run on 32-bit Windows or ARM.
- **Disk space:**
  - about 3 GB for the installed package;
  - plus room for projects. A 641-photo drone project with a dense cloud and mesh needs tens of GB in its working folder.
- **Memory:** 16 GB RAM minimum; 32 GB or more is recommended for large point clouds (about 28 M points).
- **GPU (recommended):** an NVIDIA GPU with a driver that supports **CUDA 11.x**, which means driver version **452.39 or newer**. Any current NVIDIA driver qualifies.
  - The development PC uses an RTX 3080 Laptop GPU with driver 512.36.
  - Use 4 GB of VRAM or more; 8 GB is recommended for depth maps.
  - Very new GPU generations may not be supported by a CUDA 11 build of COLMAP 3.8 (not verified). If Build Point Cloud fails with a CUDA "no kernel image" error, use a newer CUDA build of COLMAP via Tools > Preferences.
- **Without an NVIDIA GPU** (Intel/AMD graphics), the app detects the missing NVIDIA driver and runs in CPU-only mode. The status bar shows "COLMAP: found (CPU only …)".
  - Align Photos works (GPU SIFT is switched off automatically), just more slowly.
  - Tie points, markers/GCPs, Optimize Cameras and filtering work.
  - Build Model from an existing point cloud works.
  - **Build Point Cloud (depth maps) is not available.** COLMAP's dense stereo requires CUDA; the app says so instead of failing.
- **3D view:** needs OpenGL 2.1 or newer, which any normal graphics driver provides. On a remote desktop without OpenGL, the 3D view shows a message and everything else still works.

### 3. Install
1. Copy `PhotoMeshStudio_portable.zip` to the laptop.
2. Right-click it, choose **Properties**, tick **Unblock** if that box is shown, and click OK. This stops Windows SmartScreen from blocking the scripts.
3. Extract it to a folder **you can write to** with a **short path**, for example `C:\PhotoMeshStudio` or `D:\Apps\PhotoMeshStudio`. Avoid `C:\Program Files`. The result is `C:\PhotoMeshStudio\PhotoMeshStudio\...`.
   - Windows limits file paths to 260 characters, and some Qt files inside the environment are deeply nested. The `photomesh-studio` folder path may be at most about 73 characters, so the extracted `PhotoMeshStudio` folder path must be about 56 characters or less. The installer checks this and stops with a clear message if the folder path is too long (for example, Desktop or Downloads folders inside a long user profile path). Enabling *Win32 long paths* in Windows also removes the limit.
4. Double-click **`install_offline.bat`**. It takes about 1–3 minutes, needs no internet and no administrator rights, and prints:
   - "Packages OK";
   - "COLMAP OK";
   - whether an NVIDIA driver was found.
   It also creates the **PhotoMesh Studio** shortcut on the desktop and in the Start menu.
5. Start the app from the shortcut, or with `PhotoMesh Studio.bat`.
6. Optional: run `run_tests_offline.bat` to self-test. Expect "… passed"; COLMAP tests are skipped unless you pass a photo folder.

> If you move the folder later, run `install_offline.bat` again. The Python environment stores its own location.

### 4. Moving projects from the old computer
A project is a **`.pmsx` file** plus its **working folder**. For example, `bench_drone5\drone_DJI_001_fast.pmsx` uses `bench_drone5\fast\`, which holds COLMAP data, depth maps, point clouds, the mesh and the logs.

1. **Save** the project on the old PC and close the app.
2. Copy the **whole project folder** (e.g. `bench_drone5\`, which contains both the `.pmsx` and `fast\`) to the new laptop, to any drive or folder.
3. Copy the **photos** too (e.g. `F:\Drone\...\DJI_001`), anywhere you like.
4. Open the `.pmsx` in PhotoMesh Studio.
   - **Results** (working folder, tie points, point cloud, mesh, thumbnails) are found automatically next to the new `.pmsx` location. The Console logs "Project folder was moved: product paths updated".
   - **Photos:** if they are not at the old path (a different drive letter, for example), the status bar says "N photo(s) not found…". Choose **Tools > Change Image Paths...** (also in the Workspace right-click menu on the chunk, Images or a photo) and select the folder that now holds the photos. Subfolders are searched; photos are matched by file name, and the best-matching folder path wins when names repeat. The app reports how many photos it relinked and lists any it could not find.
5. **File > Save** to store the new paths.

Notes:
- The app never writes into the photo folders. Read-only photo drives work.
- Texture and tiled model built from the app live in the working folder and move with it. If they were built in a separate folder (for example `bench_drone5_texture\...` or `bench_drone5_tiles\...`), copy those folders too and attach them with **File > Import > Import Texture...** (folder with `info.json` and `texture_0.jpg`) and **File > Import > Import Tiled Model...** (folder with `tileset.json`), then Save.
- Processing metadata (Workspace > Properties) moves with the `.pmsx`.
- Preferences (window layout, layer toggles, COLMAP path) are per-user settings and start at defaults on the new laptop.

### 5. Troubleshooting
| Symptom | Fix |
|---|---|
| Windows protected your PC / scripts blocked | Unblock the zip before extracting (step 3.2), or click *More info → Run anyway*. |
| *ERROR: this folder path is too long for Windows* | Move the extracted `PhotoMeshStudio` folder to a short path (e.g. `C:\PhotoMeshStudio`) and run `install_offline.bat` again. |
| `install_offline.bat` reports *ERROR … missing* | The zip was extracted only partly. Extract it again with Windows Explorer or 7-Zip. |
| Message: *colmap.exe does not start* | Run `redist\vc_redist.x64.exe` (needs admin), or install "Microsoft Visual C++ 2015-2022 Redistributable (x64)". |
| Status bar shows *COLMAP: not found* | Check that `tools\colmap\bin\colmap.exe` exists next to `photomesh-studio\`, or set its path in Tools > Preferences. |
| *Build Point Cloud needs CUDA* | No NVIDIA driver was found. Install or update the NVIDIA driver (452.39 or newer). On non-NVIDIA laptops, dense reconstruction is not possible; process dense on a GPU PC and copy the project back. |
| CUDA error / out of memory during depth maps | Choose a lower quality (Medium/Low) in Build Point Cloud, close other GPU apps, and update the driver. |
| 3D view is black or says "OpenGL unavailable" | Update the graphics driver. On laptops with two GPUs, set *pythonw.exe* (in `photomesh-studio\.venv\Scripts`) to "High performance" in Windows Settings > Display > Graphics. |
| *N photos not found* after opening | Use Tools > Change Image Paths... (section 4). |
| App started from a moved folder fails | Run `install_offline.bat` again. |
| Window freezes while adding many photos (older versions) | Install the update (section 6). Photos are now added in a few seconds; thumbnails fill in the background (status bar, ✕ to stop). |
| Add Photos / Open dialog itself hangs | Tools > Preferences > *Use built-in file dialogs* (section 7). |
| Anything else | Send the newest log from Help > Open Log Folder (section 7). Also check Console (View > Console) and the logs in the project working folder (`*_log.txt`). |

### 6. Updating an existing installation (no reinstall)
A code update comes as a small `PhotoMeshStudio_update_<date>.zip` (about 1 MB).
1. Close PhotoMesh Studio.
2. Unblock the zip (Properties → **Unblock**), then extract it **into** the installed `PhotoMeshStudio` folder — the one that contains `install_offline.bat` and the `photomesh-studio` folder (e.g. `C:\PhotoMeshStudio\PhotoMeshStudio`). Choose **Replace the files in the destination**.
3. Double-click **`check_update.bat`**. It must print *Update OK*.
4. Start the app from the desktop shortcut as usual.

The Python environment (`photomesh-studio\.venv`), COLMAP/GLOMAP and the shortcut are kept. Run `install_offline.bat` again only if an update note says new packages are needed.

Version 0.1.3 (exports, orthomosaic/DEM, Import Shapes with styles, manual markers, toolbar icons, the Build Point Cloud memory fix, faster shapes on photos; see `CHANGES.md`) also needs **no new packages**. Extract the update zip over an existing install as above; a laptop without PhotoMesh Studio uses the full `PhotoMeshStudio_portable_<date>.zip` (section 3).

Version 0.1.2 (Build Texture, Build Tiled Model, textured view, OBJ/glTF/3D Tiles export) needs **no new packages**. Texturing a large model uses a lot of memory (each 8192×8192 page is held in memory as floating point while it is built); 8192×4 on a 1.85 M-face model ran fine on a 32 GB laptop, so on 16 GB machines close other programs or use fewer pages. Real textures need a working OpenGL 2.1 graphics driver; with the built-in Windows "Basic Display" driver large textures are scaled down for display (the files are not).

### 7. Log files (for bug reports)
Every session writes a log file to `%LOCALAPPDATA%\PhotoMeshStudio\logs\photomesh_<date>_<time>_<pid>.log`. Open the folder with **Help → Open Log Folder**. The log contains:
- system info (Windows, CPU/RAM, Python/Qt/Pillow versions, NVIDIA driver);
- every Console message, and the time of each Add Photos phase;
- errors with full tracebacks;
- a **hang report**: if the window stops responding for 20 s, the stack of every thread is written to the log (and repeated every 20 s while the hang lasts).

If something goes wrong, send the newest `photomesh_*.log` (after closing the app, or while it hangs). The last 30 logs are kept.

If **File → Add Photos / Open** itself hangs before a dialog appears (broken Explorer shell extensions, disconnected network or OneDrive drives), tick **Tools → Preferences → General → Use built-in file dialogs**. You can also start the app once with the environment variable `PHOTOMESH_QT_DIALOGS=1`.

