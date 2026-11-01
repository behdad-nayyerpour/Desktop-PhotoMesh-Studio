# Troubleshooting

[Documentation](README.md) · [Installation](installation.md)

## COLMAP is not found

Open **Tools > Preferences** and check the configured executable path.
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

## Old products are marked as outdated

After camera optimization or a geometry change, rebuild the affected products.
See [rebuilding after optimization](user-guide.md#rebuild-after-optimizing-cameras).

## Contour export produces few elevation levels

Check the mesh elevation range and contour interval.
If the Z range is smaller than the interval, there may be only one contour
level or none. Check model scale, units, and vertical orientation before export.

## Photos are missing after moving a project

Use **Tools > Change Image Paths...**, select the new photo folder, then save.
Copy the complete project results as well as the `.pmsx` file.
See [moving projects](installation.md#move-a-project-to-another-computer).

## Report a failed step

Use the error dialog's **Report to GitHub** button or **Help > Report a Problem...**.
Reports are saved in `%LOCALAPPDATA%\PhotoMeshStudio\reports`.
The **Help > Open Log Folder** command opens application logs.

Include the action that failed, expected behavior, version, settings, and the
generated report ZIP when possible. Review attachments before sharing them.
An automated non-GPU test pass does not verify a full reconstruction on your GPU.

[Open an issue](https://github.com/behdad-nayyerpour/Desktop-PhotoMesh-Studio/issues/new?template=bug_report.md).
