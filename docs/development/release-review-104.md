# 1.0.4 implementation and review

## Scope and status

Implementation in progress on an isolated release branch. No public publication
is authorized. The approved scope is in [release-quality.md](release-quality.md).
The review includes maintainability, functional and numerical contracts,
project compatibility, failure/cancellation, offline operation and performance.

## Changes under validation

- Project, Markers and Cameras side panels; Photos on the right.
- Two central tabs with shared Plan View and retained photo/ortho renderer state.
- Console/Jobs initially hidden and opened as floating panels.
- Removed Project's local action strip; existing menu/context commands remain.
- One project-wide Use Photo GPS setting controls pair preselection and camera
  references without removing photographs from alignment. Markers do not toggle it.
- Legacy GPS opt-outs conservatively disable the global policy until explicit
  opt-in; serialized per-camera legacy fields remain readable and unchanged.
- Saved window layout, active central tab, Plan View renderer and render styles;
  per-operation file picker directories.
- Approved About and full bundled offline license viewer.
- Fixed failed photo-open retaining the previously opened photo identity.
- Route GPS references through exact model aliases; unresolved duplicate legacy
  photo names are excluded instead of swapping coordinates.
- Retain selected-photo enable/remove commands in Edit after removing the local
  strip, and block those commands during project preparation/processing.

## Validation

Pending CI regression/static checks, visual review in both themes/scales and
installer validation. New tests exercise Plan View/marker interaction, failed
photo opens, GPS settings and legacy policy, picker cancellation and UI restore.
Existing tests for superseded UI behavior are updated to the approved contracts.

## Review evidence and limits

Read the main window and its reference, marker, shape, toolbar and registration
callers, project serialization, GPS frame validation and fastpipe pair selection.
Existing CPU/GPU processing variants and numerical methods are retained.
No user files or local working copies were inspected or modified.
Real CUDA reconstruction, actual survey accuracy and driver-specific displays
remain target-hardware checks; passing synthetic tests cannot establish these.
