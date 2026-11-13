# Lens2Mesh1.0.5 candidate additions

This supplement describes the current candidate. The complete English1.0.4
PDF is retained unchanged and opens offline through Help > User Manual (PDF).
Help > Third-party Notices opens component licenses and replacement information.

## References and calibration

Use measured control coordinates and place the same physical point on at least
two aligned photographs. Check points stay outside adjustment and provide
independent accuracy checks. Approximate coordinates taken from the model
cannot verify survey accuracy. GPS and marker switches control the reference
constraints; turning a switch off does not undo an existing coordinate frame.
Select the camera model and fit only parameters supported by that model.
Reported DJI/RTK deviations are opt-in metadata, not an accuracy certificate.

Confirm horizontal coordinates, units and camera/control height references.
Unknown or incompatible height references must be resolved before mixing GPS
and controls. No geoid correction is automatic. ENU requires confirmed WGS84
ellipsoidal heights and exports its actual local Cartesian frame.

## Ground classification, DTM and LAS/LAZ

Point Cloud Classification estimates ground with a progressive morphological
lower envelope. Cell size controls the terrain grid; slope permits terrain
inclination; height thresholds control separation; maximum window radius must
be large enough for above-ground objects. A large roof, low vegetation, cliffs
and incomplete coverage can defeat these assumptions. Inspect results and
independent reference data before using the derived DTM for decisions.

The source cloud is retained. Ground uses class2 and non-ground class1; this
candidate does not provide separate automatic building/vegetation classes.
Class colours and visibility controls are separate from outlier filtering.
Build DTM uses classified ground, while Build DEM retains the DSM workflow.
Measured cells and permitted interpolation remain distinct; gaps are not proof
of a terrain surface. LAS/LAZ export preserves classes and supported attributes,
with explicit coordinate precision and actual Cartesian CRS metadata.

## Cross section and distance

Open Survey > Cross Section. The closable bottom panel replaces the standalone
measurement command. Click a start point, move the mouse to preview the line,
then click the end. Drag either endpoint to edit it or its middle handle to
move the whole line. Manual coordinates remain available. Navigation stays
available; the resulting length uses model units until a metric scale exists.

Sections use the current mesh. On photographs they require valid calibration
and surface intersection; an orthophoto needs a matching mesh link/frame.
Missing geometry produces gaps. Busy feedback and cancellation prevent new
drawing from competing with a pending large-mesh calculation. Photo context
and marker editing are blocked while the section panel is open and restored
when it closes. Model and orthophoto marker flags remain display/select only.

## Progress, scripts and compatibility

Progress uses available work counts. Unknown totals stay indeterminate; ETA
needs enough stable measured samples and may disappear after workload changes.
Completion is published after successful output. A completed build activates
its resulting product without applying stale results to another project.

Run Script reports reading, syntax and execution errors with complete tracebacks
and honours declared Python source encoding. Scripts run on the GUI thread;
long custom scripts should not perform blocking processing there.

Existing projects, settings and legacy installation paths remain supported.
Point selection/deletion is deferred to a later version. Full Setup is built
only after acceptance of the tested incremental candidate.
