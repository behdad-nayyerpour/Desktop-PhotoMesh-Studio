# Troubleshooting

[Documentation](README.md) · [Installation](installation.md)

## COLMAP is not found

Open **Project > Preferences** and check the configured executable path.
Source installations must supply COLMAP separately; the complete Setup includes it.

## Build Point Cloud requires CUDA

Dense stereo requires an NVIDIA GPU and a compatible CUDA-enabled COLMAP build.
Check the GPU/driver and COLMAP information in the status bar and Console.
A non-CUDA COLMAP build can still align photos.

## Processing appears inactive

Check the status bar and **Console** for the current step.
Some operations cannot report a meaningful percentage until their workload is
known. An indeterminate bar means the total is unknown.
Check available project-drive space, especially when keeping depth maps.

## Neural alignment is taking a long time

SIFT + LightGlue and ALIKED + LightGlue are optional and can be slower than
SIFT, especially on CPU. Check the Console for the active engine, device,
extraction stage and pair-matching stage. Pair preselection and the visible
feature limit control workload; enabling every image pair can greatly increase
matching work. ALIKED extraction is bounded to 2048 pixels on the long edge;
keypoints and camera dimensions are restored to original-photo coordinates.
See [alignment options](user-guide.md) before changing quality settings.

## Available memory cannot be determined

Large-allocation planners require a measured memory budget. For source installs,
install the application requirements, including psutil, in the environment used
by run.bat. For Setup installs, keep the generated report and report the error;
do not bypass the memory check with a guessed budget.

## Old products are marked as outdated

After camera optimization or a geometry change, rebuild the affected products.
See [rebuilding after optimization](user-guide.md#rebuild-after-optimizing-cameras).

## Contour export produces few elevation levels

Check the mesh elevation range and contour interval.
If the Z range is smaller than the interval, there may be only one contour
level or none. Check model scale, units, and vertical orientation before export.

## Photos are missing after moving a project

Use **Project > Relocate Photos...**, select the new photo folder, then save.
Copy the complete project results as well as the `.pmsx` file.
See [moving projects](installation.md#move-a-project-to-another-computer).

## Report a failed step

Use the error dialog's **Report to GitHub** button or **Help > Report a Problem...**.
Reports are saved in `%LOCALAPPDATA%\PhotoMeshStudio\reports`.
The **Help > Open Log Folder** command opens application logs.

Include the action that failed, expected behavior, version, settings, and the
generated report ZIP when possible. Review attachments before sharing them.
An automated non-GPU test pass does not verify a full reconstruction on your GPU.

[Open an issue](https://github.com/behdad-nayyerpour/Lens2Mesh/issues/new?template=bug_report.md).
