# Architecture and performance

[Development guide](README.md) · [1.0.4 numerical review](release-review-104.md) · [1.0.3 baseline](release-review-103.md)

## Current processing pipeline

| Stage | Behavior |
|---|---|
| Photo analysis | Process-pool EXIF, thumbnail and descriptor analysis, with ordered results and cached outputs. |
| Pair selection | GPS, descriptor and sequential overlap candidates limit matching work. Turning off both preselection methods explicitly permits all pairs and can greatly increase runtime. |
| Working images | Decode/downscale into a managed project workspace; do not overwrite source photos. Restore calibration dimensions and keypoint coordinates before camera grouping. |
| Features | SIFT is the default. Optional SIFT + LightGlue and ALIKED + LightGlue use verified local models and their own bounded, visible feature counts. ALIKED extraction has a 2048-pixel maximum long edge. |
| Mapping | Prefer the integrated global mapper when supported and appropriate; retain incremental and compatible legacy-engine fallbacks. Hierarchical mapping remains selectable. |
| Coarse-to-fine | A SIFT route. Reuse coarse poses only with reliable focal priors; otherwise map at target resolution. Preserve calibration, the project frame and transactional activation. |
| Resources | Bound worker counts and large allocations by measured resources. Unknown RAM stops large-allocation planning rather than inventing a safe budget. |
| Publication | Build new generations first, validate them, then activate complete product sets. Retain old results on failure/cancellation and invalidate derived products when their inputs change. |
| Device policy | Probe compatible device/driver execution in child processes. GPU feature failure can retry on CPU; dense depth maps still require compatible NVIDIA/CUDA hardware. |

See [engine policy and native tests](engine-modernization-102.md),
[workflow contracts](workflow-review-101.md) and the current
[release review](release-review-103.md) for implementation details and evidence.
Benchmarks measure their stated inputs/settings; they do not guarantee timing or
survey accuracy for another dataset.

## Historical measurements

The following measurements describe earlier implementations and the stated
hardware. In particular, the old 18,000-feature selection and standalone-GLOMAP
default are not current configuration guidance. Current alignment settings and
feature limits are documented in the [user guide](../user-guide.md).

Benchmark: `python benchmark.py <image_folder> [--modes fast exhaustive sequential] [--mapper Auto Global Incremental Hierarchical] [--no-gpu]`.
On the 11-image OpenMVG *Sceaux Castle* set (CPU only, no GPU) all modes register
11/11 images with ~0.52 px reprojection error and take ~70 s; Fast replaces the
final incremental mapper (14.4 s) with triangulation + BA (2.4 s), but with so
few photos almost all pairs overlap, so the matching saving only shows on
larger sets (hundreds of photos).

Drone survey, 641 DJI Mavic 3 Pro photos (597 wide 5280×3956 + 44 tele 4032×3024), Medium accuracy, Fast mode,
RTX 3080 Laptop + Ryzen 9 5900HX, COLMAP 3.8 CUDA + GLOMAP 1.2:

| | first Fast run | GLOMAP + refinement fix | speed-ups | final historical run (mixed cameras) |
|---|---|---|---|---|
| total | > 77 min (unfinished) | 38.6 min | 12.6 min | 15.2 min† |
| aligned | – | 596/641 | 596/641 | **640/641** |
| tie points | – | 1.17 M | 0.59 M | 0.62 M |
| reprojection error | – | 0.98 px* | 1.11 px | 1.09 px |

*recomputed after point filtering (the 1.02 px reported then was a pre-BA value).
†the fine stage took about the same time as before (+7 %, 44 more photos); most of the
extra time was in photo reading (EXIF analysis, decoding), which was slower on that run.

Mixed cameras: COLMAP's `single_camera` option silently *skips* every photo whose
size differs from the first one, which dropped all 44 tele (70 mm) photos of the
Mavic 3 Pro. PhotoMesh Studio now extracts per photo and then shares one camera per
group of identical lens + image size ("2 camera group(s): 597 photos, 44 photos" in
the Console). Photos that still don't align are listed in the Console after Align
Photos (here only the last frame, an oblique shot at landing with no overlap).
Speed-ups in that historical implementation: photos decoded once in parallel into downscaled working
images (key points rescaled to full resolution); fine-stage feature selection
(18 000/photo: 80 % smallest-scale for precision + 20 % largest for robustness);
GLOMAP binary output; no second triangulation when no photo was added; bundle
adjustment stops on convergence; tie point colours sampled from the working
images instead of COLMAP re-reading every full-size photo.
