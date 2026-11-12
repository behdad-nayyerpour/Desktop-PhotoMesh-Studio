# Initial Lens2Mesh 1.0.5 test milestone

This is a user-test candidate, not a final release or full installer.

- Source: `0f112b74f09dbeb99673a473cc7b6bb8918389f2`.
- Patch: `Lens2Mesh_TestPatch_0f112b74f09d.zip`, 1,693,857 bytes.
- SHA256: `3eef46fc95a0ab12d3d9cbfb2ec8e4d8b35a144887b03b0eeccadec81867233a`.
- Baseline: exact corrected public PhotoMesh Studio 1.0.4 installation,
  Setup SHA256 `059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f`.
- Verified candidate run: https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43256088287
- Acceptance: 809 tests passed, 8 hardware/data-dependent tests skipped;
  exact installed apply/inventory/rollback checks passed on Windows 2022.

Changes: initial Lens2Mesh display branding and selected L2M icon; independent
PLY reader/writer with deliberate replacement of the old dependency; verified
incremental-update and recovery infrastructure. Unchanged Python and reconstruction
engines are not downloaded. Existing settings/project storage identifiers remain.
The scalar PLY attribute name `list` is supported through load, rewrite,
coordinate transforms and world export; the superseded first ZIP must not be used.

Use the separately verified single-file BAT with the application closed. It
verifies the exact baseline and download before replacement, then retains changed
files under `<installation>/.lens2mesh-patches/<source-sha>/` with `ROLLBACK.bat`.
Do not delete that recovery folder. Projects and source photos are not patch targets.

The complete approved next-version checklist, full licensing review and remaining
branding/shortcut/documentation migration are not completed by this milestone.
The approved PDF remains unchanged at the user's request. Target CUDA/survey-data
acceptance remains separate. No full Setup was built or release published.
