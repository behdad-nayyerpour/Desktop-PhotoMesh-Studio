# Architecture and performance

[Development guide](README.md)

The measurements below are historical results on the stated data and hardware,
not performance guarantees for every project or the current release.

## fastpipe — the speed pipeline (default "Fast" mode)

Original implementation of published techniques:

| Stage | What it does |
|---|---|
| Parallel analysis | EXIF, thumbnails and descriptors computed in a process pool (cached). |
| Pair preselection | Union of (a) GPS k-nearest neighbours, (b) top-k global-descriptor similarity (GIST-like gradient grid + tiny image), (c) sequential window. Fed to COLMAP `matches_importer`, so matching cost is **O(n·k)** instead of **O(n²)** (e.g. a 200-photo grid survey: ~1 300 GPS+sequence pairs, ≤ ~2 900 with descriptor pairs, instead of 19 900). |
| Coarse-to-fine | Align at 1024 px first, then extract full-accuracy features, match only pairs co-visible in the coarse model, triangulate into the coarse poses (`point_triangulator`), register the photos the coarse stage missed (`image_registrator`), triangulate again and run one `bundle_adjuster` — never a second full SfM (that is only a fallback if the refinement fails). |
| Camera estimation | **Auto** (default): GLOMAP global SfM for 100+ photos when bundled, else incremental. **Global**: GLOMAP solves all cameras at once (rotation averaging + global positioning). **Incremental**: COLMAP mapper tuned for speed (all threads, fewer/shorter global BAs). **Hierarchical**: COLMAP `hierarchical_mapper`, scene split into parallel sub-models. Global/Hierarchical fall back to incremental if they fail. |
| Decode once | Photos are decoded once (JPEG DCT downscale, process pool) into working images in the project folder (never the photo folder); COLMAP detects on them and key points/cameras are rescaled to full resolution; deleted after alignment. |
| Feature selection | Fine stage keeps 18 000 features/photo at Medium (24 000 High): mostly the best-localised small-scale ones plus the most repeatable large-scale ones — 4× faster GPU matching than 50 k features. |
| GPU | SIFT extraction/matching GPU flags on (toggle in Preferences → GPU). |

Benchmark: `python benchmark.py <image_folder> [--modes fast exhaustive sequential] [--mapper Auto Global Incremental Hierarchical] [--no-gpu]`.
On the 11-image OpenMVG *Sceaux Castle* set (CPU only, no GPU) all modes register
11/11 images with ~0.52 px reprojection error and take ~70 s; Fast replaces the
final incremental mapper (14.4 s) with triangulation + BA (2.4 s), but with so
few photos almost all pairs overlap, so the matching saving only shows on
larger sets (hundreds of photos).

Drone survey, 641 DJI Mavic 3 Pro photos (597 wide 5280×3956 + 44 tele 4032×3024), Medium accuracy, Fast mode,
RTX 3080 Laptop + Ryzen 9 5900HX, COLMAP 3.8 CUDA + GLOMAP 1.2:

| | first Fast run | GLOMAP + refinement fix | speed-ups | current (mixed cameras) |
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
Current speed-ups: photos decoded once in parallel into downscaled working
images (key points rescaled to full resolution); fine-stage feature selection
(18 000/photo: 80 % smallest-scale for precision + 20 % largest for robustness);
GLOMAP binary output; no second triangulation when no photo was added; bundle
adjustment stops on convergence; tie point colours sampled from the working
images instead of COLMAP re-reading every full-size photo.
