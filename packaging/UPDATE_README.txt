PhotoMesh Studio - legacy portable code update
=============================================
For a laptop that ALREADY has the portable PhotoMesh Studio installed.
(No install yet? Use PhotoMeshStudio_portable_<date>.zip and README_FIRST.txt instead.)
Use only with the matching portable runtime; see the release's dependency notes.

 1. Close PhotoMesh Studio.
 2. Right-click the zip > Properties > "Unblock" (if shown) > OK.
 3. Extract the zip INTO your installed PhotoMeshStudio folder - the folder that contains
    install_offline.bat and photomesh-studio (e.g. C:\PhotoMeshStudio\PhotoMeshStudio).
    Choose "Replace the files in the destination".
 4. Double-click check_update.bat - it must print "Update OK" and the expected version.
 5. Start PhotoMesh Studio from the desktop shortcut.
 The Python environment (.venv), COLMAP/GLOMAP and your projects are kept.
 Problems: Help > Open Log Folder (%LOCALAPPDATA%\PhotoMeshStudio\logs), send the newest photomesh_*.log.
