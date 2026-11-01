PhotoMesh Studio - legacy full offline package
================================================================

Legacy portable ZIP - new laptop (Windows 10/11, 64-bit, no internet needed)
 1. Right-click the zip > Properties > tick "Unblock" (if shown) > OK.
 2. Extract it to a SHORT path you can write to, e.g. C:\PhotoMeshStudio
    (not Program Files, not a deep Desktop/Downloads path).
    Result: C:\PhotoMeshStudio\PhotoMeshStudio\install_offline.bat ...
 3. Double-click install_offline.bat (1-3 min). It must print
    "Packages OK" and "COLMAP OK"; it creates the desktop shortcut.
 4. Start "PhotoMesh Studio" from the desktop shortcut.
 5. Optional self-test: run_tests_offline.bat  (expect "... passed").
 6. Updates later (internet only while updating): install Git for Windows (defaults),
    double-click setup_git_update.bat once (browser sign-in to GitHub), then update.bat.
    See UPDATING.md.
 Details, GPU notes, moving projects: INSTALL_OTHER_LAPTOP.md.  What is new: CHANGES.md.
