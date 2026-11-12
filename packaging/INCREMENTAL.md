# Incremental test candidates

The candidate workflow installs the exact corrected public 1.0.4 Setup only on
a disposable remote runner. It builds a ZIP containing changed installed files,
the manifest and updater, not a complete Python/engine environment or Setup.

`build_patch.py` compares tracked candidate app code/resources with the real
installed baseline. Equivalent line endings are ignored. The manifest binds
all baseline application hashes, runtime identity, exact candidate Git commit,
payload hashes and deliberate dependency removals. The replaced PLY dependency
is removed only from its verified installed RECORD after checking declared
transitive requirements; no unrelated runtime files are writable by this patch.

After automated acceptance, place the ZIP on an artifact-only branch and bind
the launcher to that exact **artifact commit**, not a moving branch URL:

```powershell
python packaging/make_patch_launcher.py --url <exact-raw-GitHub-ZIP-URL> --sha256 <archive-sha256> --output Lens2Mesh_Update_Test_1.0.5.bat
```

The user runs the BAT with the application closed. It uses the existing
installation registry entry or an explicit first argument to find the installed
root. If no entry exists it asks for the folder containing `app` and `python`.
It downloads only the ZIP, checks its SHA256 and runs the updater with the
installed Python. No pip, Setup or full runtime download occurs.

The updater validates containment, baseline/payload hashes and running processes
before replacement. It saves changed files and a recovery journal under
`<installation>/.lens2mesh-patches/<candidate-sha>/`. `ROLLBACK.bat` in that folder
restores the previous managed files and removed dependency. New files are removed
on rollback; later user modifications block automatic rollback. Replacement
failures attempt immediate restoration. After a power interruption, use the
retained rollback before retrying; never delete the recovery folder first.

The downloadable BAT itself is exercised by `test-patch-download.yml`, including
a custom installation path containing spaces and Persian letters. Tests must
verify installed module origins so a source checkout cannot accidentally satisfy
an installed-build assertion. The full Setup remains gated on explicit user
acceptance; publishing a final release requires separate authorization.
