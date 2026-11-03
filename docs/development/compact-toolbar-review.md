# Compact toolbar and neural-method warning

Approved layout: two rows with separators. Project/edit/processing/settings are
on the first row. The second has uniformly labelled under-icon controls:
tie points, cloud, mesh, ortho, DEM; overlays; additional layers; cube views;
zoom and Fit. Render-mode titles remain short and stable; their tooltip and menu
show current mode/Hidden. No fixed button widths or elided labels are used.
Native size hints and the toolbar overflow mechanism preserve usable controls.
All commands also remain in the application menus.

Toolbar composition reuses existing QActions, including overlay toggles and
transparency. Layers contains only additional controls: tiled layer/modes,
camera/marker labels, trackball, projection and Show/Hide All. Display controls
already visible in the row are not duplicated in Layers. Camera navigation uses
painter-based cubes. Marker/ortho icons reuse the existing matching vector design;
shape fill and green segments follow the provided reference. No image-generation
bitmap is embedded in the app.

SIFT+LightGlue and ALIKED+LightGlue immediately show a wrapping note below the
selector that they may take a long time, particularly on CPU/many photos.
SIFT hides that note. Processing parameters and numerical algorithms are unchanged.

Review: toolbar builder, button lifecycle/state, icon resource dispatch, menu/
Workspace actions, transparency popup and alignment dialog signal connections.
The removed category labels and duplicate layer menu entries are intentional.
No legacy action, processing feature or project compatibility path is removed.
Repository-wide baseline maintainability audit remains pending before a release.
No version bump, Setup build or target-PC execution is included.

Validation planned: existing regression suite on Linux/Windows, warning and menu
interaction tests, native text-under-icon layout at 1280 logical px in dark/light
themes and scale factors 1/1.5/2. Inspect actual CI-rendered screenshots for size,
spacing, labels and clipping. This is UI work; native-engine benchmarks from the
previous processing fix are not rerun.
