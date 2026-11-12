# Initial Lens2Mesh 1.0.5 test milestone

This is a user-test candidate, not a final release or full installer.

- Source: `0fcdf3c9fb4b4dd6b3d77b884004048364b2b063`.
- Patch: `Lens2Mesh_TestPatch_0fcdf3c9fb4b.zip`, 1,693,777 bytes.
- SHA256: `5cfafb3ec8a2530e2003189696390b18ebd2f6e6bd60eb3bdab1147e143ad110`.
- Baseline: exact corrected public PhotoMesh Studio 1.0.4 installation,
  Setup SHA256 `059c81c30479f6c839fcb643f7527a73af94232505aac33840804834fce25b3f`.
- Verified candidate run: https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/actions/runs/43235599102

Changes: initial Lens2Mesh display branding and selected L2M icon; independent
PLY reader/writer with deliberate replacement of the old dependency; verified
incremental-update and recovery infrastructure. Unchanged Python and reconstruction
engines are not downloaded. Existing settings/project storage identifiers remain.

Use the separately verified single-file BAT with the application closed. It
verifies the exact baseline and download before replacement, then retains changed
files under `<installation>/.lens2mesh-patches/<source-sha>/` with `ROLLBACK.bat`.
Do not delete that recovery folder. Projects and source photos are not patch targets.

The complete approved next-version checklist, full licensing review and remaining
branding/shortcut/documentation migration are not completed by this milestone.
The approved PDF remains unchanged at the user's request. Target CUDA/survey-data
acceptance remains separate. No full Setup was built or release published.
